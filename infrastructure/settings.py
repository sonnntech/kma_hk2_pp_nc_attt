from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    app_env: str = os.getenv("APP_ENV", "local")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    source_record_count: int = int(os.getenv("SOURCE_RECORD_COUNT", "8"))
    data_root: Path = Path(os.getenv("DATA_ROOT", "./data"))
    state_root: Path = Path(os.getenv("STATE_ROOT", "./state"))
    warehouse_path: Path = Path(os.getenv("WAREHOUSE_PATH", "./warehouse/warehouse.json"))
    ledger_path: Path = Path(os.getenv("BLOCKCHAIN_LEDGER_PATH", "./state/blockchain_ledger.json"))
    contract_artifact_path: Path = Path(
        os.getenv("CONTRACT_ARTIFACT_PATH", "./contracts/artifacts/DataPipelineGovernance.json")
    )
    contract_state_path: Path = Path(os.getenv("CONTRACT_STATE_PATH", "./state/contract_state.json"))
    deployment_state_path: Path = Path(os.getenv("DEPLOYMENT_STATE_PATH", "./state/deployment.json"))
    blockchain_private_key: str = os.getenv("BLOCKCHAIN_PRIVATE_KEY", "demo-private-key")
    blockchain_account: str = os.getenv("BLOCKCHAIN_ACCOUNT", "0xDemoAccount")


def get_settings() -> Settings:
    settings = Settings()
    settings.data_root.mkdir(parents=True, exist_ok=True)
    settings.state_root.mkdir(parents=True, exist_ok=True)
    settings.warehouse_path.parent.mkdir(parents=True, exist_ok=True)
    settings.contract_artifact_path.parent.mkdir(parents=True, exist_ok=True)
    return settings
