from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_warehouse(path: Path, dataset_name: str, records: list[dict[str, Any]], manifest: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "dataset_name": dataset_name,
        "records": records,
        "manifest": manifest,
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def read_warehouse(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))
