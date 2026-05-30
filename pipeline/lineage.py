from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any


@dataclass(frozen=True)
class LineageManifest:
    dataset_name: str
    record_count: int
    pipeline_run_id: str
    source_system: str
    generated_at: str
    warehouse_path: str
    dataset_hash: str


def build_lineage_manifest(dataset_name: str, warehouse_path: str, dataset_hash: str, record_count: int) -> dict[str, Any]:
    manifest = LineageManifest(
        dataset_name=dataset_name,
        record_count=record_count,
        pipeline_run_id=f"run-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}",
        source_system="mock-payment-gateway",
        generated_at=datetime.now(UTC).isoformat(),
        warehouse_path=warehouse_path,
        dataset_hash=dataset_hash,
    )
    return asdict(manifest)
