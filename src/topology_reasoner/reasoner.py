# -*- coding: utf-8 -*-
"""
IFC2x3 から空間トポロジを抽出し BOT に写像するトポロジーリゾルバ
入力 IFC: IfcSite, IfcBuilding, IfcBuildingStorey, IfcSpace
出力 RDF: bot:Site, bot:Building, bot:Storey, bot:Space と階層関係
"""

from pathlib import Path
from typing import Optional, Dict
import re

import ifcopenshell
from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import RDF

BOT = Namespace("https://w3id.org/bot#")

def _slugify(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9_\\-]", "_", s.strip().replace(" ", "-"))

def _iri_from_name_or_guid(base_ns: str, name: Optional[str], guid: str) -> URIRef:
    local = _slugify(name) if name and name.strip() else f"equip_{guid}"
    return URIRef(f"{base_ns}{local}")

class TopologyReasoner:
    def __init__(self, base_ns: str = "https://id.morgate51.org/project#"):
        self.base_ns = base_ns
        self.M51 = Namespace(base_ns)

    def load_ifc(self, ifc_path: str):
        model = ifcopenshell.open(ifc_path)
        if str(model.schema).upper() != "IFC2X3":
            print("警告, IFC2x3 以外の可能性があるため要検討")
        return model

    def build_graph(self) -> Graph:
        g = Graph()
        g.bind("bot", BOT)
        g.bind("m51", self.M51)
        return g

    def add_node(self, g: Graph, uri: URIRef, rdf_type: URIRef, ifc_guid: str):
        g.add((uri, RDF.type, rdf_type))
        g.add((uri, self.M51.ifc_GUID, Literal(ifc_guid)))

    def extract_and_map(self, model) -> Graph:
        g = self.build_graph()

        # 1 Site
        sites = model.by_type("IfcSite")
        if len(sites) == 0:
            print("警告, IfcSite が見つからないため, 建物直下から開始する")
        site_uri = None
        if sites:
            site = sites[0]
            site_uri = _iri_from_name_or_guid(self.base_ns, getattr(site, "Name", None), site.GlobalId)
            self.add_node(g, site_uri, BOT.Site, site.GlobalId)

        # 2 Building
        buildings = model.by_type("IfcBuilding")
        guid_to_bldg_uri: Dict[str, URIRef] = {}
        for b in buildings:
            b_uri = _iri_from_name_or_guid(self.base_ns, getattr(b, "Name", None), b.GlobalId)
            self.add_node(g, b_uri, BOT.Building, b.GlobalId)
            guid_to_bldg_uri[b.GlobalId] = b_uri
            if site_uri:
                g.add((site_uri, BOT.hasBuilding, b_uri))

        # 3 Storey と 4 Space, IfcRelAggregates を辿る
        # Building -> Storey
        for b in buildings:
            b_uri = guid_to_bldg_uri[b.GlobalId]
            for rel in getattr(b, "IsDecomposedBy", []) or []:
                if rel.is_a("IfcRelDecomposes") and rel.is_a("IfcRelAggregates"):
                    for obj in rel.RelatedObjects:
                        if obj.is_a("IfcBuildingStorey"):
                            s_uri = _iri_from_name_or_guid(self.base_ns, getattr(obj, "Name", None), obj.GlobalId)
                            self.add_node(g, s_uri, BOT.Storey, obj.GlobalId)
                            g.add((b_uri, BOT.hasStorey, s_uri))

                            # Storey -> Space
                            for rel2 in getattr(obj, "IsDecomposedBy", []) or []:
                                if rel2.is_a("IfcRelAggregates"):
                                    for sp in rel2.RelatedObjects:
                                        if sp.is_a("IfcSpace"):
                                            sp_uri = _iri_from_name_or_guid(self.base_ns, getattr(sp, "Name", None), sp.GlobalId)
                                            self.add_node(g, sp_uri, BOT.Space, sp.GlobalId)
                                            g.add((s_uri, BOT.hasSpace, sp_uri))

        return g
    

# -*- coding: utf-8 -*-
"""
topology_reasoner.py

IfcFlowTerminal と IfcSpace の空間近接に基づき
equipment TTL と topology TTL を突合し brick:hasLocation を付与する

入出力
- 入力 IFC:
  1) MEP IFC: IfcFlowTerminal を抽出
  2) ARC IFC: IfcSpace を抽出し幾何から AABB を算出
- 入力 TTL:
  3) equipment.ttl
  4) topology.ttl
- 出力:
  a) merged_with_locations.ttl
  b) pairing_report.csv

依存
- ifcopenshell==0.7.0
- numpy
- rdflib
"""

import argparse
import math
import os
from typing import Dict, List, Optional, Tuple

import numpy as np
import rdflib

try:
    import ifcopenshell
    import ifcopenshell.geom as ifcgeom
except Exception as e:
    raise RuntimeError("ifcopenshell と ifcopenshell.geom のロードに失敗. prebuilt wheel の導入を確認") from e


# -----------------------------
# 単位スケールの決定
# -----------------------------
def get_length_unit_scale_to_m(ifc) -> float:
    """
    IfcProject.UnitAssignment から長さ単位のスケールをメートル基準で返す
    IFC2x3 を想定
    例: mm -> 0.001, m -> 1.0
    """
    # 既定値
    scale = 1.0
    project = ifc.by_type("IfcProject")
    if not project:
        return scale
    ua = project[0].UnitsInContext
    if not ua or not ua.Units:
        return scale
    for u in ua.Units:
        # NamedUnit かつ長さ単位
        t = getattr(u, "UnitType", None) or getattr(u, "Dimensions", None)
        # IFC2x3: 長さは IfcSIUnit か IfcConversionBasedUnit
        if getattr(u, "UnitType", None) == "LENGTHUNIT":
            # IfcSIUnit の場合
            if u.is_a("IfcSIUnit"):
                # UnitName が METRE で Prefix が MILLI など
                name = getattr(u, "Name", None) or getattr(u, "UnitName", None)
                prefix = getattr(u, "Prefix", None)
                # 既定はメートル
                scale = 1.0
                # Prefix を反映
                if prefix == "MILLI":
                    scale = 1e-3
                elif prefix == "CENTI":
                    scale = 1e-2
                elif prefix == "DECI":
                    scale = 1e-1
                elif prefix == "DECA":
                    scale = 1e1
                elif prefix == "HECTO":
                    scale = 1e2
                elif prefix == "KILO":
                    scale = 1e3
                # それ以外は METRE とみなす
                return scale
            # 変換定義単位の場合
            if u.is_a("IfcConversionBasedUnit"):
                # ConversionFactor の値からメートル換算
                cf = u.ConversionFactor
                if cf and cf.is_a("IfcMeasureWithUnit"):
                    # 測定値 × SI単位への係数
                    value_component = getattr(cf, "ValueComponent", None)
                    unit_component = getattr(cf, "UnitComponent", None)
                    # value_component は IfcReal など
                    if value_component is not None and unit_component is not None:
                        # UnitComponent が METRE 前提
                        # 例: 1.0 FOOT = 0.3048 METRE なら scale は 0.3048
                        try:
                            scale = float(value_component.wrappedValue)
                        except Exception:
                            scale = float(value_component)
                        return scale
    return scale


# -----------------------------
# 変換行列ユーティリティ
# -----------------------------
def axis2placement3d_to_matrix(ap):
    """
    IfcAxis2Placement3D を 4x4 同次変換行列に変換
    右手系 XYZ
    """
    # 位置ベクトル
    loc = ap.Location
    ox, oy, oz = loc.Coordinates
    origin = np.array([ox, oy, oz], dtype=float)

    # 方向ベクトル
    # Z軸: Axis. X軸: RefDirection. Yは外積
    z_dir = np.array([0.0, 0.0, 1.0], dtype=float)
    if getattr(ap, "Axis", None):
        z_dir = np.array(ap.Axis.DirectionRatios, dtype=float)
        z_dir = z_dir / np.linalg.norm(z_dir)

    x_dir = np.array([1.0, 0.0, 0.0], dtype=float)
    if getattr(ap, "RefDirection", None):
        x_dir = np.array(ap.RefDirection.DirectionRatios, dtype=float)
        x_dir = x_dir / np.linalg.norm(x_dir)

    # 直交化
    y_dir = np.cross(z_dir, x_dir)
    if np.linalg.norm(y_dir) < 1e-9:
        # x と z が平行な場合のフォールバック
        if abs(z_dir[2]) < 0.999:
            x_dir = np.array([1.0, 0.0, 0.0], dtype=float)
            y_dir = np.cross(z_dir, x_dir)
        else:
            x_dir = np.array([0.0, 1.0, 0.0], dtype=float)
            y_dir = np.cross(z_dir, x_dir)
    y_dir = y_dir / np.linalg.norm(y_dir)
    x_dir = np.cross(y_dir, z_dir)
    x_dir = x_dir / np.linalg.norm(x_dir)

    # 同次行列
    T = np.eye(4, dtype=float)
    T[:3, 0] = x_dir
    T[:3, 1] = y_dir
    T[:3, 2] = z_dir
    T[:3, 3] = origin
    return T


def local_placement_to_world_matrix(lp) -> np.ndarray:
    """
    IfcLocalPlacement の親参照を再帰的に辿り世界座標変換行列を得る
    """
    # 自身の相対変換
    rel = lp.RelativePlacement
    if not rel:
        T_local = np.eye(4, dtype=float)
    else:
        if rel.is_a("IfcAxis2Placement3D"):
            T_local = axis2placement3d_to_matrix(rel)
        elif rel.is_a("IfcAxis2Placement2D"):
            # 2D の場合も 3D に埋め込み
            loc = rel.Location
            ox, oy = loc.Coordinates
            T_local = np.eye(4, dtype=float)
            T_local[:3, 3] = [ox, oy, 0.0]
        else:
            T_local = np.eye(4, dtype=float)

    # 親があれば合成
    parent = lp.PlacementRelTo
    if parent:
        T_parent = local_placement_to_world_matrix(parent)
        return T_parent @ T_local
    return T_local


# -----------------------------
# IFC 抽出
# -----------------------------
def extract_flowterminals_worldpoints(ifc_path: str) -> Tuple[List[Dict], float]:
    """
    IfcFlowTerminal の代表点を世界座標で抽出
    代表点は LocalPlacement の原点を世界座標へ写像した点
    戻り値: [ {guid, name, point(np.array shape=(3,)), product_ref}, ... ], scale_to_m
    """
    ifc = ifcopenshell.open(ifc_path)
    scale_to_m = get_length_unit_scale_to_m(ifc)

    terminals = []
    # IFC2x3 では AirTerminal は IfcFlowTerminal の subtype IfcAirTerminal
    # ただしユーザ指定は "airflowterminal" だが, IFCクラス名は IfcFlowTerminal/IfcAirTerminal
    for e in ifc.by_type("IfcFlowTerminal"):
        try:
            guid = e.GlobalId
            name = getattr(e, "Name", "") or ""
            lp = e.ObjectPlacement
            if not lp or not lp.is_a("IfcLocalPlacement"):
                continue
            T = local_placement_to_world_matrix(lp)
            p = np.array([0.0, 0.0, 0.0, 1.0])
            pw = T @ p
            # 単位をメートルに正規化
            xyz_m = np.array(pw[:3], dtype=float) * scale_to_m
            terminals.append(
                {"guid": guid, "name": name, "point_m": xyz_m, "product": e}
            )
        except Exception:
            continue

    return terminals, scale_to_m


def extract_spaces_aabb(ifc_path: str) -> Tuple[List[Dict], float]:
    """
    IfcSpace のメッシュを生成し AABB を算出
    戻り値: [ {guid, name, aabb_min_m(np.array3), aabb_max_m(np.array3), centroid_m(np.array3), product}, ... ], scale_to_m
    """
    ifc = ifcopenshell.open(ifc_path)
    scale_to_m = get_length_unit_scale_to_m(ifc)

    # 幾何設定
    settings = ifcgeom.settings()
    settings.set(settings.USE_WORLD_COORDS, True)
    # 表示詳細はデフォルト. 精度問題がある場合は BREP 優先等の設定を適宜調整

    spaces = []
    for s in ifc.by_type("IfcSpace"):
        try:
            shape = ifcgeom.create_shape(settings, s)
        except Exception:
            # 幾何化に失敗したスペースはスキップ
            continue
        # verts はモデル単位. メートルに換算
        verts = np.array(shape.geometry.verts, dtype=float).reshape(-1, 3) * scale_to_m
        if verts.size == 0:
            continue
        vmin = verts.min(axis=0)
        vmax = verts.max(axis=0)
        centroid = verts.mean(axis=0)
        spaces.append(
            {
                "guid": s.GlobalId,
                "name": getattr(s, "Name", "") or "",
                "aabb_min_m": vmin,
                "aabb_max_m": vmax,
                "centroid_m": centroid,
                "product": s,
            }
        )
    return spaces, scale_to_m


# -----------------------------
# 幾何評価
# -----------------------------
def point_aabb_distance(p: np.ndarray, vmin: np.ndarray, vmax: np.ndarray) -> float:
    """
    3D 点と AABB のユークリッド最近接距離
    AABB 内であれば 0
    """
    dx = max(vmin[0] - p[0], 0.0, p[0] - vmax[0])
    dy = max(vmin[1] - p[1], 0.0, p[1] - vmax[1])
    dz = max(vmin[2] - p[2], 0.0, p[2] - vmax[2])
    return math.sqrt(dx * dx + dy * dy + dz * dz)


def pair_terminals_to_spaces(
    terminals: List[Dict],
    spaces: List[Dict],
    z_slack_m: float = 0.2,
) -> List[Dict]:
    """
    各 IfcFlowTerminal を最も近い IfcSpace に割当
    まず AABB 内包を優先し, 無ければ AABB 最近接距離の最小を採用
    z_slack_m は天井ふところ等に対する上側緩衝
    戻り値: [ {terminal_guid, space_guid, distance_m, inside, terminal_name, space_name} ]
    """
    pairs = []
    for t in terminals:
        p = t["point_m"]
        best = None
        best_d = float("inf")
        best_inside = False

        for s in spaces:
            vmin = s["aabb_min_m"].copy()
            vmax = s["aabb_max_m"].copy()
            # 上側へ緩衝
            vmax[2] += z_slack_m

            # 内包判定
            inside = (
                (vmin[0] <= p[0] <= vmax[0])
                and (vmin[1] <= p[1] <= vmax[1])
                and (vmin[2] <= p[2] <= vmax[2])
            )
            if inside:
                d = 0.0
            else:
                d = point_aabb_distance(p, vmin, vmax)

            if d < best_d or (d == best_d and inside and not best_inside):
                best_d = d
                best = s
                best_inside = inside

        if best is not None:
            pairs.append(
                {
                    "terminal_guid": t["guid"],
                    "terminal_name": t["name"],
                    "terminal_point_m": p,
                    "space_guid": best["guid"],
                    "space_name": best["name"],
                    "distance_m": best_d,
                    "inside": best_inside,
                }
            )
    return pairs


# -----------------------------
# RDF 突合と書き戻し
# -----------------------------
BRICK = rdflib.Namespace("https://brickschema.org/schema/Brick#")
PROV = rdflib.Namespace("http://www.w3.org/ns/prov#")
RDF = rdflib.RDF

DEFAULT_GUID_PRED_IRIS = [
    # よく使われる候補を列挙. 実際の TTL に合わせて CLI から上書き可
    "https://w3id.org/ifc/IFC4#globalId",
    "https://w3id.org/ifc/IFC2X3#globalId",
    "https://example.org/ifc#globalId",
    "http://example.com/ifc#guid",
    "http://schema.buildingsmart.org/ifc#globalId",
    "urn:ifc:globalId",
]


def find_resource_by_guid(
    g: rdflib.Graph, guid: str, guid_pred_iris: List[str]
) -> Optional[rdflib.term.Identifier]:
    """
    GUID リテラル一致でリソースを探索
    大文字小文字は区別しない
    """
    guid_lower = guid.lower()
    for pred_iri in guid_pred_iris:
        pred = rdflib.URIRef(pred_iri)
        for s, p, o in g.triples((None, pred, None)):
            if isinstance(o, rdflib.Literal) and str(o).lower() == guid_lower:
                return s
    # フォールバック: 任意プロパティに GUID 文字列が含まれる場合
    for s, p, o in g.triples((None, None, None)):
        if isinstance(o, rdflib.Literal) and str(o).lower() == guid_lower:
            return s
    return None


def merge_ttls_and_add_locations(
    topology_ttl: str,
    equipment_ttl: str,
    pairs: List[Dict],
    guid_pred_iris: List[str],
    out_ttl: str,
    report_csv: str,
):
    g = rdflib.Graph()
    g.parse(topology_ttl, format="turtle")
    g.parse(equipment_ttl, format="turtle")

    # 追加トリプルと監査レコード
    rows = []
    for rec in pairs:
        term_guid = rec["terminal_guid"]
        space_guid = rec["space_guid"]

        subj = find_resource_by_guid(g, term_guid, guid_pred_iris)
        obj = find_resource_by_guid(g, space_guid, guid_pred_iris)

        method = "inside_aabb" if rec["inside"] else "nearest_aabb"
        dist_mm = rec["distance_m"] * 1000.0

        if subj is None or obj is None:
            rows.append(
                [
                    term_guid,
                    str(subj) if subj else "",
                    rec["terminal_name"],
                    space_guid,
                    str(obj) if obj else "",
                    rec["space_name"],
                    f"{dist_mm:.1f}",
                    method,
                    "unresolved_uri",
                ]
            )
            continue

        # brick:hasLocation を追加
        g.add((subj, BRICK.hasLocation, obj))
        # 由来の記録
        g.add((subj, PROV.wasDerivedFrom, rdflib.Literal(f"ifc://{term_guid}")))
        g.add((obj, PROV.wasDerivedFrom, rdflib.Literal(f"ifc://{space_guid}")))

        rows.append(
            [
                term_guid,
                str(subj),
                rec["terminal_name"],
                space_guid,
                str(obj),
                rec["space_name"],
                f"{dist_mm:.1f}",
                method,
                "ok",
            ]
        )

    # TTL 出力
    g.serialize(destination=out_ttl, format="turtle")

    # CSV 出力
    import csv

    os.makedirs(os.path.dirname(report_csv), exist_ok=True)
    with open(report_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "terminal_guid",
                "terminal_uri",
                "terminal_name",
                "space_guid",
                "space_uri",
                "space_name",
                "distance_mm",
                "method",
                "status",
            ]
        )
        w.writerows(rows)

# -*- coding: utf-8 -*-
"""
jupyterbook_adapter.py

Jupyter Book上で IfcFlowTerminal と IfcSpace の最近傍関係を推定し
equipment と topology のTTLを統合して brick:hasLocation を付与するための
関数型インターフェイスを提供する

依存
- ifcopenshell
- numpy
- rdflib
- pandas
"""

from typing import List, Dict, Tuple, Optional
import os
import numpy as np
import rdflib
import pandas as pd

# 既存モジュール側の関数をインポートする想定
# from topology_reasoner import (
#     extract_flowterminals_worldpoints,
#     extract_spaces_aabb,
#     pair_terminals_to_spaces,
#     find_resource_by_guid,
#     DEFAULT_GUID_PRED_IRIS,
#     BRICK, PROV
# )

# ここでは, 既出の定義をそのまま使用する前提
BRICK = rdflib.Namespace("https://brickschema.org/schema/Brick#")
PROV = rdflib.Namespace("http://www.w3.org/ns/prov#")
RDF = rdflib.RDF

DEFAULT_GUID_PRED_IRIS = [
    "https://w3id.org/ifc/IFC4#globalId",
    "https://w3id.org/ifc/IFC2X3#globalId",
    "https://example.org/ifc#globalId",
    "http://example.com/ifc#guid",
    "http://schema.buildingsmart.org/ifc#globalId",
    "urn:ifc:globalId",
]


def merge_graphs_and_add_locations_in_memory(
    topology_ttl_path: str,
    equipment_ttl_path: str,
    pairs: List[Dict],
    guid_pred_iris: List[str],
) -> Tuple[rdflib.Graph, pd.DataFrame]:
    """
    topology.ttl と equipment.ttl を読み込み1つのGraphへ統合し,
    ペア情報に基づいて brick:hasLocation を追加する
    監査情報は DataFrame で返す
    """
    g = rdflib.Graph()
    g.parse(topology_ttl_path, format="turtle")
    g.parse(equipment_ttl_path, format="turtle")

    def _find_resource_by_guid(
        g_: rdflib.Graph, guid: str, pred_iris: List[str]
    ) -> Optional[rdflib.term.Identifier]:
        guid_lower = guid.lower()
        # 明示述語検索
        for iri in pred_iris:
            pred = rdflib.URIRef(iri)
            for s, p, o in g_.triples((None, pred, None)):
                if isinstance(o, rdflib.Literal) and str(o).lower() == guid_lower:
                    return s
        # フォールバック
        for s, p, o in g_.triples((None, None, None)):
            if isinstance(o, rdflib.Literal) and str(o).lower() == guid_lower:
                return s
        return None

    rows = []
    for rec in pairs:
        term_guid = rec["terminal_guid"]
        space_guid = rec["space_guid"]

        subj = _find_resource_by_guid(g, term_guid, guid_pred_iris)
        obj = _find_resource_by_guid(g, space_guid, guid_pred_iris)

        method = "inside_aabb" if rec["inside"] else "nearest_aabb"
        dist_mm = rec["distance_m"] * 1000.0

        status = "ok"
        if subj is None or obj is None:
            status = "unresolved_uri"
        else:
            # triple 追加
            g.add((subj, BRICK.hasLocation, obj))
            # 由来
            g.add((subj, PROV.wasDerivedFrom, rdflib.Literal(f"ifc://{term_guid}")))
            g.add((obj, PROV.wasDerivedFrom, rdflib.Literal(f"ifc://{space_guid}")))

        rows.append(
            {
                "terminal_guid": term_guid,
                "terminal_uri": str(subj) if subj else "",
                "terminal_name": rec.get("terminal_name", ""),
                "space_guid": space_guid,
                "space_uri": str(obj) if obj else "",
                "space_name": rec.get("space_name", ""),
                "distance_mm": round(dist_mm, 1),
                "method": method,
                "status": status,
            }
        )

    df = pd.DataFrame(rows)
    return g, df


def run_pairing(
    mep_ifc_path: str,
    arc_ifc_path: str,
    topology_ttl_path: str,
    equipment_ttl_path: str,
    z_slack_m: float = 0.2,
    guid_pred_iris: Optional[List[str]] = None,
    write_ttl: bool = False,
    out_ttl_path: Optional[str] = None,
    write_csv: bool = False,
    report_csv_path: Optional[str] = None,
):
    """
    Jupyter Book対応のエントリポイント
    1. IFCから IfcFlowTerminal と IfcSpace を抽出
    2. 近接ベースでペアリング
    3. RDF統合と brick:hasLocation 追加
    4. Graph と DataFrame を返す
    5. 必要に応じてTTLとCSVを書出す

    Returns
    -------
    g : rdflib.Graph
        位置リンク追加後の統合グラフ
    df : pandas.DataFrame
        監査レポート. 列 terminal_guid, terminal_uri, terminal_name, space_guid, space_uri, space_name, distance_mm, method, status
    pairs : List[Dict]
        幾何ペアリングの生データ
    """
    if guid_pred_iris is None:
        guid_pred_iris = DEFAULT_GUID_PRED_IRIS

    # 既存関数の呼出を想定
    terminals, _ = extract_flowterminals_worldpoints(mep_ifc_path)
    spaces, _ = extract_spaces_aabb(arc_ifc_path)

    if len(terminals) == 0:
        raise RuntimeError("IfcFlowTerminal が抽出できなかった")
    if len(spaces) == 0:
        raise RuntimeError("IfcSpace が抽出できなかった")

    pairs = pair_terminals_to_spaces(terminals, spaces, z_slack_m=z_slack_m)

    g, df = merge_graphs_and_add_locations_in_memory(
        topology_ttl_path=topology_ttl_path,
        equipment_ttl_path=equipment_ttl_path,
        pairs=pairs,
        guid_pred_iris=guid_pred_iris,
    )

    if write_ttl:
        if not out_ttl_path:
            raise ValueError("write_ttl=True の場合 out_ttl_path が必要")
        os.makedirs(os.path.dirname(out_ttl_path), exist_ok=True)
        g.serialize(destination=out_ttl_path, format="turtle")

    if write_csv:
        if not report_csv_path:
            raise ValueError("write_csv=True の場合 report_csv_path が必要")
        os.makedirs(os.path.dirname(report_csv_path), exist_ok=True)
        df.to_csv(report_csv_path, index=False, encoding="utf-8")

    return g, df, pairs