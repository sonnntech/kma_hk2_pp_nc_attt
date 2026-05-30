from __future__ import annotations

from blockchain.contract_service import ContractService
from pipeline.hashing import sha256_digest
from pipeline.warehouse_writer import read_warehouse
from audit.verifier import VerificationResult


def verify_dataset_integrity(warehouse_path, contract_service: ContractService, dataset_name: str) -> VerificationResult:
    warehouse = read_warehouse(warehouse_path)
    actual_hash = sha256_digest(warehouse["records"])
    proof = contract_service.get_proof(dataset_name)
    expected_hash = proof["dataset_hash"]
    if actual_hash == expected_hash:
        return VerificationResult("pass", expected_hash, actual_hash, "Hash Match - Data Integrity Verified")
    return VerificationResult("fail", expected_hash, actual_hash, "Hash Mismatch - Data Tampering Detected")
