from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from typing import Any


@dataclass(frozen=True)
class SourceRecord:
    record_id: int
    customer_id: str
    amount: float
    currency: str
    event_time: str
    region: str


def generate_mock_source_data(record_count: int) -> list[dict[str, Any]]:
    base_time = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
    records = [
        SourceRecord(
            record_id=index + 1,
            customer_id=f"CUST-{index + 1:03d}",
            amount=round(125.0 + (index * 17.5), 2),
            currency="USD",
            event_time=(base_time + timedelta(hours=index)).isoformat(),
            region=["NA", "EU", "APAC"][index % 3],
        )
        for index in range(record_count)
    ]
    return [asdict(record) for record in records]
