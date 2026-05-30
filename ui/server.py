from __future__ import annotations

import html
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlencode
from wsgiref.simple_server import make_server

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from audit.audit_engine import verify_dataset_integrity
from blockchain.contract_service import ContractService
from blockchain.transaction_service import TransactionService
from blockchain.web3_client import Web3Client
from infrastructure.logging import configure_logging
from infrastructure.settings import Settings, get_settings
from pipeline.etl_pipeline import bootstrap_contract, run_pipeline
from pipeline.hashing import sha256_digest
from pipeline.warehouse_writer import read_warehouse


@dataclass(frozen=True)
class ActionFeedback:
    level: str
    title: str
    detail: str


def load_json(path: Path) -> dict[str, Any] | list[Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def build_contract_service(settings: Settings) -> ContractService:
    web3_client = Web3Client(settings.ledger_path)
    tx_service = TransactionService(web3_client, settings.blockchain_private_key, settings.blockchain_account)
    return ContractService(
        settings.contract_artifact_path,
        settings.contract_state_path,
        settings.deployment_state_path,
        tx_service,
    )


def compute_audit_snapshot(settings: Settings) -> ActionFeedback | None:
    if not settings.warehouse_path.exists() or not settings.contract_state_path.exists():
        return None
    contract_state = load_json(settings.contract_state_path) or {}
    proofs = contract_state.get("proofs", {})
    if "daily_customer_payments" not in proofs:
        return None
    result = verify_dataset_integrity(settings.warehouse_path, build_contract_service(settings), "daily_customer_payments")
    level = "success" if result.status == "pass" else "danger"
    return ActionFeedback(level, "Audit Result", result.message)


def deploy_only(settings: Settings) -> ActionFeedback:
    service = bootstrap_contract(settings)
    deployment = load_json(settings.deployment_state_path) or {}
    return ActionFeedback(
        "success",
        "Contract deployed",
        f"Contract address: {deployment.get('contract_address', 'unknown')} | Connected: {service.transaction_service.web3_client.is_connected()}",
    )


def store_current_proof(settings: Settings) -> ActionFeedback:
    if not settings.warehouse_path.exists():
        return ActionFeedback("warning", "Warehouse missing", "Run the pipeline first so there is a dataset to anchor.")
    service = build_contract_service(settings)
    if not settings.deployment_state_path.exists():
        bootstrap_contract(settings)
    warehouse = read_warehouse(settings.warehouse_path)
    dataset_hash = sha256_digest(warehouse["records"])
    manifest_hash = sha256_digest(warehouse["manifest"])
    receipt = service.store_proof(warehouse["dataset_name"], dataset_hash, manifest_hash)
    return ActionFeedback(
        "success",
        "Proof stored",
        f"Transaction mined in block {receipt['block_number']} with tx hash {receipt['transaction_hash']}.",
    )


def tamper_warehouse(settings: Settings) -> ActionFeedback:
    if not settings.warehouse_path.exists():
        return ActionFeedback("warning", "Warehouse missing", "Run the pipeline before simulating tampering.")
    warehouse = read_warehouse(settings.warehouse_path)
    warehouse["records"][0]["amount"] = 9999.99
    warehouse["records"][0]["risk_band"] = "critical"
    settings.warehouse_path.write_text(json.dumps(warehouse, indent=2), encoding="utf-8")
    result = compute_audit_snapshot(settings)
    detail = result.detail if result else "Warehouse changed."
    return ActionFeedback("danger", "Tamper simulation applied", detail)


def reset_demo_state(settings: Settings) -> ActionFeedback:
    for path in [
        settings.ledger_path,
        settings.contract_state_path,
        settings.deployment_state_path,
        settings.contract_artifact_path,
        settings.warehouse_path,
    ]:
        if path.exists():
            path.unlink()
    return ActionFeedback("info", "Demo state reset", "Ledger, deployment, proof, artifact, and warehouse files were cleared.")


def perform_action(settings: Settings, action: str) -> ActionFeedback:
    if action == "deploy":
        return deploy_only(settings)
    if action == "run_pipeline":
        result = run_pipeline(settings)
        return ActionFeedback("success", "Pipeline executed", f"Audit verdict: {result.audit_message}")
    if action == "store_proof":
        return store_current_proof(settings)
    if action == "audit":
        result = compute_audit_snapshot(settings)
        if result is None:
            return ActionFeedback("warning", "Audit unavailable", "Run deploy and pipeline first so proof and warehouse data exist.")
        return result
    if action == "tamper":
        return tamper_warehouse(settings)
    if action == "reset":
        return reset_demo_state(settings)
    return ActionFeedback("warning", "Unknown action", f"Unsupported action: {action}")


def render_json_block(data: Any, empty_message: str) -> str:
    if data is None:
        return f"<div class='empty'>{html.escape(empty_message)}</div>"
    return f"<pre>{html.escape(json.dumps(data, indent=2))}</pre>"


def dashboard_page(settings: Settings, feedback: ActionFeedback | None = None) -> bytes:
    deployment = load_json(settings.deployment_state_path)
    artifact = load_json(settings.contract_artifact_path)
    contract_state = load_json(settings.contract_state_path)
    ledger = load_json(settings.ledger_path)
    warehouse = load_json(settings.warehouse_path)
    audit_snapshot = compute_audit_snapshot(settings)
    latest_block = ledger["blocks"][-1] if isinstance(ledger, dict) and ledger.get("blocks") else None
    record_count = len(warehouse.get("records", [])) if isinstance(warehouse, dict) else 0
    proofs = contract_state.get("proofs", {}) if isinstance(contract_state, dict) else {}
    proof = proofs.get("daily_customer_payments")
    contract_address = deployment.get("contract_address", "Not deployed") if isinstance(deployment, dict) else "Not deployed"
    banner = ""
    if feedback is not None:
        banner = (
            f"<section class='banner {feedback.level}'>"
            f"<strong>{html.escape(feedback.title)}</strong>"
            f"<span>{html.escape(feedback.detail)}</span>"
            "</section>"
        )
    audit_label = audit_snapshot.detail if audit_snapshot else "Waiting for pipeline proof"
    audit_class = audit_snapshot.level if audit_snapshot else "neutral"
    body = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Blockchain Smart Contract Dashboard</title>
  <style>
    :root {{
      --bg: #f2efe8;
      --panel: rgba(255,255,255,0.78);
      --ink: #1f1d1b;
      --muted: #5f584f;
      --accent: #bf5b2c;
      --accent-2: #23443c;
      --success: #1d6b45;
      --warning: #9a6700;
      --danger: #a3312d;
      --neutral: #6b7280;
      --border: rgba(31,29,27,0.10);
      --shadow: 0 24px 60px rgba(45, 29, 18, 0.12);
      --radius: 24px;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "IBM Plex Sans", "Aptos", "Segoe UI", sans-serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top left, rgba(191,91,44,0.18), transparent 28%),
        radial-gradient(circle at bottom right, rgba(35,68,60,0.20), transparent 26%),
        linear-gradient(135deg, #f7f1e6 0%, #efe7da 52%, #f4f4ef 100%);
      min-height: 100vh;
    }}
    .shell {{
      width: min(1380px, calc(100% - 32px));
      margin: 24px auto 40px;
    }}
    .hero {{
      display: grid;
      grid-template-columns: 1.2fr 0.8fr;
      gap: 18px;
      align-items: stretch;
    }}
    .hero-card, .panel {{
      background: var(--panel);
      backdrop-filter: blur(18px);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      box-shadow: var(--shadow);
    }}
    .hero-card {{
      padding: 28px;
      position: relative;
      overflow: hidden;
    }}
    .hero-card::after {{
      content: "";
      position: absolute;
      inset: auto -40px -40px auto;
      width: 180px;
      height: 180px;
      background: linear-gradient(135deg, rgba(191,91,44,0.25), rgba(35,68,60,0.15));
      border-radius: 40px;
      transform: rotate(18deg);
    }}
    .eyebrow {{
      display: inline-block;
      font-size: 12px;
      letter-spacing: 0.16em;
      text-transform: uppercase;
      color: var(--accent-2);
      margin-bottom: 12px;
      font-weight: 700;
    }}
    h1 {{
      margin: 0 0 10px;
      font-family: "Iowan Old Style", "Palatino Linotype", serif;
      font-size: clamp(2rem, 3.2vw, 3.3rem);
      line-height: 1.02;
      max-width: 10ch;
    }}
    .hero p {{
      margin: 0;
      color: var(--muted);
      max-width: 64ch;
      line-height: 1.6;
      position: relative;
      z-index: 1;
    }}
    .badge-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 14px;
      padding: 24px;
    }}
    .badge {{
      padding: 16px;
      border-radius: 18px;
      background: rgba(255,255,255,0.74);
      border: 1px solid var(--border);
    }}
    .badge span {{
      display: block;
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.12em;
      margin-bottom: 8px;
    }}
    .badge strong {{
      display: block;
      font-size: 1rem;
      line-height: 1.4;
      word-break: break-word;
    }}
    .banner {{
      margin: 18px 0 0;
      padding: 14px 18px;
      border-radius: 18px;
      display: flex;
      gap: 14px;
      align-items: center;
      border: 1px solid transparent;
      animation: slideUp 220ms ease-out;
    }}
    .banner strong {{ min-width: 150px; }}
    .banner.success {{ background: rgba(29,107,69,0.12); color: var(--success); border-color: rgba(29,107,69,0.25); }}
    .banner.warning {{ background: rgba(154,103,0,0.12); color: var(--warning); border-color: rgba(154,103,0,0.25); }}
    .banner.danger {{ background: rgba(163,49,45,0.12); color: var(--danger); border-color: rgba(163,49,45,0.25); }}
    .banner.info {{ background: rgba(35,68,60,0.12); color: var(--accent-2); border-color: rgba(35,68,60,0.22); }}
    .toolbar {{
      margin-top: 18px;
      display: grid;
      grid-template-columns: repeat(6, minmax(0, 1fr));
      gap: 12px;
    }}
    form {{ margin: 0; }}
    button {{
      width: 100%;
      border: none;
      border-radius: 16px;
      padding: 14px 16px;
      font: inherit;
      font-weight: 700;
      cursor: pointer;
      transition: transform 140ms ease, box-shadow 140ms ease, opacity 140ms ease;
      box-shadow: 0 10px 18px rgba(31,29,27,0.08);
    }}
    button:hover {{ transform: translateY(-1px); }}
    .primary {{ background: linear-gradient(135deg, #c76b34, #bf5b2c); color: white; }}
    .secondary {{ background: linear-gradient(135deg, #31594f, #23443c); color: white; }}
    .ghost {{ background: rgba(255,255,255,0.82); color: var(--ink); }}
    .warn {{ background: linear-gradient(135deg, #b14038, #8f2f2a); color: white; }}
    .layout {{
      margin-top: 22px;
      display: grid;
      grid-template-columns: 1.15fr 0.85fr;
      gap: 18px;
    }}
    .stack {{
      display: grid;
      gap: 18px;
    }}
    .panel {{
      padding: 22px;
    }}
    .panel h2 {{
      margin: 0 0 8px;
      font-family: "Iowan Old Style", "Palatino Linotype", serif;
      font-size: 1.45rem;
    }}
    .panel p {{
      margin: 0 0 18px;
      color: var(--muted);
      line-height: 1.5;
    }}
    .status-row {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
      margin-bottom: 18px;
    }}
    .stat {{
      padding: 14px;
      border-radius: 16px;
      background: rgba(255,255,255,0.66);
      border: 1px solid var(--border);
    }}
    .stat span {{
      display: block;
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.12em;
      margin-bottom: 6px;
    }}
    .stat strong {{
      display: block;
      font-size: 0.96rem;
      line-height: 1.35;
      word-break: break-word;
    }}
    .pill {{
      display: inline-flex;
      align-items: center;
      border-radius: 999px;
      padding: 8px 12px;
      font-weight: 700;
      font-size: 0.92rem;
    }}
    .pill.success {{ background: rgba(29,107,69,0.13); color: var(--success); }}
    .pill.danger {{ background: rgba(163,49,45,0.12); color: var(--danger); }}
    .pill.neutral {{ background: rgba(107,114,128,0.12); color: var(--neutral); }}
    pre {{
      margin: 0;
      overflow: auto;
      padding: 16px;
      border-radius: 18px;
      background: #171614;
      color: #f6f1e8;
      font-family: "Berkeley Mono", "Fira Code", monospace;
      font-size: 13px;
      line-height: 1.55;
      min-height: 140px;
    }}
    .empty {{
      padding: 24px;
      border-radius: 18px;
      border: 1px dashed var(--border);
      color: var(--muted);
      background: rgba(255,255,255,0.46);
    }}
    .footer {{
      margin-top: 18px;
      color: var(--muted);
      font-size: 0.95rem;
      text-align: center;
    }}
    @keyframes slideUp {{
      from {{ opacity: 0; transform: translateY(6px); }}
      to {{ opacity: 1; transform: translateY(0); }}
    }}
    @media (max-width: 980px) {{
      .hero, .layout {{ grid-template-columns: 1fr; }}
      .toolbar {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      .status-row {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
    }}
    @media (max-width: 640px) {{
      .shell {{ width: min(100% - 20px, 1380px); margin-top: 10px; }}
      .hero-card, .panel {{ border-radius: 20px; }}
      .hero-card {{ padding: 22px; }}
      .badge-grid, .panel {{ padding: 18px; }}
      .toolbar, .status-row {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <main class="shell">
    <section class="hero">
      <article class="hero-card">
        <span class="eyebrow">Blockchain Integrity Demo</span>
        <h1>Smart Contract Control Room</h1>
        <p>Visual dashboard for the mock Solidity deployment, proof submission, mined transactions, warehouse state, and audit verdict. Use the controls below to drive the demo instead of relying only on terminal commands.</p>
      </article>
      <aside class="hero-card badge-grid">
        <div class="badge"><span>Contract Address</span><strong>{html.escape(contract_address)}</strong></div>
        <div class="badge"><span>Warehouse Records</span><strong>{record_count}</strong></div>
        <div class="badge"><span>Stored Proof</span><strong>{html.escape(proof['dataset_hash'][:20] + '...' if proof else 'No proof yet')}</strong></div>
        <div class="badge"><span>Latest Block</span><strong>{html.escape(str(latest_block['block_number']) if latest_block else 'No block mined')}</strong></div>
      </aside>
    </section>
    {banner}
    <section class="toolbar">
      <form method="post" action="/action"><input type="hidden" name="action" value="deploy"><button class="primary">Deploy Contract</button></form>
      <form method="post" action="/action"><input type="hidden" name="action" value="run_pipeline"><button class="secondary">Run Pipeline</button></form>
      <form method="post" action="/action"><input type="hidden" name="action" value="store_proof"><button class="ghost">Store Current Proof</button></form>
      <form method="post" action="/action"><input type="hidden" name="action" value="audit"><button class="ghost">Run Audit</button></form>
      <form method="post" action="/action"><input type="hidden" name="action" value="tamper"><button class="warn">Simulate Tamper</button></form>
      <form method="post" action="/action"><input type="hidden" name="action" value="reset"><button class="ghost">Reset Demo State</button></form>
    </section>
    <section class="layout">
      <div class="stack">
        <section class="panel">
          <h2>Verification Snapshot</h2>
          <p>Fast summary of the blockchain-linked warehouse state.</p>
          <div class="status-row">
            <div class="stat"><span>Web3 Connectivity</span><strong>{'Connected' if settings.ledger_path.exists() else 'Not initialized'}</strong></div>
            <div class="stat"><span>Artifact</span><strong>{'Ready' if artifact else 'Missing'}</strong></div>
            <div class="stat"><span>Proof Entries</span><strong>{len(proofs)}</strong></div>
            <div class="stat"><span>Blocks</span><strong>{len(ledger.get('blocks', [])) if isinstance(ledger, dict) else 0}</strong></div>
          </div>
          <div class="pill {audit_class}">{html.escape(audit_label)}</div>
        </section>
        <section class="panel">
          <h2>Warehouse Payload</h2>
          <p>Transformed dataset persisted by the ETL pipeline.</p>
          {render_json_block(warehouse, "Warehouse file not created yet. Run the pipeline to generate records.")}
        </section>
        <section class="panel">
          <h2>Deterministic Ledger</h2>
          <p>Most recent mined transaction and block hash.</p>
          {render_json_block(latest_block, "No mined block yet. Store a proof to populate the ledger.")}
        </section>
      </div>
      <div class="stack">
        <section class="panel">
          <h2>Contract Deployment</h2>
          <p>Deployment metadata and compiled Solidity artifact.</p>
          {render_json_block(deployment, "Contract not deployed yet.")}
        </section>
        <section class="panel">
          <h2>Contract Proof State</h2>
          <p>Current dataset and manifest hashes stored by the contract service.</p>
          {render_json_block(contract_state, "No contract state yet.")}
        </section>
        <section class="panel">
          <h2>Contract Artifact</h2>
          <p>Generated ABI, bytecode fingerprint, and source hash.</p>
          {render_json_block(artifact, "Artifact not built yet.")}
        </section>
      </div>
    </section>
    <div class="footer">Start the dashboard with <code>python3 ui/server.py</code> then open <code>http://127.0.0.1:8000</code>.</div>
  </main>
</body>
</html>"""
    return body.encode("utf-8")


def parse_post_body(environ: dict[str, Any]) -> dict[str, list[str]]:
    content_length = int(environ.get("CONTENT_LENGTH", "0") or "0")
    body = environ["wsgi.input"].read(content_length).decode("utf-8")
    return parse_qs(body)


def application(environ: dict[str, Any], start_response: Any):
    settings = get_settings()
    configure_logging(settings.log_level)
    method = environ.get("REQUEST_METHOD", "GET")
    path = environ.get("PATH_INFO", "/")
    if method == "GET" and path == "/api/state":
        payload = {
            "deployment": load_json(settings.deployment_state_path),
            "artifact": load_json(settings.contract_artifact_path),
            "contract_state": load_json(settings.contract_state_path),
            "ledger": load_json(settings.ledger_path),
            "warehouse": load_json(settings.warehouse_path),
        }
        body = json.dumps(payload, indent=2).encode("utf-8")
        start_response("200 OK", [("Content-Type", "application/json; charset=utf-8")])
        return [body]
    if method == "POST" and path == "/action":
        form_data = parse_post_body(environ)
        action = form_data.get("action", [""])[0]
        feedback = perform_action(settings, action)
        query = urlencode(asdict(feedback))
        start_response("303 See Other", [("Location", f"/?{query}")])
        return [b""]
    if method == "GET" and path == "/":
        params = parse_qs(environ.get("QUERY_STRING", ""))
        feedback = None
        if {"level", "title", "detail"}.issubset(params):
            feedback = ActionFeedback(
                params["level"][0],
                params["title"][0],
                params["detail"][0],
            )
        body = dashboard_page(settings, feedback)
        start_response("200 OK", [("Content-Type", "text/html; charset=utf-8")])
        return [body]
    start_response("404 Not Found", [("Content-Type", "text/plain; charset=utf-8")])
    return [b"Not Found"]


def main() -> None:
    host = "127.0.0.1"
    port = 8000
    with make_server(host, port, application) as server:
        print(f"Dashboard running at http://{host}:{port}")
        server.serve_forever()


if __name__ == "__main__":
    main()
