from odoo import api, fields, models


class WexDeviceTestSession(models.Model):
    _name = "wex.device.test.session"
    _description = "Wex Device Test Session"
    _order = "last_ping_at desc, id desc"
    _sql_constraints = [
        (
            "device_company_uniq",
            "unique(device_uuid, company_id)",
            "A device session already exists for this company.",
        )
    ]

    name = fields.Char(required=True, readonly=True)
    device_uuid = fields.Char(required=True, index=True, readonly=True)
    manufacturer = fields.Char()
    model = fields.Char()
    android_version = fields.Char()
    sdk_int = fields.Integer()
    app_version = fields.Char()
    first_ping_at = fields.Datetime(readonly=True)
    last_ping_at = fields.Datetime(readonly=True)
    last_diagnostic_at = fields.Datetime(readonly=True)
    last_test_at = fields.Datetime(readonly=True)
    ping_count = fields.Integer(default=0, readonly=True)
    last_seen_ip = fields.Char(readonly=True)
    last_user_agent = fields.Char(readonly=True)
    last_battery_level = fields.Integer(readonly=True)
    last_network_type = fields.Char(readonly=True)
    last_storage_free_mb = fields.Integer(readonly=True)
    last_storage_total_mb = fields.Integer(readonly=True)
    last_battery_temperature_c = fields.Float(readonly=True)
    last_thermal_status = fields.Char(readonly=True)
    last_status = fields.Selection(
        selection=[
            ("ok", "OK"),
            ("error", "Error"),
        ],
        default="error",
        readonly=True,
    )
    last_message = fields.Text(readonly=True)
    active = fields.Boolean(default=True)
    run_ids = fields.One2many("wex.device.test.run", "session_id", readonly=True)
    log_ids = fields.One2many("wex.device.test.log", "session_id", readonly=True)
    result_ids = fields.One2many("wex.device.test.result", "session_id", readonly=True)
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )

    def _prepare_session_name(self, manufacturer, model, device_uuid):
        parts = [part for part in [manufacturer, model] if part]
        if parts:
            return "Android - %s" % " ".join(parts)
        return "Android - %s" % device_uuid

    def _prepare_session_values(self, payload, message, ping_at):
        manufacturer = (payload.get("manufacturer") or "").strip()
        model = (payload.get("model") or "").strip()
        return {
            "name": self._prepare_session_name(manufacturer, model, payload["device_uuid"].strip()),
            "device_uuid": payload["device_uuid"].strip(),
            "manufacturer": manufacturer,
            "model": model,
            "android_version": (payload.get("android_version") or "").strip(),
            "sdk_int": payload["sdk_int"],
            "app_version": (payload.get("app_version") or "").strip(),
            "last_ping_at": ping_at,
            "last_status": "ok",
            "last_message": message,
        }

    def _get_session_domain(self, device_uuid, company):
        return [
            ("device_uuid", "=", device_uuid.strip()),
            ("company_id", "=", company.id),
        ]

    def _prepare_session_response_payload(self):
        self.ensure_one()
        return {
            "id": self.id,
            "device_uuid": self.device_uuid,
            "status": self.last_status,
            "ping_count": self.ping_count,
            "last_ping_at": fields.Datetime.to_string(self.last_ping_at),
        }

    def _get_request_metadata_values(self, request_metadata=None):
        request_metadata = request_metadata or {}
        values = {}
        client_ip = (request_metadata.get("client_ip") or "").strip()
        user_agent = (request_metadata.get("user_agent") or "").strip()
        if client_ip:
            values["last_seen_ip"] = client_ip
        if user_agent:
            values["last_user_agent"] = user_agent[:512]
        return values

    def _build_ping_write_values(self, payload, message, ping_at, session=None, request_metadata=None):
        values = self._prepare_session_values(payload, message, ping_at)
        values.update(self._get_request_metadata_values(request_metadata=request_metadata))
        if session:
            values["ping_count"] = session.ping_count + 1
            if not session.first_ping_at:
                values["first_ping_at"] = ping_at
            return values

        values["first_ping_at"] = ping_at
        values["ping_count"] = 1
        return values

    def _prepare_diagnostic_summary_values(self, payload, message, diagnostic_at):
        diagnostic = payload["diagnostic"]
        values = {
            "last_diagnostic_at": diagnostic_at,
            "last_message": message,
            "last_status": "ok",
        }
        if diagnostic.get("battery_level") is not None:
            values["last_battery_level"] = diagnostic["battery_level"]
        if diagnostic.get("network_type"):
            values["last_network_type"] = diagnostic["network_type"].strip()
        if diagnostic.get("storage_free_mb") is not None:
            values["last_storage_free_mb"] = diagnostic["storage_free_mb"]
        if diagnostic.get("storage_total_mb") is not None:
            values["last_storage_total_mb"] = diagnostic["storage_total_mb"]
        return values

    def _build_diagnostic_write_values(self, payload, message, diagnostic_at, request_metadata=None):
        values = self._prepare_diagnostic_summary_values(payload, message, diagnostic_at)
        values.update(self._get_request_metadata_values(request_metadata=request_metadata))
        return values

    def _prepare_result_summary_values(self, payload, message, result_at):
        result_payload = payload["result"]
        measurements = result_payload.get("measurements") or {}
        values = {
            "last_test_at": result_at,
            "last_message": message,
            "last_status": "ok" if result_payload["status"] != "error" else "error",
        }
        if result_payload["test_type"] == "thermal_info":
            battery_temperature_c = measurements.get("battery_temperature_c")
            thermal_status = measurements.get("thermal_status")
            if battery_temperature_c is not None:
                values["last_battery_temperature_c"] = battery_temperature_c
            if isinstance(thermal_status, str) and thermal_status.strip():
                values["last_thermal_status"] = thermal_status.strip()
        return values

    def _build_result_write_values(self, payload, message, result_at, request_metadata=None):
        values = self._prepare_result_summary_values(payload, message, result_at)
        values.update(self._get_request_metadata_values(request_metadata=request_metadata))
        return values

    @api.model
    def _find_session_from_payload(self, payload, company):
        device_uuid = payload["device_uuid"].strip()
        return self.search(self._get_session_domain(device_uuid, company), limit=1)

    @api.model
    def find_or_create_from_payload(self, payload, company, message, request_metadata=None):
        session = self._find_session_from_payload(payload, company)
        if session:
            values = self._prepare_session_values(payload, message, fields.Datetime.now())
            values.update(self._get_request_metadata_values(request_metadata=request_metadata))
            session.write(values)
            return session
        return self.create_or_update_from_ping(
            payload,
            company,
            message,
            request_metadata=request_metadata,
        )

    @api.model
    def create_or_update_from_ping(self, payload, company, message, request_metadata=None):
        ping_at = fields.Datetime.now()
        device_uuid = payload["device_uuid"].strip()
        session = self.search(self._get_session_domain(device_uuid, company), limit=1)
        values = self._build_ping_write_values(
            payload,
            message,
            ping_at,
            session=session,
            request_metadata=request_metadata,
        )
        values["company_id"] = company.id
        if session:
            session.write(values)
            return session
        return self.create(values)

    @api.model
    def update_from_diagnostic(self, payload, company, message, request_metadata=None):
        diagnostic_at = fields.Datetime.now()
        session = self._find_session_from_payload(payload, company)
        if not session:
            session = self.create_or_update_from_ping(
                payload,
                company,
                message,
                request_metadata=request_metadata,
            )
        values = self._build_diagnostic_write_values(
            payload,
            message,
            diagnostic_at,
            request_metadata=request_metadata,
        )
        session.write(values)
        return session

    @api.model
    def update_from_result(self, payload, company, message, request_metadata=None):
        result_at = fields.Datetime.now()
        session = self._find_session_from_payload(payload, company)
        if not session:
            session = self.create_or_update_from_ping(
                payload,
                company,
                message,
                request_metadata=request_metadata,
            )
        values = self._build_result_write_values(
            payload,
            message,
            result_at,
            request_metadata=request_metadata,
        )
        session.write(values)
        return session, result_at
