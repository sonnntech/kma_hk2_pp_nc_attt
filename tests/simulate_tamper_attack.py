from __future__ import annotations

import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from audit.audit_engine import verify_dataset_integrity
from pipeline.etl_pipeline import bootstrap_contract, run_pipeline
from infrastructure.settings import get_settings
from pipeline.warehouse_writer import read_warehouse


def main() -> None:
    settings = get_settings()
    run_pipeline(settings)
    warehouse = read_warehouse(settings.warehouse_path)
    warehouse["records"][0]["amount"] = 9999.99
    settings.warehouse_path.write_text(json.dumps(warehouse, indent=2), encoding="utf-8")
    contract_service = bootstrap_contract(settings)
    result = verify_dataset_integrity(settings.warehouse_path, contract_service, "daily_customer_payments")
    print(result.message)


if __name__ == "__main__":
    main()
