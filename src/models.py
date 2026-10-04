from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class IfcBundle:
    schema: str
    source_path: str
    model: Any


@dataclass(frozen=True)
class SpatialElement:
    ifc_guid: str
    name: Optional[str]
    raw_ifc_class: str
    composition_type: Optional[str] = None
    elevation: Optional[float] = None
    parent_guid: Optional[str] = None
    path: Optional[str] = None


@dataclass(frozen=True)
class SpatialElements:
    items: List[SpatialElement]


@dataclass(frozen=True)
class BdnsTaggedAsset:
    ifc_guid: str
    name: Optional[str]
    bdns_tag: str
    raw_ifc_class: Optional[str]


@dataclass(frozen=True)
class BdnsTaggedAssets:
    items: List[BdnsTaggedAsset]


@dataclass(frozen=True)
class BrickEquipment:
    ifc_guid: str
    brick_class: str
    label: Optional[str] = None
    bdns_tag: Optional[str] = None
    extra_props: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class BrickEquipmentSet:
    items: List[BrickEquipment]


@dataclass(frozen=True)
class PointRow:
    point_name: str
    equipment_ref: Optional[str]
    kind: Optional[str]
    unit: Optional[str]
    raw: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PointTable:
    rows: List[PointRow]


@dataclass(frozen=True)
class BrickPoint:
    brick_point_iri: str
    point_name: str
    linked_equipment_guid: Optional[str] = None
    kind: Optional[str] = None
    unit: Optional[str] = None
    extra_props: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class BrickPointsSet:
    items: List[BrickPoint]


@dataclass(frozen=True)
class Relation:
    subject: str
    predicate: str
    object: str
    source: Optional[str] = None


@dataclass(frozen=True)
class RelationSet:
    items: List[Relation]


@dataclass(frozen=True)
class BrickGraph:
    graph_obj: Any
