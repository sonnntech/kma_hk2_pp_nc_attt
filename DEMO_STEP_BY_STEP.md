# Demo Step By Step

Tài liệu này hướng dẫn chạy demo end-to-end cho đồ án theo từng bước, dùng trực tiếp khi trình bày với giảng viên hoặc hội đồng.

## 1. Mục tiêu demo

Sau khi hoàn thành demo, bạn cần chứng minh được 4 ý:

1. Pipeline ETL tạo dữ liệu và ghi vào warehouse thành công.
2. Hệ thống tạo hash và ghi proof lên blockchain mock thành công.
3. Audit engine đọc lại warehouse và xác minh toàn vẹn dữ liệu thành công.
4. Khi dữ liệu bị sửa trái phép, hệ thống phát hiện sai lệch ngay lập tức.

## 2. Chuẩn bị môi trường

Di chuyển vào thư mục project:

```bash
cd /home/sonnn38/Documents/BDS-projects/codex-project/blockchain-data-pipeline
```

Nếu chưa có file môi trường:

```bash
cp .env.example .env
```

Kiểm tra Python:

```bash
python3 --version
```

Kỳ vọng:

```text
Python 3.12.x
```

## 3. Giải thích nhanh cấu trúc khi mở đầu demo

Các thư mục nên giới thiệu ngắn:

- `contracts/`: smart contract Solidity và script deploy.
- `pipeline/`: ETL, hashing, lineage, mock source.
- `blockchain/`: Web3 client mock, transaction service, contract service.
- `audit/`: logic xác minh dữ liệu.
- `ui/`: dashboard trực quan hóa smart contract, proof, ledger và warehouse.
- `tests/`: test tự động và mô phỏng tamper attack.
- `warehouse/`: dữ liệu đầu ra sau ETL.
- `state/`: ledger, contract state, deployment state.

## 3A. Khởi động giao diện trực quan

Chạy lệnh:

```bash
python3 ui/server.py
```

Mở trình duyệt tại:

```text
http://127.0.0.1:8000
```

Những gì UI hiển thị:

- `Contract Address`
- `Warehouse Records`
- `Stored Proof`
- `Latest Block`
- `Contract Deployment`
- `Contract Proof State`
- `Contract Artifact`
- `Warehouse Payload`
- `Deterministic Ledger`

Các nút thao tác trong UI:

- `Deploy Contract`
- `Run Pipeline`
- `Store Current Proof`
- `Run Audit`
- `Simulate Tamper`
- `Reset Demo State`

Nếu demo trực quan, bạn có thể thực hiện gần như toàn bộ flow bằng UI thay vì chạy lần lượt bằng terminal.

## 4. Bước 1: Deploy smart contract

Chạy lệnh:

```bash
python3 contracts/deploy.py
```

Mục tiêu trình bày:

- Hệ thống đọc file Solidity [`contracts/DataPipelineGovernance.sol`](/home/sonnn38/Documents/BDS-projects/codex-project/blockchain-data-pipeline/contracts/DataPipelineGovernance.sol).
- Hệ thống sinh artifact tại [`contracts/artifacts/DataPipelineGovernance.json`](/home/sonnn38/Documents/BDS-projects/codex-project/blockchain-data-pipeline/contracts/artifacts/DataPipelineGovernance.json).
- Hệ thống sinh địa chỉ contract và lưu trạng thái deploy.

Kết quả mong đợi:

```text
0x2add3fe1437fc3af695488d8beb520ce85e6b695
```

File nên mở để minh họa:

- [`contracts/artifacts/DataPipelineGovernance.json`](/home/sonnn38/Documents/BDS-projects/codex-project/blockchain-data-pipeline/contracts/artifacts/DataPipelineGovernance.json)
- [`state/deployment.json`](/home/sonnn38/Documents/BDS-projects/codex-project/blockchain-data-pipeline/state/deployment.json)

## 5. Bước 2: Chạy ETL pipeline

Chạy lệnh:

```bash
python3 pipeline/etl_pipeline.py
```

Luồng cần giải thích khi demo:

1. `mock_sources.py` sinh dữ liệu giao dịch giả lập.
2. `etl_pipeline.py` transform dữ liệu và gắn `risk_band`.
3. `hashing.py` tính SHA256 cho dataset.
4. `lineage.py` sinh manifest lineage.
5. `warehouse_writer.py` ghi dữ liệu vào warehouse.
6. `contract_service.py` ghi proof lên blockchain mock.
7. `audit_engine.py` đọc lại warehouse để verify.

Kết quả mong đợi:

```json
{
  "contract_address": "0x2add3fe1437fc3af695488d8beb520ce85e6b695",
  "transaction_hash": "7014ac62fe49908b4accbff9e703e1b0bb537a310c7943168758d3153055145c",
  "dataset_hash": "fea7065a133eb17e94c916250462fe2ce06f04e36327a149063ca97828eb48b8",
  "manifest_hash": "0a3db80110198f27ec1175d8b96daa99e2f7312296de91759fa413a59e4c732f",
  "audit_message": "Hash Match - Data Integrity Verified",
  "warehouse_path": "warehouse/warehouse.json"
}
```

Điểm cần nhấn mạnh:

- `audit_message` phải là `Hash Match - Data Integrity Verified`.
- Điều này chứng minh dữ liệu trong warehouse vẫn khớp với proof đã ghi trên blockchain.

File nên mở để minh họa:

- [`warehouse/warehouse.json`](/home/sonnn38/Documents/BDS-projects/codex-project/blockchain-data-pipeline/warehouse/warehouse.json)
- [`state/contract_state.json`](/home/sonnn38/Documents/BDS-projects/codex-project/blockchain-data-pipeline/state/contract_state.json)
- [`state/blockchain_ledger.json`](/home/sonnn38/Documents/BDS-projects/codex-project/blockchain-data-pipeline/state/blockchain_ledger.json)

## 6. Bước 3: Giải thích warehouse và blockchain proof

Mở file warehouse:

- `records`: dữ liệu đã transform.
- `manifest`: metadata lineage gồm dataset name, record count, pipeline run id, source system, hash.

Mở file contract state:

- `dataset_hash`: hash của dữ liệu warehouse.
- `manifest_hash`: hash của lineage manifest.

Mở file ledger:

- `transaction_hash`: mã giao dịch.
- `block_hash`: hash của block.
- `signature`: chữ ký giả lập cho giao dịch ghi proof.

Thông điệp nên nói:

`Nếu ai đó sửa dữ liệu trong warehouse sau khi proof đã được commit, hash tính lại sẽ khác với dataset_hash đã lưu trong contract state.`

## 7. Bước 4: Chạy unit test

Chạy lệnh:

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
```

Mục tiêu trình bày:

- `test_pipeline.py`: kiểm tra pipeline chạy end-to-end.
- `test_blockchain.py`: kiểm tra compile, deploy, store proof.
- `test_audit.py`: kiểm tra verify integrity.

Kết quả mong đợi:

```text
Ran 3 tests in 0.008s
OK
```

## 8. Bước 5: Mô phỏng tấn công sửa dữ liệu

Chạy lệnh:

```bash
python3 tests/simulate_tamper_attack.py
```

Script này thực hiện:

1. Chạy pipeline để tạo dữ liệu hợp lệ.
2. Sửa trái phép giá trị `amount` của bản ghi đầu tiên trong warehouse.
3. Gọi audit engine để tính lại hash.
4. So sánh với proof đã lưu trên blockchain mock.

Kết quả mong đợi:

```text
Hash Mismatch - Data Tampering Detected
```

Thông điệp nên nhấn mạnh:

- Đây là bằng chứng hệ thống phát hiện được chỉnh sửa trái phép.
- Blockchain không ngăn việc sửa file local, nhưng cung cấp bằng chứng bất biến để phát hiện sai lệch.

## 9. Kịch bản thuyết trình gợi ý

Bạn có thể trình bày theo thứ tự sau:

1. Giới thiệu bài toán: ETL truyền thống khó chứng minh dữ liệu không bị sửa sau khi load.
2. Giới thiệu giải pháp: hash dữ liệu và lưu proof lên blockchain.
3. Deploy contract.
4. Chạy pipeline và cho thấy dữ liệu được ghi vào warehouse.
5. Mở `warehouse.json`, `contract_state.json`, `blockchain_ledger.json`.
6. Chạy audit thành công và nhấn mạnh `Hash Match`.
7. Chạy tamper attack và nhấn mạnh `Hash Mismatch`.
8. Kết luận: hệ thống đảm bảo traceability và tamper evidence.

## 10. Câu hỏi hội đồng có thể hỏi

### Blockchain ở đây bảo vệ cái gì?

Blockchain bảo vệ tính bất biến của proof, không bảo vệ trực tiếp file warehouse. Nếu file bị sửa, proof trên blockchain vẫn giữ nguyên nên hệ thống phát hiện được mismatch.

### Vì sao dùng hash?

Hash tạo ra dấu vân tay duy nhất cho dữ liệu. Chỉ cần thay đổi rất nhỏ trong dữ liệu thì hash sẽ thay đổi hoàn toàn.

### Vì sao có lineage manifest?

Lineage manifest lưu metadata của pipeline run để tăng khả năng truy vết: dữ liệu nào, sinh lúc nào, từ nguồn nào, ghi vào đâu.

### Đây có phải blockchain thật không?

Bản hiện tại là proof of concept offline với deterministic mock ledger để demo end-to-end trong môi trường không có node Ethereum. Có thể thay bằng Web3 thực và smart contract thật trong giai đoạn mở rộng.

## 11. Các file nên mở khi demo

- [`pipeline/etl_pipeline.py`](/home/sonnn38/Documents/BDS-projects/codex-project/blockchain-data-pipeline/pipeline/etl_pipeline.py)
- [`pipeline/hashing.py`](/home/sonnn38/Documents/BDS-projects/codex-project/blockchain-data-pipeline/pipeline/hashing.py)
- [`audit/audit_engine.py`](/home/sonnn38/Documents/BDS-projects/codex-project/blockchain-data-pipeline/audit/audit_engine.py)
- [`contracts/DataPipelineGovernance.sol`](/home/sonnn38/Documents/BDS-projects/codex-project/blockchain-data-pipeline/contracts/DataPipelineGovernance.sol)
- [`warehouse/warehouse.json`](/home/sonnn38/Documents/BDS-projects/codex-project/blockchain-data-pipeline/warehouse/warehouse.json)
- [`state/contract_state.json`](/home/sonnn38/Documents/BDS-projects/codex-project/blockchain-data-pipeline/state/contract_state.json)
- [`state/blockchain_ledger.json`](/home/sonnn38/Documents/BDS-projects/codex-project/blockchain-data-pipeline/state/blockchain_ledger.json)

## 12. Lệnh demo đầy đủ

```bash
cd /home/sonnn38/Documents/BDS-projects/codex-project/blockchain-data-pipeline
cp .env.example .env
python3 ui/server.py
python3 contracts/deploy.py
python3 pipeline/etl_pipeline.py
python3 -m unittest discover -s tests -p 'test_*.py'
python3 tests/simulate_tamper_attack.py
```

## 13. Kết quả cuối cùng cần đạt

Checklist khi demo:

- Contract deploy thành công.
- Artifact được sinh ra.
- Warehouse có dữ liệu.
- Contract state có `dataset_hash`.
- Ledger có transaction mined.
- Audit trả về `Hash Match - Data Integrity Verified`.
- Tamper simulation trả về `Hash Mismatch - Data Tampering Detected`.
