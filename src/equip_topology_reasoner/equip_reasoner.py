# equip_reasoner.py - 設備機器間トポロジー抽出・Brick TTL出力

import ifcopenshell
import networkx as nx
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from rdflib import Graph, Namespace, RDF, RDFS, Literal

# ================== Classes ==================

@dataclass
class BDNSFilter:
    """BDNSタグによるフィルタ設定"""
    pset_names: Tuple[str, ...] = ("Pset_Tag", "Pset_ManufacturerTypeInformation", "Identity Data", "BDNS")
    prop_names: Tuple[str, ...] = ("Tag", "AssetID", "Number", "BDNS", "SystemCode")
    value_regex: Optional[str] = None


# ================== IFC Loading ==================

def load_ifc(ifc_path: str):
    """IFCファイルを読み込む"""
    return ifcopenshell.open(ifc_path)


# ================== BDNS CSV Loading ==================

def load_bdns_guids(csv_path: str) -> set:
    """brick_equipment_set.csvからBDNSタグ付きのGUIDを取得"""
    import csv
    bdns_guids = set()
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if 'ifc_guid' in row and row['ifc_guid']:
                    bdns_guids.add(row['ifc_guid'])
    except Exception as e:
        print(f"Warning: Could not load BDNS CSV: {e}")
    return bdns_guids


# ================== Port & Connection Extraction ==================

def _get_ports_in_range(model, start_id: int, end_id: int) -> Dict[str, Any]:
    """指定ID範囲内のIfcDistributionPortを取得"""
    ports_dict = {}
    for port in list(model.by_type("IfcDistributionPort")):
        try:
            port_id = port.id()
            if start_id <= port_id <= end_id:
                ports_dict[port.GlobalId] = port
        except:
            pass
    return ports_dict


def _extract_system_elements_from_ports(model, start_id: int, end_id: int) -> set:
    """指定ID範囲のPortから関連する全要素を収集"""
    system_elements = set()
    
    # 事前にPort→親要素のマッピングを作成
    rel_p2e_list = list(model.by_type("IfcRelConnectsPortToElement"))
    port_to_parent = {}
    for rel in rel_p2e_list:
        try:
            port = rel.RelatingPort if hasattr(rel, 'RelatingPort') else None
            element = rel.RelatedElement if hasattr(rel, 'RelatedElement') else None
            if port and element:
                port_to_parent[port.GlobalId] = element.GlobalId
        except:
            pass
    
    # 指定範囲のPortを取得
    ports_in_range = _get_ports_in_range(model, start_id, end_id)
    
    # 指定範囲のPortの親要素を追加
    for port_guid in ports_in_range:
        parent_guid = port_to_parent.get(port_guid)
        if parent_guid:
            system_elements.add(parent_guid)
    
    # Port-Port接続から追加要素を収集（マッピング使用）
    rel_p2p_list = list(model.by_type("IfcRelConnectsPorts"))
    for rel in rel_p2p_list:
        try:
            port_a = rel.RelatingPort if hasattr(rel, 'RelatingPort') else None
            port_b = rel.RelatedPort if hasattr(rel, 'RelatedPort') else None
            
            # port_aが範囲内ならその親要素を追加
            if port_a and port_a.GlobalId in ports_in_range:
                parent_a = port_to_parent.get(port_a.GlobalId)
                if parent_a:
                    system_elements.add(parent_a)
            
            # port_bが範囲内ならその親要素を追加
            if port_b and port_b.GlobalId in ports_in_range:
                parent_b = port_to_parent.get(port_b.GlobalId)
                if parent_b:
                    system_elements.add(parent_b)
        except:
            pass
    
    return system_elements


def _extract_port_connections_in_system(model, system_elements: set) -> List[Tuple[str, str, str, Optional[str]]]:
    """システム要素内のPort-Port接続を抽出"""
    connections = []
    
    # Port→親要素のマッピングを構築
    rel_p2e_list = list(model.by_type("IfcRelConnectsPortToElement"))
    port_to_parent = {}
    for rel in rel_p2e_list:
        try:
            port = rel.RelatingPort if hasattr(rel, 'RelatingPort') else None
            element = rel.RelatedElement if hasattr(rel, 'RelatedElement') else None
            if port and element:
                port_to_parent[port.GlobalId] = element.GlobalId
        except:
            pass
    
    # Port-Port接続をループ
    rel_p2p_list = list(model.by_type("IfcRelConnectsPorts"))
    for rel in rel_p2p_list:
        try:
            port_a = rel.RelatingPort if hasattr(rel, 'RelatingPort') else None
            port_b = rel.RelatedPort if hasattr(rel, 'RelatedPort') else None
            
            if not port_a or not port_b or port_a.GlobalId == port_b.GlobalId:
                continue
            
            parent_a = port_to_parent.get(port_a.GlobalId)
            parent_b = port_to_parent.get(port_b.GlobalId)
            
            # 両方の親要素がシステム要素内にある場合のみ接続を追加
            if (parent_a and parent_b and 
                parent_a in system_elements and parent_b in system_elements and 
                parent_a != parent_b):
                
                direction = getattr(rel, 'FlowDirection', None)
                if direction == 'SOURCE':
                    connections.append((parent_a, parent_b, 'directed', 'SOURCE->SINK'))
                elif direction == 'SINK':
                    connections.append((parent_b, parent_a, 'directed', 'SOURCE->SINK'))
                else:
                    connections.append((parent_a, parent_b, 'undirected', None))
        except:
            pass
    
    return connections


# ================== Graph Building ==================

def build_equip_graph(model, start_id: int = 2676166, end_id: int = 2676344) -> nx.MultiDiGraph:
    """
    IFCモデルから指定ID範囲の機器間トポロジーグラフを構築
    - ノード：指定範囲のPortに関連する全要素
    - エッジ：Port-Port接続から導出
    """
    G = nx.MultiDiGraph()
    
    # システム要素を収集
    system_elements = _extract_system_elements_from_ports(model, start_id, end_id)
    
    # システム要素をノードに追加
    for guid in system_elements:
        try:
            element = model.by_guid(guid)
            if element:
                G.add_node(guid, 
                          name=getattr(element, 'Name', None), 
                          type=element.is_a())
        except:
            pass
    
    # Port-Port接続をエッジに追加
    connections = _extract_port_connections_in_system(model, system_elements)
    for source, target, confidence, dir_rule in connections:
        try:
            G.add_edge(source, target, confidence=confidence, dir_rule=dir_rule)
        except:
            pass
    
    return G


# ================== BDNS Filtering ==================

def filter_graph_by_bdns_csv(G: nx.MultiDiGraph, bdns_csv_path: str) -> nx.MultiDiGraph:
    """brick_equipment_set.csvのGUIDリストでグラフをフィルタ"""
    bdns_guids = load_bdns_guids(bdns_csv_path)
    tagged_nodes = {node for node in G.nodes() if node in bdns_guids}
    return G.subgraph(tagged_nodes).copy()


# ================== Brick TTL Export ==================

def export_brick_ttl(model, G: nx.MultiDiGraph, output_path: str, bdns_csv_path: str, include_ports: bool = True):
    """
    グラフを Brick TTL フォーマットで出力
    - feeds: 上流→下流の接続関係（推移閉包を含む）
    """
    g = Graph()
    
    BRICK = Namespace("https://brickschema.org/schema/Brick#")
    EX = Namespace("https://id.morgate51.org/#")  # project# を削除して # のみに
    
    g.bind("brick", BRICK)
    g.bind("m51", EX)
    
    # BDNS CSVからクラスマッピングを取得
    bdns_mapping = {}
    try:
        import csv
        with open(bdns_csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if 'ifc_guid' in row and 'brick_class' in row:
                    guid = row['ifc_guid']
                    brick_class_uri = row['brick_class']
                    # brick:ClassName を BRICK.ClassName に変換
                    class_name = brick_class_uri.replace('brick:', '')
                    bdns_mapping[guid] = getattr(BRICK, class_name, BRICK.Equipment)
    except Exception as e:
        print(f"Warning: Could not load BDNS mapping: {e}")
    
    # ノードのラベルを取得（GUID → ラベル のマッピング）
    node_labels = {}
    for node in G.nodes():
        try:
            element = model.by_guid(node)
            if element:
                name = getattr(element, 'Name', node)
                node_labels[node] = str(name)
        except:
            node_labels[node] = node
    
    # ノードを Brick オブジェクトに変換（m51:Label 形式のURIを使用）
    for node in G.nodes():
        try:
            element = model.by_guid(node)
            if element:
                # BDNSマッピングを使用、なければデフォルト
                brick_class = bdns_mapping.get(node, BRICK.Equipment)
                
                # m51:Label 形式のURIを作成
                label = node_labels[node]
                subject = EX[label]  # m51:Label
                g.add((subject, RDF.type, brick_class))
                
                # rdfs:label も追加
                g.add((subject, RDFS.label, Literal(label)))
        except:
            pass
    
    # 推移閉包を計算してすべての上流→下流関係を追加
    try:
        # NetworkXのtransitive_closureを使用
        closure = nx.transitive_closure(G)
        
        # 最上流ノードからすべての下流ノードへの関係を構築
        try:
        # ソースノード（入力次数が0のノード）を見つける
            sources = [node for node in G.nodes() if G.in_degree(node) == 0]
        
            for source in sources:
              # このソースから到達可能なすべてのノードを取得
                reachable = set(nx.descendants(G, source))
                reachable.add(source)  # 自分自身も含める
            
                src_label = node_labels[source]
                src_subj = EX[src_label]
            
                # ソースから各到達可能ノードへのfeeds関係
                for target in reachable:
                    if source != target:
                        tgt_label = node_labels[target]
                        tgt_subj = EX[tgt_label]
                    
                        # feeds: 上流→下流
                        g.add((src_subj, BRICK.feeds, tgt_subj))
                    
                        # isFedBy: 下流→上流（逆関係）
                        g.add((tgt_subj, BRICK.isFedBy, src_subj))
        except Exception as e:
            print(f"Warning: Could not compute source-descendant relationships: {e}")
            # フォールバック：直接エッジのみ
            for source, target in G.edges():
                try:
                    src_label = node_labels[source]
                    tgt_label = node_labels[target]
                    src_subj = EX[src_label]
                    tgt_subj = EX[tgt_label]
                    g.add((src_subj, BRICK.feeds, tgt_subj))
                    g.add((tgt_subj, BRICK.isFedBy, src_subj))
                except:
                    pass
                
    except Exception as e:
        print(f"Warning: Could not compute transitive closure: {e}")
        # フォールバック：直接エッジのみ
        for source, target in G.edges():
            try:
                src_label = node_labels[source]
                tgt_label = node_labels[target]
                src_subj = EX[src_label]
                tgt_subj = EX[tgt_label]
                g.add((src_subj, BRICK.feeds, tgt_subj))
            except:
                pass
    
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    g.serialize(destination=output_path, format='turtle')