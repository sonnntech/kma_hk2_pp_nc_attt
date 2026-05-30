from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from audit.audit_engine import verify_dataset_integrity
from blockchain.contract_service import ContractService
from blockchain.transaction_service import TransactionService
from blockchain.web3_client import Web3Client
from pipeline.hashing import sha256_digest


class AuditTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp(prefix="bdp-audit-"))
        self.source_path = self.temp_dir / "DataPipelineGovernance.sol"
        self.source_path.write_text(Path("contracts/DataPipelineGovernance.sol").read_text(encoding="utf-8"), encoding="utf-8")
        self.warehouse_path = self.temp_dir / "warehouse.json"
        payload = {"dataset_name": "dataset", "records": [{"id": 1, "amount": 10}], "manifest": {"dataset_hash": "x"}}
        self.warehouse_path.write_text(json.dumps(payload), encoding="utf-8")
        self.service = ContractService(
            self.temp_dir / "artifact.json",
            self.temp_dir / "contract_state.json",
            self.temp_dir / "deployment.json",
            TransactionService(Web3Client(self.temp_dir / "ledger.json"), "key", "0xabc"),
        )
        artifact = self.service.compile_contract(self.source_path)
        self.service.deploy_contract(artifact)
        self.service.store_proof("dataset", sha256_digest(payload["records"]), "manifest")

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir)

    def test_verify_dataset_integrity_success(self) -> None:
        result = verify_dataset_integrity(self.warehouse_path, self.service, "dataset")
        self.assertEqual(result.status, "pass")


if __name__ == "__main__":
    unittest.main()
