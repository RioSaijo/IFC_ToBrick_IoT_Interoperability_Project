from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from ifc import extract_spatial_elements, load_ifc
from mapping import extract_bdns_tags, map_bdns_to_brick
from points import load_points_csv, map_points
from rdf import build_graph, write_provenance, write_turtle
from reasoning import infer_relations
from validation import validate_graph, write_validation_report


DEFAULT_BASE_NS = "https://example.org/building#"


def run_pipeline(
    ifc_path: str | Path,
    points_csv: str | Path,
    output_dir: str | Path,
    base_ns: str = DEFAULT_BASE_NS,
    mapping_csv_path: str | Path | None = None,
    authoritative_mapping: Optional[dict] = None,
) -> Dict[str, Any]:
    output_dir = Path(output_dir)

    bundle = load_ifc(ifc_path)
    spatial = extract_spatial_elements(bundle)

    tagged_assets = extract_bdns_tags(bundle)
    equipments = map_bdns_to_brick(
        tagged_assets,
        mapping_csv_path=mapping_csv_path,
        authoritative_mapping=authoritative_mapping,
    )

    point_table = load_points_csv(points_csv)
    points = map_points(point_table, base_ns=base_ns)

    relations = infer_relations(
        spatial_elements=spatial,
        equipments=equipments,
        points=points,
        base_ns=base_ns,
    )

    graph = build_graph(
        spatial_elements=spatial,
        equipments=equipments,
        points=points,
        relations=relations,
        base_ns=base_ns,
    )

    ttl_path = output_dir / "building_brick.ttl"
    provenance_path = output_dir / "provenance.csv"
    validation_path = output_dir / "validation_report.json"

    write_turtle(graph, ttl_path)
    write_provenance(equipments, relations, provenance_path)

    validation = validate_graph(graph, equipments)
    write_validation_report(validation, validation_path)

    return {
        "ifc_schema": bundle.schema,
        "equipment_count": len(equipments.items),
        "point_count": len(points.items),
        "relation_count": len(relations.items),
        "outputs": {
            "ttl": str(ttl_path),
            "provenance": str(provenance_path),
            "validation": str(validation_path),
        },
        "validation": validation,
    }
