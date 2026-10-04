from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Optional

from models import BrickPoint, BrickPointsSet, PointRow, PointTable


def _clean(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in {"none", "nan", "null"}:
        return None
    return text


def _safe_local(value: str) -> str:
    local = re.sub(r"[^A-Za-z0-9_\-]", "_", value)
    return local if re.match(r"^[A-Za-z_]", local) else f"X_{local}"


def load_points_csv(csv_path: str | Path) -> PointTable:
    path = Path(csv_path)
    if not path.is_file():
        raise FileNotFoundError(f"Point CSV not found: {path}")

    rows = []
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        required = {"point_id", "name", "unit", "bdns_abbreviation", "space_id"}
        missing = required.difference(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Missing point CSV columns: {sorted(missing)}")

        for raw in reader:
            point_id = _clean(raw.get("point_id"))
            if point_id is None:
                continue

            name = _clean(raw.get("name")) or f"sensor_{point_id}"
            rows.append(
                PointRow(
                    point_name=name,
                    equipment_ref=_clean(raw.get("bdns_abbreviation")),
                    kind="sensor",
                    unit=_clean(raw.get("unit")),
                    raw={key: _clean(value) for key, value in raw.items()},
                )
            )

    return PointTable(rows=rows)


def infer_brick_point_class(name: str) -> str:
    text = name.lower()

    if "occupancy" in text or "在室" in text:
        return "brick:Occupancy_Sensor"
    if "co2" in text:
        if any(token in text for token in ("return", "rat", "還気")):
            return "brick:Return_Air_CO2_Sensor"
        return "brick:CO2_Sensor"
    if "temp" in text:
        if any(token in text for token in ("supply", "sat", "給気")):
            return "brick:Supply_Air_Temperature_Sensor"
        if any(token in text for token in ("return", "rat", "還気")):
            return "brick:Return_Air_Temperature_Sensor"
        if any(token in text for token in ("mixed", "mat", "混合")):
            return "brick:Mixed_Air_Temperature_Sensor"
        return "brick:Air_Temperature_Sensor"
    if "humidity" in text or "rh" in text:
        return "brick:Humidity_Sensor"
    if "flow" in text:
        return "brick:Air_Flow_Sensor"
    if "static" in text or "静圧" in text:
        return "brick:Supply_Air_Static_Pressure_Sensor"
    if "differential" in text or "差圧" in text:
        return "brick:Air_Differential_Pressure_Sensor"
    if "fan_speed" in text:
        return "brick:Fan_Speed_Sensor"
    if "fan_status" in text:
        return "brick:Fan_Status_Sensor"

    return "brick:Sensor"


def map_points(table: PointTable, base_ns: str) -> BrickPointsSet:
    items = []

    for row in table.rows:
        point_id = row.raw.get("point_id") or row.point_name
        iri = f"{base_ns}{_safe_local('Sensor_' + str(point_id))}"
        items.append(
            BrickPoint(
                brick_point_iri=iri,
                point_name=row.point_name,
                linked_equipment_guid=None,
                kind=row.kind,
                unit=row.unit,
                extra_props={
                    "brick_class": infer_brick_point_class(row.point_name),
                    "equipment_ref": row.equipment_ref,
                    "space_id": row.raw.get("space_id"),
                    "point_id": point_id,
                },
            )
        )

    return BrickPointsSet(items=items)
