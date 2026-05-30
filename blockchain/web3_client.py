from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any


@dataclass
class Web3Client:
    ledger_path: Path

    def __post_init__(self) -> None:
        if not self.ledger_path.exists():
            self.ledger_path.write_text(json.dumps({"chain_id": 1337, "blocks": []}, indent=2), encoding="utf-8")

    def is_connected(self) -> bool:
        return self.ledger_path.exists()

    def load_ledger(self) -> dict[str, Any]:
        return json.loads(self.ledger_path.read_text(encoding="utf-8"))

    def save_ledger(self, ledger: dict[str, Any]) -> None:
        self.ledger_path.write_text(json.dumps(ledger, indent=2), encoding="utf-8")

    def mine_transaction(self, transaction: dict[str, Any]) -> dict[str, Any]:
        ledger = self.load_ledger()
        blocks = ledger["blocks"]
        previous_hash = blocks[-1]["block_hash"] if blocks else "GENESIS"
        block_number = len(blocks) + 1
        tx_hash = sha256(json.dumps(transaction, sort_keys=True).encode("utf-8")).hexdigest()
        block_hash = sha256(f"{previous_hash}:{tx_hash}:{block_number}".encode("utf-8")).hexdigest()
        receipt = {
            "block_number": block_number,
            "previous_hash": previous_hash,
            "block_hash": block_hash,
            "transaction_hash": tx_hash,
            "transaction": transaction,
            "status": "mined",
        }
        blocks.append(receipt)
        self.save_ledger(ledger)
        return receipt
