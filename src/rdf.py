from __future__ import annotations

import csv
from pathlib import Path

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, RDFS

from models import BrickEquipmentSet, BrickGraph, BrickPointsSet, RelationSet, SpatialElements
from reasoning import equipment_iri, spatial_iri


BRICK = Namespace("https://brickschema.org/schema/Brick#")
BOT = Namespace("https://w3id.org/bot#")
QUDT_UNIT = Namespace("http://qudt.org/vocab/unit/")


def _resolve_curie(value: str) -> URIRef:
    if value.startswith("brick:"):
        return BRICK[value.split(":", 1)[1]]
    if value.startswith("bot:"):
        return BOT[value.split(":", 1)[1]]
    if value.startswith("http://") or value.startswith("https://"):
        return URIRef(value)
    raise ValueError(f"Unsupported RDF identifier: {value}")


def _unit_iri(unit: str | None):
    if not unit:
        return None
    key = unit.strip().lower()
    mapping = {
        "degc": QUDT_UNIT["DEG_C"],
        "pa": QUDT_UNIT["PA"],
        "m3/s": QUDT_UNIT["M3-PER-SEC"],
        "m³/s": QUDT_UNIT["M3-PER-SEC"],
        "ppm": QUDT_UNIT["PPM"],
        "%": QUDT_UNIT["PERCENT"],
        "percent": QUDT_UNIT["PERCENT"],
        "%rh": QUDT_UNIT["PERCENT"],
        "rh": QUDT_UNIT["PERCENT"],
    }
    return mapping.get(key)


def build_graph(
    spatial_elements: SpatialElements,
    equipments: BrickEquipmentSet,
    points: BrickPointsSet,
    relations: RelationSet,
    base_ns: str,
) -> BrickGraph:
    graph = Graph()
    project = Namespace(base_ns)

    graph.bind("brick", BRICK)
    graph.bind("bot", BOT)
    graph.bind("qudt-unit", QUDT_UNIT)
    graph.bind("project", project)
    graph.bind("rdf", RDF)
    graph.bind("rdfs", RDFS)

    spatial_classes = {
        "IfcSite": BOT.Site,
        "IfcBuilding": BOT.Building,
        "IfcBuildingStorey": BOT.Storey,
        "IfcSpace": BOT.Space,
    }

    for item in spatial_elements.items:
        subject = URIRef(spatial_iri(base_ns, item.raw_ifc_class, item.ifc_guid))
        graph.add((subject, RDF.type, spatial_classes[item.raw_ifc_class]))
        if item.name:
            graph.add((subject, RDFS.label, Literal(item.name)))
        graph.add((subject, project.ifc_GUID, Literal(item.ifc_guid)))

    for equipment in equipments.items:
        subject = URIRef(equipment_iri(base_ns, equipment.label, equipment.ifc_guid))
        graph.add((subject, RDF.type, _resolve_curie(equipment.brick_class)))
        graph.add((subject, project.ifc_GUID, Literal(equipment.ifc_guid)))
        if equipment.label:
            graph.add((subject, RDFS.label, Literal(equipment.label)))
        if equipment.bdns_tag:
            graph.add((subject, project.bdns_tag, Literal(equipment.bdns_tag)))
        status = equipment.extra_props.get("mapping_status")
        source = equipment.extra_props.get("mapping_source")
        if status:
            graph.add((subject, project.mapping_status, Literal(status)))
        if source:
            graph.add((subject, project.mapping_source, Literal(source)))

    for point in points.items:
        subject = URIRef(point.brick_point_iri)
        graph.add((subject, RDF.type, _resolve_curie(point.extra_props.get("brick_class", "brick:Point"))))
        graph.add((subject, RDFS.label, Literal(point.point_name)))
        unit = _unit_iri(point.unit)
        if unit is not None:
            graph.add((subject, BRICK.hasUnit, unit))

    for relation in relations.items:
        graph.add((
            URIRef(relation.subject),
            _resolve_curie(relation.predicate),
            URIRef(relation.object),
        ))

    return BrickGraph(graph_obj=graph)


def write_turtle(graph: BrickGraph, output_path: str | Path) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    graph.graph_obj.serialize(destination=str(path), format="turtle")


def write_provenance(
    equipments: BrickEquipmentSet,
    relations: RelationSet,
    output_path: str | Path,
) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["record_type", "subject", "predicate_or_class", "object", "source"])

        for equipment in equipments.items:
            writer.writerow([
                "mapping",
                equipment.ifc_guid,
                equipment.brick_class,
                "",
                equipment.extra_props.get("mapping_source")
                or equipment.extra_props.get("mapping_status"),
            ])

        for relation in relations.items:
            writer.writerow([
                "relation",
                relation.subject,
                relation.predicate,
                relation.object,
                relation.source,
            ])
