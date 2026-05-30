from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256

from blockchain.web3_client import Web3Client


@dataclass
class TransactionService:
    web3_client: Web3Client
    private_key: str
    account: str

    def sign_and_send(self, action: str, payload: dict[str, str]) -> dict[str, str | int | dict[str, str]]:
        signature = sha256(f"{self.private_key}:{action}:{payload}".encode("utf-8")).hexdigest()
        transaction = {
            "from": self.account,
            "action": action,
            "payload": payload,
            "signature": signature,
            "submitted_at": datetime.now(UTC).isoformat(),
        }
        return self.web3_client.mine_transaction(transaction)
