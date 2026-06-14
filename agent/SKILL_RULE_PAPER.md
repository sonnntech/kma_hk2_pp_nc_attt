Bạn là Senior LaTeX Engineer, Academic Writing Assistant và Research Engineer.

Hãy tạo cho tôi một project LaTeX hoàn chỉnh cho đề tài luận văn thạc sĩ:

“Nghiên cứu xây dựng mô hình ứng dụng Blockchain nhằm đảm bảo tính toàn vẹn và truy vết dữ liệu trong hệ thống Data Pipeline”

Mục tiêu:

* Viết khung luận văn thạc sĩ theo chuẩn học thuật.
* Format bằng LaTeX, dễ build, dễ chỉnh sửa.
* Nội dung bám theo cấu trúc Technical & Scientific Report Writing:

    * Title
    * Abstract
    * Introduction
    * Body
    * Figures / Tables
    * Conclusions
    * References
* Đồng thời tổ chức theo cấu trúc luận văn:

    * Chapter 1: Introduction
    * Chapter 2: Related Works / State of the Art
    * Chapter 3: Conceptual Model
    * Chapter 4: Experimentation / Simulation
    * Chapter 5: Analysis of Experimental Results
    * Chapter 6: Conclusion and Future Works

Yêu cầu project:

1. Tạo cấu trúc thư mục:

thesis/
├── main.tex
├── chapters/
│   ├── 00_abstract.tex
│   ├── 01_introduction.tex
│   ├── 02_related_works.tex
│   ├── 03_conceptual_model.tex
│   ├── 04_experimentation.tex
│   ├── 05_analysis.tex
│   └── 06_conclusion_future_work.tex
├── appendices/
│   └── appendix_a.tex
├── figures/
├── tables/
├── references.bib
├── glossary.tex
├── acronyms.tex
├── Makefile
└── README.md

2. main.tex phải có:

* Vietnamese + English support nếu có thể.
* UTF-8.
* A4 paper.
* Table of Contents.
* List of Figures.
* List of Tables.
* Abstract.
* Acronyms.
* Glossary.
* Bibliography.
* Appendix.
* Page numbering phù hợp cho luận văn.
* Hỗ trợ citation bằng biblatex hoặc BibTeX.
* Ưu tiên style IEEE citation dạng [1], [2].

3. Nội dung từng chương:

Chapter 1: Introduction
Bao gồm:

* Background
* Problem Statement
* Research Motivation
* Research Objectives
* Research Questions
* Scope and Limitations
* Expected Contributions
* Thesis Organization

Nội dung cần định hướng:

* Data Pipeline thường gồm ingestion, transformation, storage, serving.
* Vấn đề cần giải quyết là đảm bảo tính toàn vẹn dữ liệu và khả năng truy vết lineage.
* Các rủi ro gồm data tampering, unauthorized modification, missing lineage, weak auditability.
* Blockchain được đề xuất như một metadata registry bất biến để lưu hash, proof và lineage metadata.
* Dữ liệu lớn vẫn lưu off-chain; blockchain chỉ lưu metadata/hash/proof.

Chapter 2: Related Works / State of the Art
Bao gồm:

* Data Pipeline and Data Engineering
* Data Lineage and Data Provenance
* Data Integrity Verification
* Blockchain Fundamentals
* Smart Contracts
* On-chain vs Off-chain Architecture
* Existing Blockchain-based Data Lineage Approaches
* Research Gap

Yêu cầu:

* Tạo placeholder citation \cite{} cho từng claim quan trọng.
* Không bịa tài liệu thật nếu chưa có nguồn.
* Trong references.bib tạo các TODO entry mẫu để tôi bổ sung paper thật.

Chapter 3: Conceptual Model
Bao gồm:

* Proposed Architecture
* System Components
* Off-chain Data Storage Layer
* On-chain Metadata Registry Layer
* Hashing and Proof Generation
* Lineage Recording Mechanism
* Smart Contract Design
* Verification Workflow
* Threat Model
* Security Assumptions

Mô hình đề xuất gồm:

* Airflow/Data Pipeline layer
* Data source
* Transformation job
* Data warehouse / ClickHouse / object storage
* Metadata extractor
* Hash generator
* Blockchain smart contract
* Verification service
* Audit dashboard

Cần tạo sẵn figure placeholder bằng TikZ hoặc Mermaid-compatible comment:

* Figure 3.1: Hybrid Off-chain and On-chain Architecture
* Figure 3.2: Data Lineage Verification Workflow
* Figure 3.3: Smart Contract Interaction Flow

Chapter 4: Experimentation / Simulation
Bao gồm:

* Experimental Objectives
* Experimental Environment
* Dataset Description
* Pipeline Scenarios
* Blockchain Network Setup
* Test Cases
* Evaluation Metrics
* Reproducibility Notes

Kịch bản thực nghiệm:

* Normal pipeline execution.
* Data tampering after transformation.
* Missing lineage metadata.
* Hash mismatch detection.
* Re-run pipeline and compare proof history.

Metrics:

* Verification accuracy.
* Tampering detection rate.
* Hash generation time.
* Blockchain write latency.
* Verification latency.
* Storage overhead.
* Throughput impact.

Chapter 5: Analysis of Experimental Results
Bao gồm:

* Result Tables
* Performance Analysis
* Security Analysis
* Comparison with Non-blockchain Baseline
* Discussion
* Limitations
* Validity Threats

Tạo bảng placeholder:

* Table 5.1: Tampering Detection Results
* Table 5.2: Blockchain Write Latency
* Table 5.3: Verification Latency
* Table 5.4: Storage Overhead Comparison

Chapter 6: Conclusion and Future Works
Bao gồm:

* Summary of Research
* Answers to Research Questions
* Main Contributions
* Practical Implications
* Limitations
* Future Work

Future work gợi ý:

* Integration with DataHub lineage.
* Support multi-source business intelligence systems.
* Optimize smart contract gas cost.
* Add privacy-preserving proof.
* Extend to real-time streaming pipelines.

4. Abstract:
   Viết sẵn bản nháp 200–300 từ bằng tiếng Anh.
   Sau đó thêm một bản “Tóm tắt” tiếng Việt tương ứng.
   Abstract phải gồm:

* Problem
* Method
* Result placeholder
* Contribution
* Conclusion
  Không cite trong Abstract.

5. Style học thuật:

* Không dùng từ mơ hồ như: many, few, nowadays, obviously, clearly, perfect.
* Không dùng “I will describe”, “you will read”.
* Không dùng giọng văn quảng cáo.
* Mọi claim quan trọng phải có TODO citation.
* Các acronym lần đầu phải viết đầy đủ, ví dụ: Data Pipeline (DP), Blockchain (BC), Data Lineage (DL).

6. References:

* Tạo references.bib với các nhóm placeholder:

    * blockchain
    * data lineage
    * data provenance
    * data integrity
    * smart contract
    * data pipeline
    * data governance
* Không tự tạo paper giả.
* Nếu chưa có paper thật thì dùng comment TODO.

7. Build:

* Tạo Makefile với các lệnh:

    * make build
    * make clean
* README.md hướng dẫn:

    * Cài TeX Live hoặc MikTeX.
    * Build bằng latexmk hoặc xelatex.
    * Cách thêm citation.
    * Cách thêm hình.
    * Cách thêm bảng.

8. Output mong muốn:

* Sinh toàn bộ file LaTeX.
* Nội dung có thể build ngay.
* Nếu thiếu package thì tự điều chỉnh.
* Sau khi tạo xong, chạy build thử.
* Nếu lỗi, tự sửa cho đến khi build thành công.
* Không hỏi lại tôi. Hãy tự đưa ra quyết định hợp lý theo chuẩn luận văn kỹ thuật.

9. Ràng buộc quan trọng:

* Không hardcode thông tin trường/khoa nếu chưa có.
* Để placeholder:

    * University Name
    * Faculty Name
    * Student Name
    * Supervisor Name
    * Student ID
    * Submission Date
* Luận văn nên theo hướng kỹ thuật ứng dụng, phù hợp ngành Cybersecurity / Data Engineering.
* Ưu tiên tính rõ ràng, mạch lạc, có khả năng bảo vệ trước hội đồng.
