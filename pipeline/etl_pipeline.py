from __future__ import annotations

import json
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from audit.audit_engine import verify_dataset_integrity
from blockchain.contract_service import ContractService
from blockchain.transaction_service import TransactionService
from blockchain.web3_client import Web3Client
from infrastructure.logging import configure_logging
from infrastructure.settings import Settings, get_settings
from pipeline.hashing import sha256_digest
from pipeline.lineage import build_lineage_manifest
from pipeline.mock_sources import generate_mock_source_data
from pipeline.security_agent import inspect_records
from pipeline.warehouse_writer import write_warehouse

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PipelineResult:
    contract_address: str
    transaction_hash: str
    dataset_hash: str
    manifest_hash: str
    audit_message: str
    warehouse_path: str


def transform_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            **record,
            "amount_usd": record["amount"],
            "risk_band": "high" if record["amount"] >= 200 else "standard",
        }
        for record in records
    ]


def bootstrap_contract(settings: Settings) -> ContractService:
    web3_client = Web3Client(settings.ledger_path)
    tx_service = TransactionService(web3_client, settings.blockchain_private_key, settings.blockchain_account)
    service = ContractService(
        settings.contract_artifact_path,
        settings.contract_state_path,
        settings.deployment_state_path,
        tx_service,
    )
    artifact = service.compile_contract(Path(__file__).resolve().parents[1] / "contracts" / "DataPipelineGovernance.sol")
    deployment = service.deploy_contract(artifact)
    logger.info("Contract deployed at %s", deployment["contract_address"])
    return service


def run_pipeline(settings: Settings | None = None) -> PipelineResult:
    settings = settings or get_settings()
    configure_logging(settings.log_level)
    source_records = generate_mock_source_data(settings.source_record_count)
    security_assessment = inspect_records(source_records)
    logger.info("Security assessment status: %s", security_assessment.status)
    transformed_records = transform_records(source_records)
    dataset_hash = sha256_digest(transformed_records)
    manifest = build_lineage_manifest(
        dataset_name="daily_customer_payments",
        warehouse_path=str(settings.warehouse_path),
        dataset_hash=dataset_hash,
        record_count=len(transformed_records),
    )
    manifest["security_assessment"] = security_assessment.__dict__
    warehouse_payload = write_warehouse(settings.warehouse_path, "daily_customer_payments", transformed_records, manifest)
    manifest_hash = sha256_digest(warehouse_payload["manifest"])
    contract_service = bootstrap_contract(settings)
    receipt = contract_service.store_proof("daily_customer_payments", dataset_hash, manifest_hash)
    audit_result = verify_dataset_integrity(settings.warehouse_path, contract_service, "daily_customer_payments")
    deployment = json.loads(settings.deployment_state_path.read_text(encoding="utf-8"))
    return PipelineResult(
        contract_address=deployment["contract_address"],
        transaction_hash=str(receipt["transaction_hash"]),
        dataset_hash=dataset_hash,
        manifest_hash=manifest_hash,
        audit_message=audit_result.message,
        warehouse_path=str(settings.warehouse_path),
    )


def main() -> None:
    result = run_pipeline()
    print(json.dumps(result.__dict__, indent=2))


if __name__ == "__main__":
    main()
