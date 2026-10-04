from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from models import BrickEquipmentSet, BrickGraph


def validate_graph(
    graph: BrickGraph,
    equipments: BrickEquipmentSet,
) -> Dict[str, Any]:
    """
    Run only project checks that are currently defined.

    Full SHACL constraints remain under development. Undefined constraints are
    reported as TODO rather than inferred.
    """
    review_required = [
        equipment.ifc_guid
        for equipment in equipments.items
        if equipment.extra_props.get("mapping_status") == "review_required"
    ]

    return {
        "conforms": len(review_required) == 0,
        "triple_count": len(graph.graph_obj),
        "review_required_mappings": review_required,
        "shacl_status": "TODO",
    }


def write_validation_report(report: Dict[str, Any], output_path: str | Path) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
