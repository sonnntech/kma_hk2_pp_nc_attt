from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any


@dataclass(frozen=True)
class SecurityAssessment:
    status: str
    checked_at: str
    findings: list[str]


def inspect_records(records: list[dict[str, Any]]) -> SecurityAssessment:
    findings: list[str] = []
    if not records:
        findings.append("No source records detected.")
    if any(record["amount"] <= 0 for record in records):
        findings.append("Non-positive transaction amount detected.")
    return SecurityAssessment(
        status="pass" if not findings else "review",
        checked_at=datetime.now(UTC).isoformat(),
        findings=findings,
    )
