from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from blockchain.contract_service import ContractService
from blockchain.transaction_service import TransactionService
from blockchain.web3_client import Web3Client


class BlockchainTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp(prefix="bdp-chain-"))
        self.ledger_path = self.temp_dir / "ledger.json"
        self.artifact_path = self.temp_dir / "artifact.json"
        self.contract_state_path = self.temp_dir / "contract_state.json"
        self.deployment_state_path = self.temp_dir / "deployment.json"
        self.source_path = self.temp_dir / "DataPipelineGovernance.sol"
        self.source_path.write_text(Path("contracts/DataPipelineGovernance.sol").read_text(encoding="utf-8"), encoding="utf-8")

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir)

    def test_compile_deploy_and_store_proof(self) -> None:
        service = ContractService(
            self.artifact_path,
            self.contract_state_path,
            self.deployment_state_path,
            TransactionService(Web3Client(self.ledger_path), "key", "0xabc"),
        )
        artifact = service.compile_contract(self.source_path)
        deployment = service.deploy_contract(artifact)
        receipt = service.store_proof("dataset", "hash1", "hash2")
        proof = service.get_proof("dataset")
        self.assertEqual(proof["dataset_hash"], "hash1")
        self.assertEqual(receipt["status"], "mined")
        self.assertTrue(deployment["contract_address"].startswith("0x"))


if __name__ == "__main__":
    unittest.main()
