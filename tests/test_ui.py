from __future__ import annotations

import io
import tempfile
import unittest
from pathlib import Path

from infrastructure.settings import Settings
from ui.server import application, perform_action


class DashboardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp(prefix="bdp-ui-"))
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

    def test_dashboard_actions_and_api(self) -> None:
        feedback = perform_action(self.settings, "run_pipeline")
        self.assertEqual(feedback.level, "success")
        audit_feedback = perform_action(self.settings, "audit")
        self.assertEqual(audit_feedback.level, "success")
        tamper_feedback = perform_action(self.settings, "tamper")
        self.assertEqual(tamper_feedback.level, "danger")

    def test_wsgi_api_state_endpoint(self) -> None:
        environ = {
            "REQUEST_METHOD": "GET",
            "PATH_INFO": "/api/state",
            "QUERY_STRING": "",
            "wsgi.input": io.BytesIO(b""),
        }
        status_headers: list[tuple[str, list[tuple[str, str]]]] = []

        def start_response(status: str, headers: list[tuple[str, str]]) -> None:
            status_headers.append((status, headers))

        body = b"".join(application(environ, start_response))
        self.assertIn('"deployment"', body.decode("utf-8"))
        self.assertEqual(status_headers[0][0], "200 OK")

    def test_wsgi_dashboard_endpoint(self) -> None:
        environ = {
            "REQUEST_METHOD": "GET",
            "PATH_INFO": "/",
            "QUERY_STRING": "",
            "wsgi.input": io.BytesIO(b""),
        }
        statuses: list[str] = []

        def start_response(status: str, headers: list[tuple[str, str]]) -> None:
            statuses.append(status)

        body = b"".join(application(environ, start_response)).decode("utf-8")
        self.assertIn("Smart Contract Control Room", body)
        self.assertEqual(statuses[0], "200 OK")


if __name__ == "__main__":
    unittest.main()
