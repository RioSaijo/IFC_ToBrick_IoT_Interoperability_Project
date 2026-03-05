from rdflib import Graph
from app.contracts import IfcBundle, BrickEquipmentSet, BrickPointsSet, BrickGraph

def build_graph(
    bundle: IfcBundle,
    equip: BrickEquipmentSet,
    points: BrickPointsSet,
    base_ns: str
) -> BrickGraph:
    # minimal placeholder. later we will assert hasLocation and feeds
    g = Graph()
    return BrickGraph(graph_obj=g)
