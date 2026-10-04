from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Dict, Optional

from models import (
    BdnsTaggedAsset,
    BdnsTaggedAssets,
    BrickEquipment,
    BrickEquipmentSet,
    IfcBundle,
)


DEFAULT_FALLBACK_BRICK_CLASS = "brick:Equipment"


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def default_mapping_path() -> Path:
    candidates = [
        _project_root() / "resources" / "mappings" / "bdns_assets_to_brick_map.csv",
        _project_root() / "data" / "resources" / "bdns_assets_to_brick_map.csv",
    ]
    for path in candidates:
        if path.is_file():
            return path
    return candidates[0]


def _normalize_code(value: Optional[str]) -> str:
    return (value or "").strip().upper()


def _extract_name_prefix(name: Optional[str]) -> str:
    match = re.match(r"^([A-Za-z]+)", (name or "").strip())
    return match.group(1).upper() if match else ""


def _find_bdns_classification(model):
    for item in model.by_type("IfcClassification"):
        name = getattr(item, "Name", None)
        if isinstance(name, str) and name.strip().upper() == "BDNS":
            return item
    return None


def extract_bdns_tags(bundle: IfcBundle) -> BdnsTaggedAssets:
    bdns_classification = _find_bdns_classification(bundle.model)
    if bdns_classification is None:
        return BdnsTaggedAssets(items=[])

    references: Dict[object, str] = {}
    for ref in bundle.model.by_type("IfcClassificationReference"):
        if getattr(ref, "ReferencedSource", None) != bdns_classification:
            continue
        code = getattr(ref, "Identification", None) or getattr(ref, "Name", None)
        if code:
            references[ref] = str(code).strip()

    assets = []
    for rel in bundle.model.by_type("IfcRelAssociatesClassification"):
        code = references.get(getattr(rel, "RelatingClassification", None))
        if not code:
            continue

        for obj in getattr(rel, "RelatedObjects", None) or []:
            guid = getattr(obj, "GlobalId", None)
            if guid is None:
                continue
            name = getattr(obj, "Name", None)
            ifc_class = obj.is_a() if hasattr(obj, "is_a") else None
            assets.append(
                BdnsTaggedAsset(
                    ifc_guid=str(guid),
                    name=str(name) if name is not None else None,
                    bdns_tag=code,
                    raw_ifc_class=str(ifc_class) if ifc_class else None,
                )
            )

    return BdnsTaggedAssets(items=assets)


def load_project_crosswalk(path: str | Path | None = None) -> Dict[str, dict]:
    mapping_path = Path(path) if path is not None else default_mapping_path()
    if not mapping_path.is_file():
        return {}

    result: Dict[str, dict] = {}
    with mapping_path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            code = _normalize_code(
                row.get("bdns_abbriviation") or row.get("bdns_abbreviation")
            )
            brick_class = (row.get("brick_class_candidate") or "").strip()
            if not code or not brick_class:
                continue
            result[code] = {
                "brick_class": brick_class,
                "source": "project-defined",
                "bdns_label": (row.get("bdns_tag") or "").strip() or None,
                "raw_ifc_class": (row.get("raw_ifc_class") or "").strip() or None,
            }
    return result


def map_bdns_to_brick(
    tagged_assets: BdnsTaggedAssets,
    mapping_csv_path: str | Path | None = None,
    authoritative_mapping: Optional[Dict[str, dict]] = None,
) -> BrickEquipmentSet:
    """
    Map BDNS-tagged IFC assets to Brick classes.

    Mapping priority:
    1. externally supplied authoritative mapping
    2. project-defined research crosswalk
    3. review-required fallback to brick:Equipment

    The module does not assume that a public mapping exists. External mappings
    should be supplied only after their source and applicability are verified.
    """
    project_mapping = load_project_crosswalk(mapping_csv_path)
    authoritative_mapping = authoritative_mapping or {}

    equipments = []
    for asset in tagged_assets.items:
        code = _normalize_code(asset.bdns_tag) or _extract_name_prefix(asset.name)
        record = authoritative_mapping.get(code)
        mapping_status = "authoritative"
        mapping_source = None

        if record:
            brick_class = str(record.get("brick_class") or "").strip()
            mapping_source = record.get("source")
        else:
            record = project_mapping.get(code)
            mapping_status = "project-defined"
            if record:
                brick_class = str(record.get("brick_class") or "").strip()
                mapping_source = record.get("source")
            else:
                brick_class = DEFAULT_FALLBACK_BRICK_CLASS
                mapping_status = "review_required"
                mapping_source = None

        label = (asset.name or "").strip() or f"{code or 'equipment'}_{asset.ifc_guid[:8]}"
        equipments.append(
            BrickEquipment(
                ifc_guid=asset.ifc_guid,
                brick_class=brick_class or DEFAULT_FALLBACK_BRICK_CLASS,
                label=label,
                bdns_tag=code or asset.bdns_tag,
                extra_props={
                    "raw_ifc_class": asset.raw_ifc_class,
                    "bdns_label": asset.bdns_tag,
                    "mapping_status": mapping_status,
                    "mapping_source": mapping_source,
                },
            )
        )

    return BrickEquipmentSet(items=equipments)
