# -*- coding: utf-8 -*-

import json

from odoo.fields import Datetime
from odoo.tests.common import TransactionCase


class TestWexDeviceTestSession(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.session_model = cls.env["wex.device.test.session"]
        cls.log_model = cls.env["wex.device.test.log"]
        cls.result_model = cls.env["wex.device.test.result"]
        cls.run_model = cls.env["wex.device.test.run"]
        cls.company_a = cls.env.company
        cls.company_b = cls.env["res.company"].create({"name": "Device Test Company B"})
        cls.partner = cls.env["res.partner"].create({"name": "Device Test Partner"})
        cls.product = cls.env["product.product"].create({"name": "Device Test Product"})
        cls.repair_order = cls.env["repair.order"].create(
            {
                "partner_id": cls.partner.id,
                "product_id": cls.product.id,
                "company_id": cls.company_a.id,
            }
        )
        cls.payload = {
            "device_uuid": "device-test-uuid-001",
            "manufacturer": "Samsung",
            "model": "SM-S948B",
            "android_version": "16",
            "sdk_int": 36,
            "app_version": "1.0.0",
        }

    def test_create_or_update_from_ping_updates_same_company_session(self):
        first_session = self.session_model.create_or_update_from_ping(
            self.payload,
            self.company_a,
            "Conexión correcta",
            request_metadata={
                "client_ip": "192.168.0.50",
                "user_agent": "AndroidApp/1.0.0",
            },
        )
        second_session = self.session_model.create_or_update_from_ping(
            self.payload,
            self.company_a,
            "Conexión correcta",
            request_metadata={
                "client_ip": "192.168.0.51",
                "user_agent": "AndroidApp/1.0.1",
            },
        )

        self.assertEqual(first_session, second_session)
        self.assertEqual(second_session.ping_count, 2)
        self.assertTrue(second_session.first_ping_at)
        self.assertTrue(second_session.last_ping_at)
        self.assertEqual(second_session.last_seen_ip, "192.168.0.51")
        self.assertEqual(second_session.last_user_agent, "AndroidApp/1.0.1")

    def test_create_or_update_from_ping_keeps_sessions_separated_by_company(self):
        session_a = self.session_model.create_or_update_from_ping(
            self.payload,
            self.company_a,
            "Conexión correcta",
        )
        session_b = self.session_model.create_or_update_from_ping(
            self.payload,
            self.company_b,
            "Conexión correcta",
        )

        self.assertNotEqual(session_a.id, session_b.id)
        self.assertEqual(session_a.company_id, self.company_a)
        self.assertEqual(session_b.company_id, self.company_b)

    def test_update_from_diagnostic_updates_last_diagnostic_summary(self):
        session = self.session_model.create_or_update_from_ping(
            self.payload,
            self.company_a,
            "Conexión correcta",
        )

        updated_session = self.session_model.update_from_diagnostic(
            {
                **self.payload,
                "diagnostic": {
                    "battery_level": 58,
                    "network_type": "wifi",
                    "storage_free_mb": 24512,
                    "storage_total_mb": 512000,
                },
            },
            self.company_a,
            "Diagnóstico recibido correctamente",
            request_metadata={"client_ip": "192.168.0.60"},
        )

        self.assertEqual(updated_session, session)
        self.assertTrue(updated_session.last_diagnostic_at)
        self.assertEqual(updated_session.last_battery_level, 58)
        self.assertEqual(updated_session.last_network_type, "wifi")
        self.assertEqual(updated_session.last_storage_free_mb, 24512)
        self.assertEqual(updated_session.last_storage_total_mb, 512000)
        self.assertEqual(updated_session.last_seen_ip, "192.168.0.60")

    def test_create_logs_from_client_warnings_creates_warning_entries(self):
        session = self.session_model.create_or_update_from_ping(
            self.payload,
            self.company_a,
            "Conexión correcta",
        )

        self.log_model.create_logs_from_client_warnings(
            session,
            [
                {
                    "message": "Battery saver active",
                    "technical_details": "System power saving mode is enabled.",
                }
            ],
        )

        warning_log = self.log_model.search(
            [("session_id", "=", session.id), ("event_type", "=", "client_warning")],
            limit=1,
        )
        self.assertTrue(warning_log)
        self.assertEqual(warning_log.status, "warning")
        self.assertEqual(warning_log.message, "Battery saver active")

    def test_update_from_result_updates_last_test_summary(self):
        session = self.session_model.create_or_update_from_ping(
            self.payload,
            self.company_a,
            "Conexión correcta",
        )

        updated_session, result_at = self.session_model.update_from_result(
            {
                **self.payload,
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
            self.company_a,
            "Información térmica recibida correctamente",
            request_metadata={"client_ip": "192.168.0.70"},
        )

        self.assertEqual(updated_session, session)
        self.assertEqual(updated_session.last_test_at, result_at)
        self.assertEqual(updated_session.last_battery_temperature_c, 34.5)
        self.assertEqual(updated_session.last_thermal_status, "moderate")
        self.assertEqual(updated_session.last_seen_ip, "192.168.0.70")

    def test_create_result_stores_measurements(self):
        session = self.session_model.create_or_update_from_ping(
            self.payload,
            self.company_a,
            "Conexión correcta",
        )
        run = self.run_model.create(
            {
                "repair_order_id": self.repair_order.id,
                "company_id": self.company_a.id,
                "user_id": self.env.user.id,
            }
        )
        run.pair_with_session(session)

        result = self.result_model.create_result(
            session,
            "speaker",
            "confirmed_ok",
            "Speaker test confirmed by user.",
            Datetime.now(),
            measurements={"channel": "speaker", "volume": 80},
            technical_details="Audio tone played and confirmed.",
            run=run,
        )

        self.assertEqual(result.session_id, session)
        self.assertEqual(result.run_id, run)
        self.assertEqual(result.test_type, "speaker")
        self.assertEqual(result.status, "confirmed_ok")
        self.assertIn('"channel": "speaker"', result.measurement_json)

    def test_pair_with_session_marks_run_as_paired(self):
        session = self.session_model.create_or_update_from_ping(
            self.payload,
            self.company_a,
            "Conexión correcta",
        )
        run = self.run_model.create(
            {
                "repair_order_id": self.repair_order.id,
                "company_id": self.company_a.id,
                "user_id": self.env.user.id,
            }
        )

        run.pair_with_session(session, message="Run paired successfully.")

        self.assertEqual(run.session_id, session)
        self.assertEqual(run.state, "paired")
        self.assertTrue(run.paired_at)

    def test_pairing_qr_payload_uses_device_test_public_base_url(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "wex_device_test.public_base_url",
            "http://192.168.0.101:8069",
        )
        run = self.run_model.create(
            {
                "repair_order_id": self.repair_order.id,
                "company_id": self.company_a.id,
                "user_id": self.env.user.id,
            }
        )

        payload = self.repair_order._get_device_test_pairing_payload(run)
        parsed_payload = json.loads(payload)

        self.assertEqual(parsed_payload["type"], "wex_device_test_pairing")
        self.assertEqual(parsed_payload["base_url"], "http://192.168.0.101:8069")
        self.assertEqual(parsed_payload["pairing_token"], run.pairing_token)
        self.assertEqual(parsed_payload["pairing_code"], run.pairing_code)
        self.assertEqual(parsed_payload["run_id"], run.id)

    def test_compute_device_test_qr_fields_builds_download_and_pairing_qr(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "wex_device_test.public_base_url",
            "http://192.168.0.101:8069",
        )
        run = self.run_model.create(
            {
                "repair_order_id": self.repair_order.id,
                "company_id": self.company_a.id,
                "user_id": self.env.user.id,
            }
        )

        self.repair_order.invalidate_recordset()

        self.assertIn("/report/barcode/QR/", self.repair_order.x_device_test_download_qr_html)
        self.assertIn("/report/barcode/QR/", self.repair_order.x_device_test_pairing_qr_html)
        self.assertIn(run.pairing_token, self.repair_order.x_device_test_pairing_payload)
