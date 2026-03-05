# -*- coding: utf-8 -*-
from __future__ import annotations

import csv
import json
import logging
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from app.contracts import PointRow, PointTable

logger = logging.getLogger(__name__)

# ------------------------------
# 列名候補マップ (テストで差し替え可能なモジュール定数)
# ------------------------------
POINT_NAME_ALIASES: Tuple[str, ...] = (
    "point_name", "name", "tag", "point", "signal", "trend_name", "io_point",
)

EQUIPMENT_REF_ALIASES: Tuple[str, ...] = (
    "equipment_ref", "equipment", "equip", "ahu_id", "system", "device", "asset", "equipment_id",
)

KIND_ALIASES: Tuple[str, ...] = (
    "kind", "type", "point_type", "io_type", "category", "signal_type",
)

UNIT_ALIASES: Tuple[str, ...] = (
    "unit", "units", "eng_units", "uom",
)

# 単位の簡易正規化辞書
DEFAULT_UNIT_NORMALIZATION: Dict[str, str] = {
    "°c": "degC",
    "deg c": "degC",
    "degc": "degC",
    "c": "degC",
    "°f": "degF",
    "deg f": "degF",
    "degf": "degF",
    "kw": "kW",
    "w": "W",
    "pa": "Pa",
    "kpa": "kPa",
    "m3/h": "m3/h",
    "m3/s": "m3/s",
    "%": "%",
}

# kind の簡易正規化辞書
DEFAULT_KIND_NORMALIZATION: Dict[str, str] = {
    "sensor": "sensor",
    "sns": "sensor",
    "cmd": "command",
    "command": "command",
    "setpoint": "setpoint",
    "sp": "setpoint",
    "status": "status",
    "st": "status",
    "alarm": "alarm",
}

# ------------------------------
# CSVW メタデータの簡易解釈
# ------------------------------
def _load_csvw_metadata(path: Optional[str | Path]) -> Dict[str, Any]:
    """
    CSVW メタデータ JSON の最小読み込み. 存在しない場合は空辞書を返す.
    想定利用:
      - columns[].titles による列名マッピング
      - dialect.encoding による文字コードヒント
      - tableSchema.aboutUrl などは未使用
    """
    if not path:
        return {}
    p = Path(path)
    if not p.is_file():
        logger.warning("CSVW metadata not found, path=%s", p)
        return {}
    try:
        with p.open("r", encoding="utf-8") as f:
            meta = json.load(f)
            return meta if isinstance(meta, dict) else {}
    except Exception as e:
        logger.warning("CSVW metadata load failed, path=%s, err=%s", p, e)
        return {}


def _aliases_from_csvw(meta: Dict[str, Any]) -> Dict[str, List[str]]:
    """
    CSVW の columns[].name と titles から, 列名エイリアスを抽出.
    形式:
      {
        "point_name": ["Point Name", "Tag", ...],
        "equipment_ref": ["Equipment", ...],
        ...
      }
    """
    out: Dict[str, List[str]] = {}
    cols = meta.get("tableSchema", {}).get("columns", []) if meta else []
    if not isinstance(cols, list):
        return out

    # CSVW では titles が配列または文字列の場合がある
    def _as_list(x: Any) -> List[str]:
        if x is None:
            return []
        if isinstance(x, list):
            return [str(v) for v in x]
        return [str(x)]

    for col in cols:
        if not isinstance(col, dict):
            continue
        name = str(col.get("name") or "").strip()
        titles = [t.strip() for t in _as_list(col.get("titles")) if str(t).strip()]
        if not name:
            continue

        # 列の意味を推定してキー名へ寄せる簡易規則
        lname = name.lower()
        if any(k in lname for k in ["point", "tag", "signal", "name"]):
            out.setdefault("point_name", []).extend([name] + titles)
        elif any(k in lname for k in ["equip", "system", "device", "asset", "ahu"]):
            out.setdefault("equipment_ref", []).extend([name] + titles)
        elif any(k in lname for k in ["kind", "type", "io type", "category"]):
            out.setdefault("kind", []).extend([name] + titles)
        elif any(k in lname for k in ["unit", "uom", "eng"]):
            out.setdefault("unit", []).extend([name] + titles)
        # 未該当は無視

    return out


def _encoding_from_csvw(meta: Dict[str, Any]) -> Optional[str]:
    """
    CSVW の dialect.encoding があれば返す.
    """
    try:
        enc = meta.get("dialect", {}).get("encoding")
        if isinstance(enc, str) and enc.strip():
            return enc.strip()
    except Exception:
        pass
    return None


# ------------------------------
# 列マッピング解決
# ------------------------------
def _resolve_column(source_header: List[str], aliases: List[str]) -> Optional[str]:
    """
    大文字小文字と前後空白を無視して最初に一致する元列名を返す.
    """
    norm_header = {h.strip().lower(): h for h in source_header}
    for a in aliases:
        key = a.strip().lower()
        if key in norm_header:
            return norm_header[key]
    return None


def _candidate_aliases(
    csvw_aliases: Dict[str, List[str]] | None,
    builtin_candidates: Tuple[str, ...],
) -> List[str]:
    """
    CSVW の titles 由来の別名を優先し, その後に内蔵候補を連結する.
    """
    out: List[str] = []
    if csvw_aliases:
        out.extend(csvw_aliases)
    out.extend(list(builtin_candidates))
    # 重複排除を安定順序で
    seen: set[str] = set()
    dedup: List[str] = []
    for x in out:
        xl = x.strip().lower()
        if xl and xl not in seen:
            seen.add(xl)
            dedup.append(x)
    return dedup


# ------------------------------
# 正規化ヘルパ
# ------------------------------
def _normalize_unit(unit: Optional[str], unit_map: Optional[Dict[str, str]]) -> Optional[str]:
    if unit is None:
        return None
    u = unit.strip()
    if not u:
        return None
    key = u.lower().replace("°", "°")  # 明示的に保持
    # CSVW 側で優先上書き
    if unit_map and key in unit_map:
        return unit_map[key]
    # 既定辞書
    return DEFAULT_UNIT_NORMALIZATION.get(key, u)


def _normalize_kind(kind: Optional[str], kind_map: Optional[Dict[str, str]]) -> Optional[str]:
    if kind is None:
        return None
    k = kind.strip()
    if not k:
        return None
    key = k.lower()
    if kind_map and key in kind_map:
        return kind_map[key]
    return DEFAULT_KIND_NORMALIZATION.get(key, k)


# ------------------------------
# 文字コードフォールバック読取
# ------------------------------
def _read_dict_rows(csv_path: Path, preferred_encoding: Optional[str]) -> List[Dict[str, Any]]:
    encodings = [preferred_encoding] if preferred_encoding else []
    # 優先順: CSVW 指定 -> utf-8-sig -> utf-8 -> cp932
    for e in ["utf-8-sig", "utf-8", "cp932"]:
        if e not in encodings:
            encodings.append(e)

    last_err: Optional[Exception] = None
    for enc in encodings:
        try:
            with csv_path.open("r", encoding=enc, newline="") as f:
                reader = csv.DictReader(f)
                rows = [dict(r) for r in reader]
                logger.info("CSV loaded, path=%s, encoding=%s, rows=%d", csv_path, enc, len(rows))
                return rows
        except Exception as e:
            last_err = e
            logger.warning("CSV read failed, path=%s, encoding=%s, err=%s", csv_path, enc, e)
            continue
    # すべて失敗
    raise RuntimeError(f"CSV read failed for {csv_path} with encodings {encodings}. last_err={last_err}")


# ------------------------------
# 公開関数
# ------------------------------
def load_points_csv(
    csv_path: str | Path,
    csvw_metadata_path: str | Path | None = None,
) -> PointTable:
    """
    ポイント一覧 CSV を読み込み, PointRow の配列へ正規化して返す.
    列名ゆらぎは内蔵候補と CSVW メタデータの titles を用いて解決する.
    unit と kind は簡易正規化を適用する.
    """
    csv_path = Path(csv_path)

    # CSVW メタデータの読み込み
    meta = _load_csvw_metadata(csvw_metadata_path)
    csvw_alias_map = _aliases_from_csvw(meta)
    enc_hint = _encoding_from_csvw(meta)

    # CSV 読取
    dict_rows = _read_dict_rows(csv_path, preferred_encoding=enc_hint)
    if not dict_rows:
        logger.info("No rows found in CSV, path=%s", csv_path)
        return PointTable(rows=[])

    # ヘッダ
    header = list(dict_rows[0].keys())

    # 列解決
    name_col = _resolve_column(
        header,
        _candidate_aliases(csvw_alias_map.get("point_name"), POINT_NAME_ALIASES),
    )
    equip_col = _resolve_column(
        header,
        _candidate_aliases(csvw_alias_map.get("equipment_ref"), EQUIPMENT_REF_ALIASES),
    )
    kind_col = _resolve_column(
        header,
        _candidate_aliases(csvw_alias_map.get("kind"), KIND_ALIASES),
    )
    unit_col = _resolve_column(
        header,
        _candidate_aliases(csvw_alias_map.get("unit"), UNIT_ALIASES),
    )

    logger.info(
        "Resolved columns. point_name=%s, equipment_ref=%s, kind=%s, unit=%s",
        name_col, equip_col, kind_col, unit_col,
    )

    # CSVW に unit/kind 正規化辞書がある場合の受け口
    unit_norm_map = None
    kind_norm_map = None
    try:
        unit_norm_map = meta.get("unitNormalization") if isinstance(meta, dict) else None
        kind_norm_map = meta.get("kindNormalization") if isinstance(meta, dict) else None
    except Exception:
        pass

    # PointRow の組立
    items: List[PointRow] = []
    missing_name = 0

    for r in dict_rows:
        raw: Dict[str, Any] = dict(r)

        point_name = str(r.get(name_col) or "").strip() if name_col else ""
        if not point_name:
            # 仕様: point_name 欠損は None ではなく空文字で検出しやすく保持
            missing_name += 1

        equipment_ref = str(r.get(equip_col)).strip() if equip_col and r.get(equip_col) not in (None, "") else None

        kind_val_raw = str(r.get(kind_col)).strip() if kind_col and r.get(kind_col) not in (None, "") else None
        kind_val = _normalize_kind(kind_val_raw, kind_norm_map)

        unit_val_raw = str(r.get(unit_col)).strip() if unit_col and r.get(unit_col) not in (None, "") else None
        unit_val = _normalize_unit(unit_val_raw, unit_norm_map)

        row = PointRow(
            point_name=point_name,
            equipment_ref=equipment_ref,
            kind=kind_val,
            unit=unit_val,
            raw=raw,
        )
        items.append(row)

    if missing_name > 0:
        logger.warning("Rows with missing point_name detected, count=%d, path=%s", missing_name, csv_path)

    logger.info("PointTable built, rows=%d, path=%s", len(items), csv_path)
    return PointTable(rows=items)