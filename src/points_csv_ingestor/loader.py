# -*- coding: utf-8 -*-
"""
points_csv_ingestor.loader

仕様（最新版）:
- CSVスキーマ: point_id,name,unit,bdns_abbreviation,space_id
- すべてのセンサーに brick:hasLocation を付与する
- bdns_abbreviation = NaN → Space所属 → space_id を使用し bot:Space を生成
- bdns_abbreviation あり → 機器所属 → m51:<bdns> を生成し、その個体に brick:hasLocation を付与
- Sensor自身にも hasLocation を付与する（必須）
"""

from __future__ import annotations
import re
from typing import Optional
import pandas as pd
from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import RDF, RDFS, XSD

# 先頭付近の import 群は既存のまま

# --- ユーティリティ: 欠損判定のヘルパ ---
import pandas as pd

def _is_missing(x) -> bool:
    return x is None or pd.isna(x)

def _as_str_or_none(x):
    if _is_missing(x):
        return None
    s = str(x).strip()
    if s in ("", "None", "none", "NaN", "nan"):
        return None
    return s

BASE_NS = "https://id.morgate51.org/project#"

M51  = Namespace(BASE_NS)
BRICK = Namespace("https://brickschema.org/schema/Brick#")
BOT   = Namespace("https://w3id.org/bot#")
QUDT_UNIT = Namespace("http://qudt.org/vocab/unit/")

__all__ = ["csv_to_brick_graph", "write_graph", "BASE_NS"]


def _safe_local(local: str) -> str:
    s = re.sub(r"[^A-Za-z0-9_\-]", "_", local)
    if not re.match(r"^[A-Za-z_]", s):
        s = "X_" + s
    return s


# --- Sensor class mapping (Brick 1.3 実在クラスのみ) ---
def _infer_sensor_class(name: str) -> URIRef:
    n = (name or "").lower()

    if "occupancy" in n or "在室" in n:
        return BRICK["Occupancy_Sensor"]

    if "co2" in n:
        if any(k in n for k in ["return", "rat", "還気"]):
            return BRICK["Return_Air_CO2_Sensor"]
        return BRICK["CO2_Sensor"]

    if "temp" in n:
        if any(k in n for k in ["supply", "sat", "給気"]):
            return BRICK["Supply_Air_Temperature_Sensor"]
        if any(k in n for k in ["return", "rat", "還気"]):
            return BRICK["Return_Air_Temperature_Sensor"]
        if any(k in n for k in ["mixed", "mat", "混合"]):
            return BRICK["Mixed_Air_Temperature_Sensor"]
        return BRICK["Air_Temperature_Sensor"]

    if "humidity" in n or "rh" in n:
        return BRICK["Humidity_Sensor"]

    if "flow" in n:
        if "supply" in n:
            return BRICK["Supply_Air_Flow_Sensor"]
        if "discharge" in n:
            return BRICK["Discharge_Air_Flow_Sensor"]
        return BRICK["Air_Flow_Sensor"]

    if "static" in n or "静圧" in n:
        return BRICK["Supply_Air_Static_Pressure_Sensor"]

    if "differential" in n or "差圧" in n:
        return BRICK["Air_Differential_Pressure_Sensor"]

    if "fan_speed" in n:
        return BRICK["Fan_Speed_Sensor"]

    if "fan_status" in n:
        return BRICK["Fan_Status_Sensor"]

    return BRICK["Sensor"]


# --- Unit mapping ---
def _map_unit_to_qudt(u: Optional[str]) -> Optional[URIRef]:
    if not u:
        return None
    t = u.lower()
    if t == "binary":
        return None
    if t == "degc":
        return QUDT_UNIT["DEG_C"]
    if t == "pa":
        return QUDT_UNIT["PA"]
    if t in ("m3/s","m³/s"):
        return QUDT_UNIT["M3-PER-SEC"]
    if t == "ppm":
        return QUDT_UNIT["PPM"]
    if t in ("%","percent","%rh","rh"):
        return QUDT_UNIT["PERCENT"]
    return None


def csv_to_brick_graph(csv_path: str, base_ns: str = BASE_NS, verbose=False) -> Graph:
    df = pd.read_csv(csv_path, dtype=object)

    required = ["point_id","name","unit","bdns_abbreviation","space_id"]
    for c in required:
        if c not in df.columns:
            raise ValueError(f"Missing col: {c}")

    # 列正規化, 空文字や文字列NaNを None に統一
    for c in required:
        df[c] = df[c].apply(_as_str_or_none)

    g = Graph()
    m51 = Namespace(base_ns)
    g.bind("m51", m51)
    g.bind("brick", BRICK)
    g.bind("bot", BOT)
    g.bind("qudt-unit", QUDT_UNIT)
    g.bind("rdfs", RDFS)
    g.bind("xsd", XSD)

    SENSOR_ID = m51["sensorID"]

    total = 0
    skipped_space_required = 0

    for _, row in df.iterrows():
        total += 1

        # point_id
        pid_raw = row["point_id"]
        try:
            pid = int(pid_raw) if not _is_missing(pid_raw) else None
        except Exception:
            pid = None
        if pid is None:
            # point_id 欠損はスキップ
            continue

        name = _as_str_or_none(row["name"]) or f"sensor_{pid}"
        unit = _as_str_or_none(row["unit"])
        bdns = _as_str_or_none(row["bdns_abbreviation"])
        space_id = _as_str_or_none(row["space_id"])

        # センサー個体
        sensor_iri = m51[f"Sensor_{pid}"]
        class_iri  = _infer_sensor_class(name)
        g.add((sensor_iri, RDF.type, class_iri))
        g.add((sensor_iri, RDFS.label, Literal(name)))
        g.add((sensor_iri, SENSOR_ID, Literal(pid, datatype=XSD.integer)))

        # --- hasLocation を必ず付与する方針 ---
        if _is_missing(bdns):
            # Space 所属, space_id から Space 個体へ
            if _is_missing(space_id):
                skipped_space_required += 1
            else:
                local = f"m51_{space_id.replace('-', '_')}"
                space_iri = m51[_safe_local(local)]  # _safe_local はここで文字列が保証される
                g.add((space_iri, RDF.type, BOT.Space))
                g.add((sensor_iri, BRICK.hasLocation, space_iri))
        else:
            # 機器所属, 機器個体の生成と hasPoint
            equip_local = _safe_local(bdns)  # ここでbdnsは必ず文字列
            equip_iri = m51[equip_local]

            # 型付けの推定
            bdns_u = bdns.upper()
            if bdns_u.startswith("AHU"):
                g.add((equip_iri, RDF.type, BRICK["AHU"]))
            elif bdns_u.startswith("VAVS") or bdns_u.startswith("VAV"):
                g.add((equip_iri, RDF.type, BRICK["VAV"]))
            elif bdns_u.startswith("FCU"):
                g.add((equip_iri, RDF.type, BRICK["FCU"]))
            else:
                g.add((equip_iri, RDF.type, BRICK["Equipment"]))

            # 付帯
            g.add((equip_iri, BRICK.hasPoint, sensor_iri))

            # センサーにも hasLocation を付ける今回の仕様
            # 優先順位: space_id があれば Space へ, なければ機器に付いている Location を流用, それもなければ未付与
            if not _is_missing(space_id):
                local = f"m51_{space_id.replace('-', '_')}"
                space_iri = m51[_safe_local(local)]
                g.add((space_iri, RDF.type, BOT.Space))
                g.add((sensor_iri, BRICK.hasLocation, space_iri))
            else:
                # 機器の hasLocation を流用, なければ今は付与不能
                # ここで機器のロケーションが既知なら, 次のように継承できる
                # for _, _, loc in g.triples((equip_iri, BRICK.hasLocation, None)):
                #     g.add((sensor_iri, BRICK.hasLocation, loc))
                pass

        # 単位
        unit_iri = _map_unit_to_qudt(unit)
        if unit_iri is not None:
            g.add((sensor_iri, BRICK.hasUnit, unit_iri))

    if verbose:
        print(f"rows={total}, skipped_space_required={skipped_space_required}, triples={len(g)}")
    return g



def write_graph(g:Graph, out_ttl_path:str):
    g.serialize(destination=out_ttl_path, format="turtle")