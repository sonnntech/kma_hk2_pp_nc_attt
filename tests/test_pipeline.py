from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from infrastructure.settings import Settings
from pipeline.etl_pipeline import run_pipeline
from pipeline.warehouse_writer import read_warehouse


class PipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp(prefix="bdp-pipeline-"))
        self.settings = Settings(
            data_root=self.temp_dir / "data",
            state_root=self.temp_dir / "state",
            warehouse_path=self.temp_dir / "warehouse" / "warehouse.json",
            ledger_path=self.temp_dir / "state" / "blockchain_ledger.json",
            contract_artifact_path=self.temp_dir / "contracts" / "artifacts" / "DataPipelineGovernance.json",
            contract_state_path=self.temp_dir / "state" / "contract_state.json",
            deployment_state_path=self.temp_dir / "state" / "deployment.json",
        )
        self.settings.data_root.mkdir(parents=True, exist_ok=True)
        self.settings.state_root.mkdir(parents=True, exist_ok=True)
        self.settings.warehouse_path.parent.mkdir(parents=True, exist_ok=True)
        self.settings.contract_artifact_path.parent.mkdir(parents=True, exist_ok=True)
        contract_target = self.temp_dir / "contracts"
        contract_target.mkdir(parents=True, exist_ok=True)
        source_contract = Path("contracts/DataPipelineGovernance.sol").read_text(encoding="utf-8")
        (contract_target / "DataPipelineGovernance.sol").write_text(source_contract, encoding="utf-8")

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir)

    def test_pipeline_writes_warehouse_and_audits(self) -> None:
        result = run_pipeline(self.settings)
        warehouse = read_warehouse(self.settings.warehouse_path)
        self.assertEqual(result.audit_message, "Hash Match - Data Integrity Verified")
        self.assertEqual(warehouse["dataset_name"], "daily_customer_payments")
        self.assertTrue(result.contract_address.startswith("0x"))


if __name__ == "__main__":
    unittest.main()
