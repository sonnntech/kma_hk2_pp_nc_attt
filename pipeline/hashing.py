from __future__ import annotations

import hashlib
import json
from typing import Any


def canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"))


def sha256_digest(data: Any) -> str:
    payload = canonical_json(data).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
