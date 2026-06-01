import json

from odoo import api, fields, models


class WexDeviceTestLog(models.Model):
    _name = "wex.device.test.log"
    _description = "Wex Device Test Log"
    _order = "create_date desc, id desc"

    session_id = fields.Many2one(
        "wex.device.test.session",
        required=True,
        ondelete="cascade",
        index=True,
        readonly=True,
    )
    run_id = fields.Many2one(
        "wex.device.test.run",
        index=True,
        readonly=True,
        ondelete="set null",
    )
    event_type = fields.Selection(
        selection=[
            ("ping_request", "Ping Request"),
            ("ping_success", "Ping Success"),
            ("ping_error", "Ping Error"),
            ("diagnostic_submitted", "Diagnostic Submitted"),
            ("diagnostic_success", "Diagnostic Success"),
            ("diagnostic_error", "Diagnostic Error"),
            ("result_submitted", "Result Submitted"),
            ("result_success", "Result Success"),
            ("result_error", "Result Error"),
            ("client_warning", "Client Warning"),
        ],
        required=True,
        readonly=True,
    )
    status = fields.Selection(
        selection=[
            ("ok", "OK"),
            ("warning", "Warning"),
            ("error", "Error"),
        ],
        required=True,
        readonly=True,
    )
    message = fields.Char(required=True, readonly=True)
    technical_details = fields.Text(readonly=True)
    payload_json = fields.Text(readonly=True)
    company_id = fields.Many2one(
        "res.company",
        required=True,
        readonly=True,
        index=True,
    )

    @api.model
    def _prepare_payload_json(self, payload):
        if not payload:
            return False
        return json.dumps(payload, sort_keys=True, ensure_ascii=False, indent=2)

    @api.model
    def create_log(
        self,
        session,
        event_type,
        status,
        message,
        payload=None,
        technical_details=None,
        run=None,
    ):
        return self.create(
            {
                "session_id": session.id,
                "run_id": run.id if run else False,
                "event_type": event_type,
                "status": status,
                "message": message,
                "technical_details": technical_details,
                "payload_json": self._prepare_payload_json(payload),
                "company_id": session.company_id.id,
            }
        )

    @api.model
    def create_logs_from_client_warnings(self, session, warnings, run=None):
        warnings = warnings or []
        for warning in warnings:
            if not isinstance(warning, dict):
                continue
            message = (warning.get("message") or "").strip()
            if not message:
                continue
            self.create_log(
                session,
                "client_warning",
                "warning",
                message,
                payload=warning,
                technical_details=(warning.get("technical_details") or "").strip() or False,
                run=run,
            )
