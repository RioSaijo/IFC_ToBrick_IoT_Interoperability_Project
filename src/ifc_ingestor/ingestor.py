
from __future__ import annotations

from pathlib import Path
from typing import Optional

import ifcopenshell

from app.contracts import IfcBundle


def _detect_schema(model: "ifcopenshell.file") -> str:
    """
    ifcopenshell の model から IFC スキーマ名を取得するヘルパー。
    例: "IFC2X3", "IFC4", "IFC4X3" など。
    """
    # ifcopenshell のバージョンによって属性名が異なる可能性もあるため、
    # 安全側で getattr を使っておく。
    for attr in ("schema", "schema_name", "schema_identifier"):
        schema = getattr(model, attr, None)
        if isinstance(schema, str) and schema:
            return schema.upper()

    # 取れなかった場合のフォールバック
    return "UNKNOWN"


def load_ifc_bundle(ifc_path: str) -> IfcBundle:
    """
    IFC ファイルを読み込み、最小限のメタ情報とともに IfcBundle にラップして返す。

    Parameters
    ----------
    ifc_path : str
        入力 IFC ファイルへのパス。

    Returns
    -------
    IfcBundle
        - schema: IFC スキーマ名 (例: "IFC2X3")
        - source_path: 与えられた IFC ファイルパス（絶対パス化）
        - model: ifcopenshell.file オブジェクト

    Raises
    ------
    FileNotFoundError
        ファイルが存在しない場合。
    RuntimeError
        ifcopenshell がファイルを開けなかった場合。
    """
    path_obj = Path(ifc_path)

    if not path_obj.is_file():
        raise FileNotFoundError(f"IFC file not found: {path_obj}")

    try:
        model = ifcopenshell.open(str(path_obj))
    except Exception as exc:  # type: ignore[broad-except]
        raise RuntimeError(f"Failed to open IFC file with ifcopenshell: {path_obj}") from exc

    schema = _detect_schema(model)
    # 絶対パスに揃えておくと、後段のモジュールで扱いやすい
    abs_path = str(path_obj.resolve())

    return IfcBundle(
        schema=schema,
        source_path=abs_path,
        model=model,
    )
