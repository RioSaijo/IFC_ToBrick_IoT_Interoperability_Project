from __future__ import annotations

from pathlib import Path
from typing import Optional

import ifcopenshell

from models import IfcBundle, SpatialElement, SpatialElements


_SPATIAL_CLASSES = ("IfcSite", "IfcBuilding", "IfcBuildingStorey", "IfcSpace")


def _detect_schema(model: "ifcopenshell.file") -> str:
    for attr in ("schema", "schema_name", "schema_identifier"):
        value = getattr(model, attr, None)
        if isinstance(value, str) and value:
            return value.upper()
    return "UNKNOWN"


def load_ifc(ifc_path: str | Path) -> IfcBundle:
    path = Path(ifc_path)
    if not path.is_file():
        raise FileNotFoundError(f"IFC file not found: {path}")

    try:
        model = ifcopenshell.open(str(path))
    except Exception as exc:
        raise RuntimeError(f"Failed to open IFC file: {path}") from exc

    return IfcBundle(
        schema=_detect_schema(model),
        source_path=str(path.resolve()),
        model=model,
    )


def _parent_of(obj) -> Optional[object]:
    for rel in getattr(obj, "Decomposes", None) or []:
        if rel.is_a("IfcRelAggregates"):
            return getattr(rel, "RelatingObject", None)
    return None


def _guid(obj) -> Optional[str]:
    value = getattr(obj, "GlobalId", None)
    return str(value) if value is not None else None


def _name(obj) -> Optional[str]:
    value = getattr(obj, "Name", None)
    return str(value) if value is not None else None


def _build_path(obj) -> str:
    chain = []
    current = obj

    while current is not None:
        chain.append(current)
        current = _parent_of(current)

    labels = []
    for item in reversed(chain):
        cls = item.is_a() if hasattr(item, "is_a") else type(item).__name__
        label = _name(item) or _guid(item) or "unknown"
        labels.append(f"{cls}[{label}]")

    return "/".join(labels)


def extract_spatial_elements(bundle: IfcBundle) -> SpatialElements:
    items = []

    for ifc_class in _SPATIAL_CLASSES:
        for obj in bundle.model.by_type(ifc_class):
            guid = _guid(obj)
            if guid is None:
                continue

            parent = _parent_of(obj)
            elevation = None
            if ifc_class == "IfcBuildingStorey":
                value = getattr(obj, "Elevation", None)
                elevation = float(value) if value is not None else None

            composition = getattr(obj, "CompositionType", None)

            items.append(
                SpatialElement(
                    ifc_guid=guid,
                    name=_name(obj),
                    raw_ifc_class=ifc_class,
                    composition_type=str(composition) if composition is not None else None,
                    elevation=elevation,
                    parent_guid=_guid(parent) if parent is not None else None,
                    path=_build_path(obj),
                )
            )

    return SpatialElements(items=items)
