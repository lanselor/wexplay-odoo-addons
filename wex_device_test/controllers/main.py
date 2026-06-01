import json

from odoo import fields, http
from odoo.http import request
from odoo.exceptions import ValidationError


class WexDeviceTestController(http.Controller):
    AUDIO_TEST_TYPES = {"speaker", "earpiece"}
    SENSOR_TEST_TYPES = {"proximity", "accelerometer", "gyroscope"}
    RESULT_TEST_TYPES = AUDIO_TEST_TYPES | SENSOR_TEST_TYPES | {"thermal_info"}
    AUDIO_RESULT_STATUSES = {"pending", "played", "confirmed_ok", "confirmed_fail", "error"}
    SENSOR_RESULT_STATUSES = {"available", "not_available", "detected", "not_detected", "error"}
    THERMAL_RESULT_STATUSES = {"available", "not_available", "error"}

    def _get_session_model(self):
        return request.env["wex.device.test.session"].sudo().with_company(request.env.company)

    def _get_log_model(self):
        return request.env["wex.device.test.log"].sudo().with_company(request.env.company)

    def _get_result_model(self):
        return request.env["wex.device.test.result"].sudo().with_company(request.env.company)

    def _get_run_model(self):
        return request.env["wex.device.test.run"].sudo().with_company(request.env.company)

    def _get_server_time(self):
        return fields.Datetime.to_string(fields.Datetime.now())

    def _json_response(self, payload, status=200, headers=None):
        response_headers = [("Content-Type", "application/json")]
        if headers:
            response_headers.extend(headers)
        return request.make_response(
            json.dumps(payload),
            headers=response_headers,
            status=status,
        )

    def _build_error_payload(self, code, message):
        return {
            "ok": False,
            "code": code,
            "message": message,
            "server_time": self._get_server_time(),
        }

    def _error_response(self, status, code, message, headers=None):
        return self._json_response(self._build_error_payload(code, message), status=status, headers=headers)

    def _prepare_run_response_payload(self, run):
        if not run:
            return False
        return run._prepare_run_response_payload()

    def _success_response(self, session, message, run=None):
        payload = {
            "ok": True,
            "code": "ping_recorded",
            "message": message,
            "session_id": session.id,
            "server_time": self._get_server_time(),
            "session": session._prepare_session_response_payload(),
        }
        if run:
            payload["run_id"] = run.id
            payload["run"] = {
                "id": run.id,
                "state": run.state,
            }
        return self._json_response(payload)

    def _diagnostic_success_response(self, session, message, run=None):
        payload = {
            "ok": True,
            "code": "diagnostic_recorded",
            "message": message,
            "session_id": session.id,
            "server_time": self._get_server_time(),
            "session": {
                "id": session.id,
                "device_uuid": session.device_uuid,
                "status": session.last_status,
                "last_diagnostic_at": fields.Datetime.to_string(session.last_diagnostic_at),
                "battery_level": session.last_battery_level,
                "network_type": session.last_network_type,
                "storage_free_mb": session.last_storage_free_mb,
                "storage_total_mb": session.last_storage_total_mb,
            },
        }
        if run:
            payload["run_id"] = run.id
            payload["run"] = {
                "id": run.id,
                "state": run.state,
            }
        return self._json_response(payload)

    def _result_success_response(self, session, result_record, message, run=None):
        payload = {
            "ok": True,
            "code": "test_result_recorded",
            "message": message,
            "session_id": session.id,
            "server_time": self._get_server_time(),
            "result": {
                "id": result_record.id,
                "test_type": result_record.test_type,
                "status": result_record.status,
                "executed_at": fields.Datetime.to_string(result_record.executed_at),
            },
            "session": {
                "id": session.id,
                "device_uuid": session.device_uuid,
                "status": session.last_status,
                "last_test_at": fields.Datetime.to_string(session.last_test_at),
                "last_battery_temperature_c": session.last_battery_temperature_c,
                "last_thermal_status": session.last_thermal_status,
            },
        }
        if run:
            payload["run_id"] = run.id
            payload["run"] = {
                "id": run.id,
                "state": run.state,
            }
        return self._json_response(payload)

    def _pair_success_response(self, run, session, message):
        return self._json_response(
            {
                "ok": True,
                "code": "run_paired",
                "message": message,
                "session_id": session.id,
                "run_id": run.id,
                "server_time": self._get_server_time(),
                "pairing": {
                    "status": run.state,
                    "token_mode": "pairing_token",
                    "code_mode": "pairing_code",
                },
                "run": self._prepare_run_response_payload(run),
                "session": session._prepare_session_response_payload(),
            }
        )

    def _get_bearer_token(self):
        authorization = request.httprequest.headers.get("Authorization", "")
        if not authorization.startswith("Bearer "):
            return False
        token = authorization[7:].strip()
        return token or False

    def _get_expected_token(self):
        return (
            request.env["ir.config_parameter"]
            .sudo()
            .get_param("wex_device_test.api_token", default="")
            .strip()
        )

    def _get_json_payload(self):
        raw_body = request.httprequest.get_data(as_text=True) or "{}"
        try:
            return json.loads(raw_body), False
        except json.JSONDecodeError:
            return False, "Invalid JSON payload."

    def _validate_bearer_token(self):
        token = self._get_bearer_token()
        if not token:
            return False, self._error_response(
                401,
                "missing_bearer_token",
                "Missing Bearer token.",
                headers=[("WWW-Authenticate", "Bearer")],
            )

        expected_token = self._get_expected_token()
        if not expected_token:
            return False, self._error_response(
                503,
                "token_not_configured",
                "Device test API token is not configured.",
            )
        if token != expected_token:
            return False, self._error_response(403, "invalid_api_token", "Invalid API token.")

        return token, False

    def _validate_payload(self, payload):
        if not isinstance(payload, dict):
            return "Invalid JSON payload."

        required_text_fields = [
            "device_uuid",
            "manufacturer",
            "model",
            "android_version",
            "app_version",
        ]
        for field_name in required_text_fields:
            value = payload.get(field_name)
            if not isinstance(value, str) or not value.strip():
                return "Field '%s' is required." % field_name

        sdk_int = payload.get("sdk_int")
        if not isinstance(sdk_int, int):
            return "Field 'sdk_int' must be an integer."
        if sdk_int < 1:
            return "Field 'sdk_int' must be greater than 0."

        return False

    def _validate_pair_payload(self, payload):
        payload_error = self._validate_payload(payload)
        if payload_error:
            return payload_error
        pairing_token = payload.get("pairing_token")
        pairing_code = payload.get("pairing_code")
        if isinstance(pairing_token, str) and pairing_token.strip():
            return False
        if isinstance(pairing_code, str) and pairing_code.strip():
            return False
        return "Field 'pairing_token' or 'pairing_code' is required."

    def _validate_diagnostic_payload(self, payload):
        payload_error = self._validate_payload(payload)
        if payload_error:
            return payload_error

        diagnostic = payload.get("diagnostic")
        if not isinstance(diagnostic, dict):
            return "Field 'diagnostic' must be an object."

        integer_fields = ["battery_level", "storage_free_mb", "storage_total_mb"]
        for field_name in integer_fields:
            value = diagnostic.get(field_name)
            if value is None:
                continue
            if not isinstance(value, int):
                return "Field '%s' must be an integer." % field_name
            if value < 0:
                return "Field '%s' must be greater than or equal to 0." % field_name

        battery_level = diagnostic.get("battery_level")
        if battery_level is not None and battery_level > 100:
            return "Field 'battery_level' must be less than or equal to 100."

        network_type = diagnostic.get("network_type")
        if network_type is not None and (not isinstance(network_type, str) or not network_type.strip()):
            return "Field 'network_type' must be a non-empty string."

        warnings = diagnostic.get("warnings")
        if warnings is not None and not isinstance(warnings, list):
            return "Field 'warnings' must be a list."

        return False

    def _get_allowed_result_statuses(self, test_type):
        if test_type in self.AUDIO_TEST_TYPES:
            return self.AUDIO_RESULT_STATUSES
        if test_type in self.SENSOR_TEST_TYPES:
            return self.SENSOR_RESULT_STATUSES
        if test_type == "thermal_info":
            return self.THERMAL_RESULT_STATUSES
        return set()

    def _validate_result_payload(self, payload):
        payload_error = self._validate_payload(payload)
        if payload_error:
            return payload_error

        result = payload.get("result")
        if not isinstance(result, dict):
            return "Field 'result' must be an object."

        test_type = result.get("test_type")
        if test_type not in self.RESULT_TEST_TYPES:
            return "Field 'test_type' is not supported."

        status = result.get("status")
        allowed_statuses = self._get_allowed_result_statuses(test_type)
        if status not in allowed_statuses:
            return "Field 'status' is not valid for test type '%s'." % test_type

        message = result.get("message")
        if not isinstance(message, str) or not message.strip():
            return "Field 'message' is required inside 'result'."

        technical_details = result.get("technical_details")
        if technical_details is not None and not isinstance(technical_details, str):
            return "Field 'technical_details' must be a string."

        measurements = result.get("measurements")
        if measurements is not None and not isinstance(measurements, dict):
            return "Field 'measurements' must be an object."

        if test_type == "thermal_info" and isinstance(measurements, dict):
            battery_temperature_c = measurements.get("battery_temperature_c")
            if battery_temperature_c is not None and not isinstance(
                battery_temperature_c, (int, float)
            ):
                return "Field 'battery_temperature_c' must be numeric."

            thermal_status = measurements.get("thermal_status")
            if thermal_status is not None and (
                not isinstance(thermal_status, str) or not thermal_status.strip()
            ):
                return "Field 'thermal_status' must be a non-empty string."

        return False

    def _get_client_ip(self):
        forwarded_for = request.httprequest.headers.get("X-Forwarded-For", "")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        return request.httprequest.remote_addr or ""

    def _prepare_request_metadata(self):
        return {
            "client_ip": self._get_client_ip(),
            "user_agent": request.httprequest.user_agent.string or "",
        }

    def _prepare_ping_context(self):
        return {
            "company": request.env.company,
            "message": "Conexión correcta",
            "request_metadata": self._prepare_request_metadata(),
        }

    def _prepare_diagnostic_context(self):
        return {
            "company": request.env.company,
            "message": "Diagnóstico recibido correctamente",
            "request_metadata": self._prepare_request_metadata(),
        }

    def _prepare_result_context(self, payload):
        test_type = payload["result"]["test_type"]
        result_messages = {
            "speaker": "Resultado de altavoz recibido correctamente",
            "earpiece": "Resultado de auricular recibido correctamente",
            "proximity": "Resultado de proximidad recibido correctamente",
            "accelerometer": "Resultado de acelerómetro recibido correctamente",
            "gyroscope": "Resultado de giroscopio recibido correctamente",
            "thermal_info": "Información térmica recibida correctamente",
        }
        return {
            "company": request.env.company,
            "message": result_messages[test_type],
            "request_metadata": self._prepare_request_metadata(),
        }

    def _prepare_pairing_context(self):
        return {
            "company": request.env.company,
            "message": "Run paired successfully.",
            "request_metadata": self._prepare_request_metadata(),
        }

    def _get_session_for_payload(self, payload):
        if not isinstance(payload, dict):
            return request.env["wex.device.test.session"]
        device_uuid = payload.get("device_uuid")
        if not isinstance(device_uuid, str) or not device_uuid.strip():
            return request.env["wex.device.test.session"]
        return self._get_session_model().search(
            [
                ("device_uuid", "=", device_uuid.strip()),
                ("company_id", "=", request.env.company.id),
            ],
            limit=1,
        )

    def _get_run_context_values(self, payload):
        if not isinstance(payload, dict):
            return {}
        values = {}
        run_id = payload.get("run_id")
        if isinstance(run_id, int) and run_id > 0:
            values["run_id"] = run_id
        pairing_token = payload.get("pairing_token")
        if isinstance(pairing_token, str) and pairing_token.strip():
            values["pairing_token"] = pairing_token.strip()
        pairing_code = payload.get("pairing_code")
        if isinstance(pairing_code, str) and pairing_code.strip():
            values["pairing_code"] = pairing_code.strip().upper()
        return values

    def _get_run_for_payload(self, payload, required=False):
        run_context = self._get_run_context_values(payload)
        if not run_context:
            if required:
                return False, self._error_response(
                    400,
                    "missing_run_context",
                    "Field 'run_id' or 'pairing_token' is required.",
                )
            return False, False
        run = self._get_run_model().find_pairable_run(
            pairing_token=run_context.get("pairing_token"),
            pairing_code=run_context.get("pairing_code"),
            run_id=run_context.get("run_id"),
            company=request.env.company,
        )
        if not run:
            return False, self._error_response(
                404,
                "pairing_run_not_found",
                "No active run matches the provided pairing token.",
            )
        if run_context.get("pairing_token") and not run._check_pairing_token(run_context["pairing_token"]):
            return False, self._error_response(
                403,
                "invalid_pairing_token",
                "Invalid pairing token.",
            )
        if run_context.get("run_id") and run.id != run_context["run_id"]:
            return False, self._error_response(
                404,
                "pairing_run_not_found",
                "No active run matches the provided pairing token.",
            )
        return run, False

    def _check_run_accepts_operational_payload(self, run):
        if not run:
            return False
        if run._can_receive_results():
            return False
        return self._error_response(
            409,
            "run_not_ready",
            "This run is not ready to receive operational test data.",
        )

    def _log_request_event(self, session, event_type, status, message, payload=None, technical_details=None, run=None):
        return self._get_log_model().create_log(
            session,
            event_type,
            status,
            message,
            payload=payload,
            technical_details=technical_details,
            run=run,
        )

    def _log_payload_error(self, payload, event_type, message):
        session = self._get_session_for_payload(payload)
        run, _error = self._get_run_for_payload(payload, required=False)
        if not session:
            return False
        return self._log_request_event(
            session,
            event_type,
            "error",
            message,
            payload=payload,
            technical_details=message,
            run=run,
        )

    @http.route(
        "/wex/device-test/run/pair",
        type="http",
        auth="public",
        methods=["POST"],
        csrf=False,
        save_session=False,
    )
    def pair_run(self, **kwargs):
        _token, error_response = self._validate_bearer_token()
        if error_response:
            return error_response

        payload, payload_error = self._get_json_payload()
        if payload_error:
            return self._error_response(400, "invalid_json_payload", payload_error)

        validation_error = self._validate_pair_payload(payload)
        if validation_error:
            return self._error_response(400, "invalid_pair_payload", validation_error)

        pairing_context = self._prepare_pairing_context()
        run, run_error = self._get_run_for_payload(payload, required=True)
        if run_error:
            return run_error
        if not run._is_pairable():
            return self._error_response(
                409,
                "run_not_pairable",
                "This run is no longer available for pairing.",
            )

        session = self._get_session_model().find_or_create_from_payload(
            payload,
            pairing_context["company"],
            pairing_context["message"],
            request_metadata=pairing_context["request_metadata"],
        )
        try:
            run.pair_with_session(session, message=pairing_context["message"])
        except ValidationError as error:
            return self._error_response(409, "run_not_pairable", str(error))

        self._log_request_event(
            session,
            "ping_request",
            "ok",
            "Pairing payload accepted",
            payload=payload,
            run=run,
        )
        return self._pair_success_response(run, session, pairing_context["message"])

    @http.route(
        "/wex/device-test/session/ping",
        type="http",
        auth="public",
        methods=["POST"],
        csrf=False,
        save_session=False,
    )
    def ping_session(self, **kwargs):
        _token, error_response = self._validate_bearer_token()
        if error_response:
            return error_response

        payload, payload_error = self._get_json_payload()
        if payload_error:
            return self._error_response(400, "invalid_json_payload", payload_error)

        validation_error = self._validate_payload(payload)
        if validation_error:
            self._log_payload_error(payload, "ping_error", validation_error)
            return self._error_response(400, "invalid_payload", validation_error)

        ping_context = self._prepare_ping_context()
        run, run_error = self._get_run_for_payload(payload, required=False)
        if run_error:
            return run_error
        session = (
            self._get_session_model().create_or_update_from_ping(
                payload,
                ping_context["company"],
                ping_context["message"],
                request_metadata=ping_context["request_metadata"],
            )
        )
        self._log_request_event(
            session,
            "ping_request",
            "ok",
            "Ping payload accepted",
            payload=payload,
            run=run,
        )
        self._log_request_event(
            session,
            "ping_success",
            "ok",
            ping_context["message"],
            payload=payload,
            run=run,
        )
        return self._success_response(session, ping_context["message"], run=run)

    @http.route(
        "/wex/device-test/session/diagnostic",
        type="http",
        auth="public",
        methods=["POST"],
        csrf=False,
        save_session=False,
    )
    def submit_diagnostic(self, **kwargs):
        _token, error_response = self._validate_bearer_token()
        if error_response:
            return error_response

        payload, payload_error = self._get_json_payload()
        if payload_error:
            return self._error_response(400, "invalid_json_payload", payload_error)

        validation_error = self._validate_diagnostic_payload(payload)
        if validation_error:
            self._log_payload_error(payload, "diagnostic_error", validation_error)
            return self._error_response(400, "invalid_diagnostic_payload", validation_error)

        diagnostic_context = self._prepare_diagnostic_context()
        run, run_error = self._get_run_for_payload(payload, required=False)
        if run_error:
            return run_error
        run_state_error = self._check_run_accepts_operational_payload(run)
        if run_state_error:
            return run_state_error
        session = self._get_session_model().update_from_diagnostic(
            payload,
            diagnostic_context["company"],
            diagnostic_context["message"],
            request_metadata=diagnostic_context["request_metadata"],
        )
        self._log_request_event(
            session,
            "diagnostic_submitted",
            "ok",
            "Diagnostic payload accepted",
            payload=payload,
            run=run,
        )
        self._log_request_event(
            session,
            "diagnostic_success",
            "ok",
            diagnostic_context["message"],
            payload=payload.get("diagnostic"),
            run=run,
        )
        self._get_log_model().create_logs_from_client_warnings(
            session,
            payload.get("diagnostic", {}).get("warnings"),
            run=run,
        )
        return self._diagnostic_success_response(session, diagnostic_context["message"], run=run)

    @http.route(
        "/wex/device-test/session/result",
        type="http",
        auth="public",
        methods=["POST"],
        csrf=False,
        save_session=False,
    )
    def submit_result(self, **kwargs):
        _token, error_response = self._validate_bearer_token()
        if error_response:
            return error_response

        payload, payload_error = self._get_json_payload()
        if payload_error:
            return self._error_response(400, "invalid_json_payload", payload_error)

        validation_error = self._validate_result_payload(payload)
        if validation_error:
            self._log_payload_error(payload, "result_error", validation_error)
            return self._error_response(400, "invalid_result_payload", validation_error)

        result_context = self._prepare_result_context(payload)
        run, run_error = self._get_run_for_payload(payload, required=False)
        if run_error:
            return run_error
        run_state_error = self._check_run_accepts_operational_payload(run)
        if run_state_error:
            return run_state_error
        session, result_at = self._get_session_model().update_from_result(
            payload,
            result_context["company"],
            result_context["message"],
            request_metadata=result_context["request_metadata"],
        )
        result_payload = payload["result"]
        result_record = self._get_result_model().create_result(
            session,
            result_payload["test_type"],
            result_payload["status"],
            result_payload["message"].strip(),
            result_at,
            measurements=result_payload.get("measurements"),
            technical_details=(result_payload.get("technical_details") or "").strip() or False,
            run=run,
        )
        if run and run.state == "paired":
            run._mark_as_in_progress(message=result_context["message"])
        self._log_request_event(
            session,
            "result_submitted",
            "ok",
            "Test result payload accepted",
            payload=payload,
            run=run,
        )
        self._log_request_event(
            session,
            "result_success",
            "ok",
            result_context["message"],
            payload=result_payload,
            run=run,
        )
        return self._result_success_response(session, result_record, result_context["message"], run=run)
