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

    # Select appropriate SVG icon for verification status
    if audit_class == "success":
        svg_icon = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
          <path fill-rule="evenodd" d="M2.25 12c0-5.385 4.365-9.75 9.75-9.75s9.75 4.365 9.75 9.75-4.365 9.75-9.75 9.75S2.25 17.385 2.25 12zm13.36-1.814a.75.75 0 10-1.22-.872l-3.236 4.53L9.53 12.22a.75.75 0 00-1.06 1.06l2.25 2.25a.75.75 0 001.14-.094l3.748-5.25z" clip-rule="evenodd" />
        </svg>"""
    elif audit_class == "danger":
        svg_icon = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
          <path fill-rule="evenodd" d="M12 2.25c-5.385 0-9.75 4.365-9.75 9.75s4.365 9.75 9.75 9.75 9.75-4.365 9.75-9.75S17.385 2.25 12 2.25zm-1.72 6.97a.75.75 0 10-1.06 1.06L10.94 12l-1.72 1.72a.75.75 0 101.06 1.06L12 13.06l1.72 1.72a.75.75 0 101.06-1.06L13.06 12l1.72-1.72a.75.75 0 10-1.06-1.06L12 10.94l-1.72-1.72z" clip-rule="evenodd" />
        </svg>"""
    else:
        svg_icon = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
          <path fill-rule="evenodd" d="M12 2.25c-5.385 0-9.75 4.365-9.75 9.75s4.365 9.75 9.75 9.75 9.75-4.365 9.75-9.75S17.385 2.25 12 2.25zM12 7.5a.75.75 0 01.75.75v5.25a.75.75 0 01-1.5 0V8.25A.75.75 0 0112 7.5zm0 10a1 1 0 100-2 1 1 0 000 2z" clip-rule="evenodd" />
        </svg>"""

    body = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Blockchain Smart Contract Dashboard</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg: #ffffff;
      --panel: #ffffff;
      --ink: #0f172a;
      --muted: #475569;
      --accent: #2563eb;
      --accent-2: #4f46e5;
      --success: #10b981;
      --warning: #f59e0b;
      --danger: #ef4444;
      --neutral: #64748b;
      --border: #e2e8f0;
      --shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
      --radius: 10px;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: 'Outfit', sans-serif;
      color: var(--ink);
      background: var(--bg);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 0 16px;
    }}
    .shell {{
      width: 100%;
      max-width: 1100px;
      margin: 40px auto;
    }}
    .header-panel {{
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 24px;
      display: grid;
      grid-template-columns: 1.2fr 1fr;
      gap: 24px;
      align-items: center;
      margin-bottom: 20px;
      box-shadow: var(--shadow);
    }}
    .badge-tag {{
      background: #eff6ff;
      border: 1px solid #bfdbfe;
      padding: 4px 10px;
      border-radius: 99px;
      font-size: 11px;
      font-weight: 600;
      letter-spacing: 0.05em;
      text-transform: uppercase;
      color: var(--accent);
      display: inline-block;
      margin-bottom: 8px;
    }}
    h1 {{
      margin: 0 0 6px;
      font-size: 28px;
      font-weight: 800;
      letter-spacing: -0.02em;
      color: var(--ink);
    }}
    .brand p {{
      margin: 0;
      color: var(--muted);
      font-size: 14px;
      line-height: 1.5;
    }}
    .quick-stats {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
    }}
    .stat-card {{
      background: #f8fafc;
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 12px;
      transition: all 0.15s ease;
    }}
    .stat-card:hover {{
      background: #f1f5f9;
      border-color: #cbd5e1;
    }}
    .stat-title {{
      display: block;
      font-size: 10px;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.05em;
      margin-bottom: 4px;
      font-weight: 600;
    }}
    .stat-value {{
      display: block;
      font-size: 14px;
      font-weight: 700;
      color: var(--ink);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }}
    .text-accent {{ color: var(--accent); }}
    .text-accent2 {{ color: var(--accent-2); }}
    
    .banner {{
      margin-bottom: 20px;
      padding: 12px 16px;
      border-radius: 8px;
      display: flex;
      gap: 12px;
      align-items: center;
      border: 1px solid transparent;
      animation: slideDown 0.2s ease-out;
      font-size: 14px;
    }}
    .banner.success {{ background: #ecfdf5; border-color: #a7f3d0; color: #065f46; }}
    .banner.warning {{ background: #fffbeb; border-color: #fde68a; color: #92400e; }}
    .banner.danger {{ background: #fff5f5; border-color: #fecdd3; color: #991b1b; }}
    .banner.info {{ background: #f5f3ff; border-color: #ddd6fe; color: #5b21b6; }}
    
    .toolbar-panel {{
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 20px;
      margin-bottom: 20px;
      box-shadow: var(--shadow);
    }}
    .panel-section-title {{
      display: block;
      font-size: 10px;
      font-weight: 700;
      color: var(--muted);
      letter-spacing: 0.1em;
      margin-bottom: 12px;
      text-transform: uppercase;
    }}
    .toolbar-grid {{
      display: grid;
      grid-template-columns: repeat(6, 1fr);
      gap: 10px;
    }}
    .btn {{
      width: 100%;
      border: 1px solid transparent;
      border-radius: 6px;
      padding: 12px 8px;
      font-family: 'Outfit', sans-serif;
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.15s ease;
      display: flex;
      align-items: center;
      justify-content: center;
      text-align: center;
    }}
    .btn:hover {{
      transform: translateY(-1px);
    }}
    .btn:active {{
      transform: translateY(0);
    }}
    .btn-deploy {{
      background: #2563eb;
      color: white;
      border-color: #2563eb;
    }}
    .btn-deploy:hover {{ background: #1d4ed8; }}
    
    .btn-run {{
      background: #4f46e5;
      color: white;
      border-color: #4f46e5;
    }}
    .btn-run:hover {{ background: #4338ca; }}
    
    .btn-proof {{
      background: #ffffff;
      color: #2563eb;
      border-color: #cbd5e1;
    }}
    .btn-proof:hover {{ background: #f8fafc; border-color: #94a3b8; }}
    
    .btn-audit {{
      background: #ffffff;
      color: #10b981;
      border-color: #cbd5e1;
    }}
    .btn-audit:hover {{ background: #f8fafc; border-color: #94a3b8; }}
    
    .btn-tamper {{
      background: #dc2626;
      color: white;
      border-color: #dc2626;
    }}
    .btn-tamper:hover {{ background: #b91c1c; }}
    
    .btn-reset {{
      background: #ffffff;
      color: #64748b;
      border-color: #cbd5e1;
    }}
    .btn-reset:hover {{ background: #f1f5f9; color: #0f172a; }}
    
    .main-layout {{
      display: grid;
      grid-template-columns: 0.95fr 1.05fr;
      gap: 20px;
    }}
    .panel {{
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 24px;
      box-shadow: var(--shadow);
      display: flex;
      flex-direction: column;
    }}
    .panel h2 {{
      margin: 0 0 4px;
      font-size: 20px;
      font-weight: 700;
      letter-spacing: -0.01em;
      color: var(--ink);
    }}
    .panel-subtitle {{
      margin: 0 0 16px;
      font-size: 13px;
      color: var(--muted);
    }}
    
    .verdict-card {{
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 16px;
      display: flex;
      align-items: center;
      gap: 14px;
      margin-bottom: 20px;
      transition: all 0.2s ease;
    }}
    .verdict-card.success {{
      background: #ecfdf5;
      border-color: #a7f3d0;
      color: #065f46;
    }}
    .verdict-card.success .verdict-icon {{
      color: var(--success);
    }}
    .verdict-card.success .verdict-text {{
      color: #065f46;
    }}
    .verdict-card.danger {{
      background: #fff1f2;
      border-color: #fecdd3;
      color: #9f1239;
    }}
    .verdict-card.danger .verdict-icon {{
      color: var(--danger);
    }}
    .verdict-card.danger .verdict-text {{
      color: #9f1239;
    }}
    .verdict-card.neutral {{
      background: #f8fafc;
      border-color: #e2e8f0;
      color: #334155;
    }}
    .verdict-card.neutral .verdict-icon {{
      color: #64748b;
    }}
    .verdict-card.neutral .verdict-text {{
      color: #334155;
    }}
    .verdict-icon {{
      width: 36px;
      height: 36px;
      flex-shrink: 0;
    }}
    .verdict-info {{
      display: flex;
      flex-direction: column;
    }}
    .verdict-label-tag {{
      font-size: 9px;
      font-weight: 600;
      color: var(--muted);
      letter-spacing: 0.05em;
      margin-bottom: 2px;
    }}
    .verdict-text {{
      font-size: 14px;
      font-weight: 700;
      line-height: 1.4;
    }}
    .status-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
    }}
    .status-item {{
      background: #f8fafc;
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      padding: 12px;
    }}
    .status-title {{
      display: block;
      font-size: 10px;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.05em;
      margin-bottom: 4px;
    }}
    .status-value {{
      display: block;
      font-size: 13px;
      font-weight: 600;
      color: var(--ink);
    }}
    .explorer-panel {{
      padding: 0;
      overflow: hidden;
    }}
    .explorer-header {{
      padding: 24px 24px 16px;
      border-bottom: 1px solid var(--border);
      display: flex;
      flex-direction: column;
      gap: 12px;
    }}
    .tab-buttons {{
      display: flex;
      background: #f1f5f9;
      padding: 3px;
      border-radius: 8px;
      width: fit-content;
      border: 1px solid #e2e8f0;
    }}
    .tab-btn {{
      background: transparent;
      border: none;
      color: #64748b;
      padding: 6px 14px;
      font-family: 'Outfit', sans-serif;
      font-size: 13px;
      font-weight: 600;
      border-radius: 6px;
      cursor: pointer;
      transition: all 0.15s ease;
    }}
    .tab-btn.active {{
      background: #ffffff;
      color: #0f172a;
      box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }}
    .tab-btn:hover:not(.active) {{
      color: #0f172a;
    }}
    .tab-content {{
      padding: 24px;
      display: none;
      flex-direction: column;
      flex-grow: 1;
    }}
    .tab-content.active {{
      display: flex;
      animation: fadeIn 0.2s ease-out;
    }}
    .tab-description {{
      margin: 0 0 14px;
      font-size: 13px;
      color: var(--muted);
      line-height: 1.5;
    }}
    pre {{
      margin: 0;
      overflow: auto;
      padding: 14px;
      border-radius: 8px;
      background: #f8fafc;
      border: 1px solid #e2e8f0;
      color: #0f172a;
      font-family: 'JetBrains Mono', monospace;
      font-size: 12px;
      line-height: 1.6;
      max-height: 380px;
      min-height: 140px;
    }}
    .empty {{
      padding: 20px;
      border-radius: 8px;
      border: 1px dashed var(--border);
      color: var(--muted);
      background: #f8fafc;
      font-size: 13px;
      text-align: center;
    }}
    .footer {{
      margin-top: 24px;
      color: var(--muted);
      font-size: 12px;
      text-align: center;
    }}
    .footer code {{
      background: #cbd5e1;
      padding: 2px 4px;
      border-radius: 4px;
      color: var(--accent);
      font-family: 'JetBrains Mono', monospace;
    }}
    @keyframes fadeIn {{
      from {{ opacity: 0; transform: translateY(2px); }}
      to {{ opacity: 1; transform: translateY(0); }}
    }}
    @keyframes slideDown {{
      from {{ opacity: 0; transform: translateY(-8px); }}
      to {{ opacity: 1; transform: translateY(0); }}
    }}
    @media (max-width: 980px) {{
      .header-panel {{ grid-template-columns: 1fr; }}
      .toolbar-grid {{ grid-template-columns: repeat(3, 1fr); }}
      .main-layout {{ grid-template-columns: 1fr; }}
    }}
    @media (max-width: 640px) {{
      .toolbar-grid {{ grid-template-columns: repeat(2, 1fr); }}
      .status-grid {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <main class="shell">
    <header class="header-panel">
      <div class="brand">
        <span class="badge-tag">Blockchain Integrity System</span>
        <h1>Smart Contract Control Room</h1>
        <p>A secure ETL data pipeline with on-chain cryptographic proofs and independent auditing.</p>
      </div>
      <div class="quick-stats">
        <div class="stat-card">
          <span class="stat-title">Smart Contract</span>
          <strong class="stat-value text-accent" title="{html.escape(contract_address)}">{html.escape(contract_address if len(contract_address) < 22 else contract_address[:18] + '...')}</strong>
        </div>
        <div class="stat-card">
          <span class="stat-title">Warehouse Size</span>
          <strong class="stat-value">{record_count} Records</strong>
        </div>
        <div class="stat-card">
          <span class="stat-title">Stored Proof</span>
          <strong class="stat-value text-accent2">{html.escape(proof['dataset_hash'][:14] + '...' if proof else 'No Proof')}</strong>
        </div>
        <div class="stat-card">
          <span class="stat-title">Ledger Height</span>
          <strong class="stat-value">Block #{html.escape(str(latest_block['block_number']) if latest_block else '0')}</strong>
        </div>
      </div>
    </header>

    {banner}

    <section class="toolbar-panel">
      <span class="panel-section-title">CONTROL OPERATIONS</span>
      <div class="toolbar-grid">
        <form method="post" action="/action"><input type="hidden" name="action" value="deploy"><button class="btn btn-deploy">Deploy Contract</button></form>
        <form method="post" action="/action"><input type="hidden" name="action" value="run_pipeline"><button class="btn btn-run">Run Pipeline</button></form>
        <form method="post" action="/action"><input type="hidden" name="action" value="store_proof"><button class="btn btn-proof">Store Proof</button></form>
        <form method="post" action="/action"><input type="hidden" name="action" value="audit"><button class="btn btn-audit">Verify Audit</button></form>
        <form method="post" action="/action"><input type="hidden" name="action" value="tamper"><button class="btn btn-tamper">Simulate Tamper</button></form>
        <form method="post" action="/action"><input type="hidden" name="action" value="reset"><button class="btn btn-reset">Reset Demo</button></form>
      </div>
    </section>

    <section class="main-layout">
      <!-- Left Column: Audit Verdict & Network Status -->
      <div class="column-left">
        <div class="panel verdict-panel {audit_class}">
          <h2>Verification Verdict</h2>
          <p class="panel-subtitle">On-chain integrity verification status</p>
          
          <div class="verdict-card {audit_class}">
            <div class="verdict-icon">
              {svg_icon}
            </div>
            <div class="verdict-info">
              <span class="verdict-label-tag">AUDIT MESSAGE</span>
              <strong class="verdict-text">{html.escape(audit_label)}</strong>
            </div>
          </div>

          <div class="status-grid">
            <div class="status-item">
              <span class="status-title">Ledger State</span>
              <strong class="status-value">{'Connected & Healthy' if settings.ledger_path.exists() else 'Not initialized'}</strong>
            </div>
            <div class="status-item">
              <span class="status-title">Solidity Compilation</span>
              <strong class="status-value">{'Compiled & Ready' if artifact else 'Missing'}</strong>
            </div>
            <div class="status-item">
              <span class="status-title">Registered Proofs</span>
              <strong class="status-value">{len(proofs)} active proof(s)</strong>
            </div>
            <div class="status-item">
              <span class="status-title">Mined Blocks</span>
              <strong class="status-value">{len(ledger.get('blocks', [])) if isinstance(ledger, dict) else 0} blocks</strong>
            </div>
          </div>
        </div>
      </div>

      <!-- Right Column: Data Explorer with Modern Tabs -->
      <div class="column-right">
        <div class="panel explorer-panel">
          <div class="explorer-header">
            <h2>Data Explorer</h2>
            <div class="tab-buttons">
              <button class="tab-btn active" onclick="switchTab('tab-warehouse')">Warehouse</button>
              <button class="tab-btn" onclick="switchTab('tab-ledger')">Ledger & Proofs</button>
              <button class="tab-btn" onclick="switchTab('tab-contract')">Smart Contract</button>
            </div>
          </div>

          <!-- Tab Content: Warehouse Payload -->
          <div id="tab-warehouse" class="tab-content active">
            <p class="tab-description">The local structured database representing data generated and sanitized by ETL pipeline.</p>
            {render_json_block(warehouse, "Warehouse payload not created yet. Run the pipeline to write files.")}
          </div>

          <!-- Tab Content: Ledger & Proofs -->
          <div id="tab-ledger" class="tab-content">
            <p class="tab-description">The latest block state mined on the local immutable ledger, alongside registered proofs.</p>
            <div class="ledger-subgrid">
              <div class="subblock">
                <h3>Latest Mined Block</h3>
                {render_json_block(latest_block, "No blocks mined yet. Submit a proof to trigger mining.")}
              </div>
              <div class="subblock" style="margin-top: 16px;">
                <h3>Active Proof State (On-chain)</h3>
                {render_json_block(contract_state, "No on-chain contract state generated yet.")}
              </div>
            </div>
          </div>

          <!-- Tab Content: Smart Contract Info -->
          <div id="tab-contract" class="tab-content">
            <p class="tab-description">Metadata of the deployed Smart Contract, bytecode fingerprint, and full compilation details.</p>
            <div class="ledger-subgrid">
              <div class="subblock">
                <h3>Solidity Deployment Artifact</h3>
                {render_json_block(deployment, "Contract not deployed yet.")}
              </div>
              <div class="subblock" style="margin-top: 16px;">
                <h3>ABI & Bytecode Specs</h3>
                {render_json_block(artifact, "Solidity compilation artifact missing. Build or deploy to compile.")}
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <div class="footer">Start the dashboard with <code>python3 ui/server.py</code> then open <code>http://127.0.0.1:8000</code>.</div>
  </main>

  <script>
    function switchTab(tabId) {{
      document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
      document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
      document.getElementById(tabId).classList.add('active');
      event.currentTarget.classList.add('active');
    }}
  </script>
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
    import sys
    host = "127.0.0.1"
    port = 8000
    
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print(f"Invalid port: {sys.argv[1]}. Using default.")

    max_attempts = 10
    for attempt in range(max_attempts):
        try:
            with make_server(host, port, application) as server:
                print(f"Dashboard running at http://{host}:{port}")
                server.serve_forever()
                break
        except OSError as e:
            if e.errno in (48, 98):
                print(f"Port {port} is busy. Trying next port {port + 1}...")
                port += 1
            else:
                raise e
    else:
        print(f"Could not bind to any port after {max_attempts} attempts.")


if __name__ == "__main__":
    main()
