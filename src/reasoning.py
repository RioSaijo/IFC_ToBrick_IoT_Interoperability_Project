from __future__ import annotations

import re

from models import BrickEquipmentSet, BrickPointsSet, Relation, RelationSet, SpatialElements


def _safe_local(value: str) -> str:
    local = re.sub(r"[^A-Za-z0-9_\-]", "_", value)
    return local if re.match(r"^[A-Za-z_]", local) else f"X_{local}"


def equipment_iri(base_ns: str, label: str | None, guid: str) -> str:
    local = _safe_local(label) if label else f"equipment_{guid}"
    return f"{base_ns}{local}"


def spatial_iri(base_ns: str, ifc_class: str, guid: str) -> str:
    return f"{base_ns}{_safe_local(ifc_class)}_{guid}"


def infer_relations(
    spatial_elements: SpatialElements,
    equipments: BrickEquipmentSet,
    points: BrickPointsSet,
    base_ns: str,
) -> RelationSet:
    relations = []
    spatial_by_guid = {item.ifc_guid: item for item in spatial_elements.items}

    for item in spatial_elements.items:
        if not item.parent_guid or item.parent_guid not in spatial_by_guid:
            continue

        parent = spatial_by_guid[item.parent_guid]
        predicate = "brick:hasPart"
        if item.raw_ifc_class == "IfcBuilding":
            predicate = "bot:hasBuilding"
        elif item.raw_ifc_class == "IfcBuildingStorey":
            predicate = "bot:hasStorey"
        elif item.raw_ifc_class == "IfcSpace":
            predicate = "bot:hasSpace"

        relations.append(
            Relation(
                subject=spatial_iri(base_ns, parent.raw_ifc_class, parent.ifc_guid),
                predicate=predicate,
                object=spatial_iri(base_ns, item.raw_ifc_class, item.ifc_guid),
                source="IfcRelAggregates",
            )
        )

    equipment_by_ref = {}
    for equipment in equipments.items:
        iri = equipment_iri(base_ns, equipment.label, equipment.ifc_guid)
        for key in (equipment.bdns_tag, equipment.label):
            if key:
                equipment_by_ref[str(key).strip().upper()] = iri

    for point in points.items:
        equipment_ref = point.extra_props.get("equipment_ref")
        if equipment_ref:
            target = equipment_by_ref.get(str(equipment_ref).strip().upper())
            if target:
                relations.append(
                    Relation(
                        subject=target,
                        predicate="brick:hasPoint",
                        object=point.brick_point_iri,
                        source="BMS/IoT point metadata",
                    )
                )

        space_id = point.extra_props.get("space_id")
        if space_id:
            matching = next(
                (
                    item
                    for item in spatial_elements.items
                    if item.raw_ifc_class == "IfcSpace"
                    and (
                        item.ifc_guid == space_id
                        or (item.name or "").strip() == str(space_id).strip()
                    )
                ),
                None,
            )
            if matching:
                relations.append(
                    Relation(
                        subject=point.brick_point_iri,
                        predicate="brick:hasLocation",
                        object=spatial_iri(base_ns, matching.raw_ifc_class, matching.ifc_guid),
                        source="BMS/IoT point metadata",
                    )
                )

    return RelationSet(items=relations)
