from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class VerificationResult:
    status: str
    expected_hash: str
    actual_hash: str
    message: str
