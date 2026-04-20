from __future__ import annotations
from typing import Dict, Any
from app.contracts import BrickGraph
from ifc_ingestor.ingestor import load_ifc_bundle
from bdns_extractor.extractor import extract_bdns_tags
from class_mapper.mapper import map_bdns_to_brick_equipment
from points_csv_ingestor.loader import load_points_csv
from points_linker.linker import link_points_to_equipment
from topology_reasoner.reasoner import build_graph
from rdf_writer.writer import write_turtle

def run_all(
    ifc_path: str,
    points_csv: str,
    base_ns: str,
    out_ttl: str,
    csvw_metadata_path: str | None = None,
    crosswalk_equip: dict | None = None,
    crosswalk_points: dict | None = None,
) -> Dict[str, Any]:
    crosswalk_equip = crosswalk_equip or {}
    crosswalk_points = crosswalk_points or {}

    bundle = load_ifc_bundle(ifc_path)
    tagged = extract_bdns_tags(bundle)
    equip_set = map_bdns_to_brick_equipment(tagged, base_ns, crosswalk_equip)
    pt_table = load_points_csv(points_csv, csvw_metadata_path)
    pt_set = link_points_to_equipment(pt_table, equip_set, base_ns, crosswalk_points)
    bg: BrickGraph = build_graph(bundle, equip_set, pt_set, base_ns)
    write_turtle(bg, out_ttl)
    return {"out": out_ttl}


