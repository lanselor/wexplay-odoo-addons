# -*- coding: utf-8 -*-

import json

from odoo.tests import HttpCase, tagged


@tagged("post_install", "-at_install")
class TestWexDeviceTestHttp(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["ir.config_parameter"].sudo().set_param(
            "wex_device_test.api_token",
            "wex-device-test-http-token",
        )
        cls.authenticate(None, None)
        cls.partner = cls.env["res.partner"].create({"name": "HTTP Device Test Partner"})
        cls.product = cls.env["product.product"].create({"name": "HTTP Device Test Product"})
        cls.repair_order = cls.env["repair.order"].create(
            {
                "partner_id": cls.partner.id,
                "product_id": cls.product.id,
                "company_id": cls.env.company.id,
            }
        )
        cls.payload = {
            "device_uuid": "http-device-uuid-001",
            "manufacturer": "Samsung",
            "model": "SM-S948B",
            "android_version": "16",
            "sdk_int": 36,
            "app_version": "1.0.0",
        }
    def _create_run(self):
        return self.env["wex.device.test.run"].create(
            {
                "repair_order_id": self.repair_order.id,
                "company_id": self.env.company.id,
                "user_id": self.env.user.id,
            }
        )

    def _post_ping(self, payload=None, token=None, raw_body=None):
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = "Bearer %s" % token

        body = raw_body
        if body is None:
            body = json.dumps(payload or self.payload).encode()

        return self.url_open(
            "/wex/device-test/session/ping",
            data=body,
            headers=headers,
        )

    def _post_diagnostic(self, payload=None, token=None):
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = "Bearer %s" % token

        return self.url_open(
            "/wex/device-test/session/diagnostic",
            data=json.dumps(payload).encode(),
            headers=headers,
        )

    def _post_result(self, payload=None, token=None):
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = "Bearer %s" % token

        return self.url_open(
            "/wex/device-test/session/result",
            data=json.dumps(payload).encode(),
            headers=headers,
        )

    def _post_pair(self, payload=None, token=None):
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = "Bearer %s" % token

        return self.url_open(
            "/wex/device-test/run/pair",
            data=json.dumps(payload).encode(),
            headers=headers,
        )

    def test_ping_requires_bearer_token(self):
        response = self._post_ping(token=None)

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["code"], "missing_bearer_token")

    def test_ping_rejects_invalid_token(self):
        response = self._post_ping(token="wrong-token")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "invalid_api_token")

    def test_ping_rejects_invalid_payload(self):
        self._post_ping(token="wex-device-test-http-token")
        response = self._post_ping(
            payload={
                "device_uuid": self.payload["device_uuid"],
                "manufacturer": "Samsung",
                "model": "SM-S948B",
                "android_version": "16",
                "sdk_int": 36,
            },
            token="wex-device-test-http-token",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "invalid_payload")
        session = self.env["wex.device.test.session"].search(
            [("device_uuid", "=", self.payload["device_uuid"])],
            limit=1,
        )
        log_types = self.env["wex.device.test.log"].search(
            [("session_id", "=", session.id)]
        ).mapped("event_type")
        self.assertIn("ping_error", log_types)

    def test_ping_creates_or_updates_session(self):
        response = self._post_ping(token="wex-device-test-http-token")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["code"], "ping_recorded")
        self.assertTrue(payload["session_id"])
        self.assertEqual(payload["session"]["device_uuid"], self.payload["device_uuid"])

    def test_pair_links_run_and_session(self):
        run = self._create_run()
        response = self._post_pair(
            payload={
                **self.payload,
                "pairing_token": run.pairing_token,
                "pairing_code": run.pairing_code,
            },
            token="wex-device-test-http-token",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["code"], "run_paired")
        self.assertEqual(payload["run_id"], run.id)
        self.assertEqual(payload["run"]["state"], "paired")

        run.invalidate_recordset()
        self.assertEqual(run.state, "paired")
        self.assertTrue(run.session_id)

    def test_diagnostic_requires_valid_payload(self):
        response = self._post_diagnostic(
            payload={**self.payload, "diagnostic": "invalid"},
            token="wex-device-test-http-token",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "invalid_diagnostic_payload")

    def test_diagnostic_records_summary_and_logs(self):
        response = self._post_diagnostic(
            payload={
                **self.payload,
                "diagnostic": {
                    "battery_level": 58,
                    "network_type": "wifi",
                    "storage_free_mb": 24512,
                    "storage_total_mb": 512000,
                    "warnings": [
                        {
                            "message": "Battery saver active",
                            "technical_details": "System power saving mode is enabled.",
                        }
                    ],
                },
            },
            token="wex-device-test-http-token",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["code"], "diagnostic_recorded")
        self.assertEqual(payload["session"]["battery_level"], 58)
        self.assertEqual(payload["session"]["network_type"], "wifi")

        session = self.env["wex.device.test.session"].search(
            [("device_uuid", "=", self.payload["device_uuid"])],
            limit=1,
        )
        self.assertTrue(session.last_diagnostic_at)

        log_types = self.env["wex.device.test.log"].search(
            [("session_id", "=", session.id)]
        ).mapped("event_type")
        self.assertIn("diagnostic_submitted", log_types)
        self.assertIn("diagnostic_success", log_types)
        self.assertIn("client_warning", log_types)

    def test_result_requires_valid_payload(self):
        response = self._post_result(
            payload={
                **self.payload,
                "result": {
                    "test_type": "speaker",
                    "status": "detected",
                    "message": "Invalid audio status.",
                },
            },
            token="wex-device-test-http-token",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "invalid_result_payload")

    def test_result_records_audio_test(self):
        run = self._create_run()
        self._post_pair(
            payload={
                **self.payload,
                "pairing_token": run.pairing_token,
                "pairing_code": run.pairing_code,
            },
            token="wex-device-test-http-token",
        )
        response = self._post_result(
            payload={
                **self.payload,
                "run_id": run.id,
                "pairing_token": run.pairing_token,
                "result": {
                    "test_type": "speaker",
                    "status": "confirmed_ok",
                    "message": "Speaker test confirmed by user.",
                    "technical_details": "Audio tone played and confirmed.",
                    "measurements": {
                        "channel": "speaker",
                        "volume": 80,
                    },
                },
            },
            token="wex-device-test-http-token",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["code"], "test_result_recorded")
        self.assertEqual(payload["run_id"], run.id)
        self.assertEqual(payload["result"]["test_type"], "speaker")
        self.assertEqual(payload["result"]["status"], "confirmed_ok")

        session = self.env["wex.device.test.session"].search(
            [("device_uuid", "=", self.payload["device_uuid"])],
            limit=1,
        )
        self.assertTrue(session.last_test_at)

        result = self.env["wex.device.test.result"].search(
            [("session_id", "=", session.id), ("test_type", "=", "speaker")],
            limit=1,
        )
        self.assertTrue(result)
        self.assertEqual(result.run_id, run)
        self.assertEqual(result.status, "confirmed_ok")

        log_types = self.env["wex.device.test.log"].search(
            [("session_id", "=", session.id)]
        ).mapped("event_type")
        self.assertIn("result_submitted", log_types)
        self.assertIn("result_success", log_types)

    def test_result_records_thermal_info_summary(self):
        run = self._create_run()
        self._post_pair(
            payload={
                **self.payload,
                "pairing_token": run.pairing_token,
                "pairing_code": run.pairing_code,
            },
            token="wex-device-test-http-token",
        )
        response = self._post_result(
            payload={
                **self.payload,
                "run_id": run.id,
                "pairing_token": run.pairing_token,
                "result": {
                    "test_type": "thermal_info",
                    "status": "available",
                    "message": "Thermal information collected.",
                    "measurements": {
                        "battery_temperature_c": 34.5,
                        "thermal_status": "moderate",
                    },
                },
            },
            token="wex-device-test-http-token",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["code"], "test_result_recorded")
        self.assertEqual(payload["session"]["last_battery_temperature_c"], 34.5)
        self.assertEqual(payload["session"]["last_thermal_status"], "moderate")
