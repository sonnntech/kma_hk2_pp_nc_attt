from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

from blockchain.transaction_service import TransactionService


@dataclass
class ContractService:
    artifact_path: Path
    contract_state_path: Path
    deployment_state_path: Path
    transaction_service: TransactionService

    def compile_contract(self, source_path: Path) -> dict[str, Any]:
        source = source_path.read_text(encoding="utf-8")
        if "contract DataPipelineGovernance" not in source or "pragma solidity" not in source:
            raise ValueError("Solidity source is missing expected declarations.")
        artifact = {
            "contractName": "DataPipelineGovernance",
            "abi": [
                {"name": "storeProof", "type": "function"},
                {"name": "getProof", "type": "function"},
            ],
            "bytecode": "0x" + sha256(source.encode("utf-8")).hexdigest(),
            "sourceHash": sha256(source.encode("utf-8")).hexdigest(),
        }
        self.artifact_path.write_text(json.dumps(artifact, indent=2), encoding="utf-8")
        return artifact

    def deploy_contract(self, artifact: dict[str, Any]) -> dict[str, Any]:
        contract_address = "0x" + sha256(artifact["bytecode"].encode("utf-8")).hexdigest()[:40]
        deployment = {"contract_address": contract_address, "artifact_hash": artifact["sourceHash"]}
        self.deployment_state_path.write_text(json.dumps(deployment, indent=2), encoding="utf-8")
        if not self.contract_state_path.exists():
            self.contract_state_path.write_text(json.dumps({"proofs": {}}, indent=2), encoding="utf-8")
        return deployment

    def store_proof(self, dataset_name: str, dataset_hash: str, manifest_hash: str) -> dict[str, Any]:
        state = json.loads(self.contract_state_path.read_text(encoding="utf-8"))
        state["proofs"][dataset_name] = {"dataset_hash": dataset_hash, "manifest_hash": manifest_hash}
        self.contract_state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
        return self.transaction_service.sign_and_send(
            "storeProof",
            {"dataset_name": dataset_name, "dataset_hash": dataset_hash, "manifest_hash": manifest_hash},
        )

    def get_proof(self, dataset_name: str) -> dict[str, str]:
        state = json.loads(self.contract_state_path.read_text(encoding="utf-8"))
        return state["proofs"][dataset_name]
