from __future__ import annotations

import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from blockchain.contract_service import ContractService
from blockchain.transaction_service import TransactionService
from blockchain.web3_client import Web3Client
from infrastructure.logging import configure_logging
from infrastructure.settings import get_settings


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    web3_client = Web3Client(settings.ledger_path)
    tx_service = TransactionService(web3_client, settings.blockchain_private_key, settings.blockchain_account)
    contract_service = ContractService(
        settings.contract_artifact_path,
        settings.contract_state_path,
        settings.deployment_state_path,
        tx_service,
    )
    artifact = contract_service.compile_contract(Path(__file__).resolve().with_name("DataPipelineGovernance.sol"))
    deployment = contract_service.deploy_contract(artifact)
    print(deployment["contract_address"])


if __name__ == "__main__":
    main()
