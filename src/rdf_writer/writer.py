# src/rdf_writer/writer.py
from __future__ import annotations

from pathlib import Path
from typing import Any, Optional
import logging
import re

from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import RDF, RDFS

from app.contracts import BrickGraph, BrickEquipment, BrickEquipmentSet

BRICK = Namespace("https://brickschema.org/schema/Brick#")
TAG = Namespace("https://brickschema.org/schema/BrickTag#")
# プロジェクト命名空間は build_graph_from_equipments で 'm51' として bind する

def _ns_ex(base_ns: str) -> Namespace:
    return Namespace(base_ns)

def _slugify_label(label: str) -> str:
    # label から IRI のローカル名として安全なスラッグを生成
    return re.sub(r"[^A-Za-z0-9_\-]", "_", label.strip().replace(" ", "-"))

def _to_subject_iri(base_ns: str, label: Optional[str], guid: str) -> URIRef:
    # label を優先, 欠損時は equip_<GUID>
    local = _slugify_label(label) if label else f"equip_{guid}"
    return URIRef(f"{base_ns}{local}")

def _resolve_brick_class(curie_or_uri: str) -> URIRef:
    """
    Composite safe resolver for Brick classes.
    複合文字列を想定し '|' ',' ';' で分割して brick:CURIE を優先, 次にフル Brick IRI を選択
    """
    s = (curie_or_uri or "").strip()
    if not s:
        logging.warning("brick_class is empty, defaulting to brick:Equipment")
        return BRICK["Equipment"]

    tokens = [t.strip() for t in re.split(r"[|,;]", s) if t.strip()]
    for t in tokens:
        if t.startswith("brick:"):
            return BRICK[t[len("brick:"):]]
    brick_ns = str(BRICK)
    for t in tokens:
        if t.startswith(brick_ns):
            return URIRef(t)
    if s.startswith("brick:"):
        return BRICK[s[len("brick:"):]]
    return URIRef(s)

def _add_equipment_triples(g: Graph, eq: BrickEquipment, base_ns: str) -> None:
    """
    新仕様に基づくトリプル付与
    1 主語 IRI は label を優先してローカル名に採用, 欠損時は equip_<GUID>
    2 rdfs:label は出力しない
    3 brick:hasTag は出力しない
    4 brick:hasIdentifier は出力しない, m51:ifc_GUID を出力
    5 extra_props.bdns_label は m51:asset_description に出力, mapping_source は不出力
    """
    m51 = _ns_ex(base_ns)
    subj = _to_subject_iri(base_ns, getattr(eq, "label", None), eq.ifc_guid)

    # rdf:type
    g.add((subj, RDF.type, _resolve_brick_class(eq.brick_class)))

    # IFC GUID をプロジェクト語彙で保持
    g.add((subj, m51.ifc_GUID, Literal(eq.ifc_guid)))

    # 追加メタ
    if eq.extra_props:
        ifc_cls = eq.extra_props.get("raw_ifc_class")
        if ifc_cls:
            g.add((subj, m51.ifc_class, Literal(ifc_cls)))
        bdns_label = eq.extra_props.get("bdns_label")
        if bdns_label:
            g.add((subj, m51.asset_description, Literal(bdns_label)))
        # mapping_source は不出力
        unmapped = eq.extra_props.get("unmapped")
        if unmapped is True:
            g.add((subj, m51.unmapped, Literal(True)))

def build_graph_from_equipments(equip_set: BrickEquipmentSet, base_ns: str) -> BrickGraph:
    g = Graph()
    g.bind("rdf", RDF)
    g.bind("rdfs", RDFS)
    g.bind("brick", BRICK)
    g.bind("tag", TAG)
    g.bind("m51", Namespace(base_ns))
    for eq in equip_set.items:
        _add_equipment_triples(g, eq, base_ns)
    return BrickGraph(graph_obj=g)

def write_turtle(bg: BrickGraph, out_ttl: str | Path) -> None:
    out_path = Path(out_ttl)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    g: Graph = bg.graph_obj
    g.serialize(destination=str(out_path), format="turtle")

def write_equipments_turtle(equip_set: BrickEquipmentSet, base_ns: str, out_ttl: str | Path) -> None:
    bg = build_graph_from_equipments(equip_set, base_ns)
    write_turtle(bg, out_ttl)


from pathlib import Path
from rdflib import Graph

def merge_ttl_files(
    ttl_dir: str | Path,
    output_path: str | Path | None = None
) -> Graph:
    """
    指定ディレクトリ配下のTTLファイルをすべて読み込み,
    RDFグラフとしてマージする関数
    """

    ttl_dir = Path(ttl_dir)
    graph = Graph()

    for ttl_file in ttl_dir.glob("*.ttl"):
        graph.parse(ttl_file, format="turtle")

    if output_path is not None:
        graph.serialize(destination=str(output_path), format="turtle")

    return graph
