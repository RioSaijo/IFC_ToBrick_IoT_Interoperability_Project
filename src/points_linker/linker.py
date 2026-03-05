from typing import Dict
from app.contracts import PointTable, BrickEquipmentSet, BrickPointsSet

def link_points_to_equipment(
    table: PointTable,
    equip_set: BrickEquipmentSet,
    base_ns: str,
    point_crosswalk: Dict
) -> BrickPointsSet:
    # minimal placeholder. later we will resolve equipment and mint point IRIs
    return BrickPointsSet(items=[])
