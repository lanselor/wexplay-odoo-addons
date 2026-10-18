# -*- coding: utf-8 -*-

import base64
import io
import json

from PIL import Image
from lxml import html
from unittest.mock import patch

from odoo.exceptions import AccessError, UserError, ValidationError
from odoo import Command
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestWexConsent(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.groups_id = [Command.link(cls.env.ref("wex_consent.group_wex_consent_manager").id)]
        stream = io.BytesIO()
        Image.new("RGB", (200, 80), "white").save(stream, format="PNG")
        cls.signature = base64.b64encode(stream.getvalue()).decode()
        cls.storage = cls.env["dms.storage"].create(
            {
                "name": "Consent Test Storage",
                "save_type": "database",
            }
        )
        cls.company = cls.env.company
        cls.company.x_wex_consent_dms_storage_id = cls.storage
        cls.company.x_wex_consent_reception_legal_text = (
            "Texto legal de recepción válido para pruebas."
        )
        cls.partner = cls.env["res.partner"].create({"name": "Cliente SAT"})
        cls.product = cls.env["product.product"].create(
            {
                "name": "iPhone test",
            }
        )
        cls.repair = cls.env["repair.order"].create(
            {
                "partner_id": cls.partner.id,
                "product_id": cls.product.id,
                "product_uom": cls.product.uom_id.id,
                "product_qty": 1.0,
                "x_device_type": "mobile",
                "x_device_description": "iPhone negro 128GB con funda",
                "x_reported_issue": "No carga",
            }
        )

    def test_request_queue_flow_marks_document_pending_and_signed(self):
        document = self.env["wex.consent.document"].get_or_create_from_repair(
            self.repair, "reception"
        )
        request = document.action_request_signature()
        session = self.env["wex.consent.kiosk.session"].get_default_session(
            self.company.id
        )

        pulled_request_id = self.env["wex.consent.document"].kiosk_pull_next_request(
            session.id
        )

        self.assertEqual(pulled_request_id, request.id)
        self.assertEqual(request.state, "presented")
        self.assertEqual(document.state, "pending_signature")

        with patch(
            "odoo.addons.wex_consent.models.wex_consent_document.WexConsentDocument.action_generate_signed_pdf",
            autospec=True,
            return_value=True,
        ):
            request.action_sign_request("Cliente SAT", self.signature, False, signer_vat="TEST-001")

        self.assertEqual(request.state, "signed")
        self.assertEqual(document.state, "signed")
        self.assertEqual(document.signer_name, "Cliente SAT")

    def test_reception_consent_defaults_are_not_preselected(self):
        document = self.env["wex.consent.document"].get_or_create_from_repair(
            self.repair, "reception"
        )

        self.assertFalse(document.allow_email_non_commercial)
        self.assertFalse(document.allow_email_commercial)
        self.assertFalse(document.allow_whatsapp_non_commercial)
        self.assertFalse(document.allow_whatsapp_commercial)
        self.assertFalse(document.warranty_conditions_accepted)

    def test_reception_signature_requires_configured_legal_text(self):
        self.company.x_wex_consent_reception_legal_text = ""
        document = self.env["wex.consent.document"].create(
            {
                "name": "Recepción sin texto legal",
                "repair_order_id": self.repair.id,
                "document_type": "reception",
            }
        )

        with self.assertRaises(UserError):
            document.action_request_signature()

    def test_cancelled_document_does_not_block_new_document(self):
        document = self.env["wex.consent.document"].get_or_create_from_repair(
            self.repair, "reception"
        )
        document.state = "cancelled"

        new_document = self.env["wex.consent.document"].get_or_create_from_repair(
            self.repair, "reception"
        )

        self.assertNotEqual(document, new_document)
        self.assertEqual(new_document.state, "draft")
        self.assertEqual(new_document.document_type, "reception")

    def test_signed_document_is_reused_and_not_overwritten(self):
        document = self.env["wex.consent.document"].get_or_create_from_repair(
            self.repair, "reception"
        )
        document.write(
            {
                "state": "signed",
                "signer_name": "Firmante original",
                "legal_text": "Texto legal firmado original.",
            }
        )

        reused_document = self.env["wex.consent.document"].get_or_create_from_repair(
            self.repair, "reception"
        )

        self.assertEqual(reused_document, document)
        self.assertEqual(reused_document.state, "signed")
        self.assertEqual(reused_document.signer_name, "Firmante original")
        self.assertEqual(reused_document.legal_text, "Texto legal firmado original.")

    def test_duplicate_active_document_is_blocked(self):
        self.env["wex.consent.document"].get_or_create_from_repair(
            self.repair, "delivery"
        )

        with self.assertRaises(ValidationError):
            self.env["wex.consent.document"].create(
                {
                    "name": "Entrega duplicada",
                    "repair_order_id": self.repair.id,
                    "document_type": "delivery",
                }
            )

    def test_duplicate_active_documents_are_blocked_in_batch_create(self):
        with self.assertRaises(ValidationError):
            self.env["wex.consent.document"].create(
                [
                    {
                        "name": "Recepción duplicada A",
                        "repair_order_id": self.repair.id,
                        "document_type": "reception",
                    },
                    {
                        "name": "Recepción duplicada B",
                        "repair_order_id": self.repair.id,
                        "document_type": "reception",
                    },
                ]
            )

    def test_duplicate_active_documents_are_blocked_in_batch_write(self):
        delivery_document = self.env["wex.consent.document"].get_or_create_from_repair(
            self.repair, "delivery"
        )
        reception_document = self.env["wex.consent.document"].get_or_create_from_repair(
            self.repair, "reception"
        )

        with self.assertRaises(ValidationError):
            (delivery_document | reception_document).write({"document_type": "delivery"})

    def test_store_pdf_in_dms_creates_sat_repair_and_signatures_tree(self):
        document = self.env["wex.consent.document"].get_or_create_from_repair(
            self.repair, "delivery"
        )
        document.write(
            {
                "pdf_file": base64.b64encode(b"%PDF-1.4 test"),
                "pdf_filename": "delivery-test.pdf",
            }
        )

        dms_file = document._store_pdf_in_dms()

        self.assertTrue(dms_file)
        self.assertEqual(dms_file.directory_id.name, "SIGNATURES")
        self.assertEqual(dms_file.directory_id.parent_id.name, self.repair._get_sat_dms_safe_name())
        self.assertEqual(
            dms_file.directory_id.parent_id.parent_id.name,
            "SAT",
        )

    def _inspection(self, device_type="mobile", console_format=None):
        marks = {"device_type": device_type, "front": [[[0.1, 0.2], [0.3, 0.4]]], "back": []}
        if console_format:
            marks["console_format"] = console_format
        self.repair.write({
            "x_device_type": device_type,
            "x_device_inspection_marks": marks,
            "x_device_condition_ids": [Command.set(self.env.ref(
                "wexplay_repair.device_condition_broken_screen"
            ).ids)],
        })
        return self.env["wex.consent.document"].get_or_create_from_repair(self.repair, "reception")

    def _present(self, document):
        request = document.action_request_signature()
        session = self.env["wex.consent.kiosk.session"].get_default_session(self.company.id)
        request.action_mark_presented(session)
        return request

    def test_reception_snapshot_contains_both_composed_faces(self):
        document = self._inspection()
        snapshot = document._get_document_snapshot()
        inspection = document._get_reception_inspection_snapshot()
        self.assertEqual(snapshot["device_type"], "mobile")
        self.assertEqual(inspection["description"], self.repair.x_device_description)
        self.assertEqual(len(inspection["conditions"]), 1)
        self.assertEqual(len(inspection["views"]), 2)
        self.assertTrue(all(view["src"].startswith("data:image/svg+xml;base64,") for view in inspection["views"]))

    def test_queued_and_presented_snapshot_cannot_change(self):
        document = self._inspection()
        request = document.action_request_signature()
        original = document.snapshot_json
        original_text = document.device_description
        self.repair.write({"x_device_description": "Edited after request", "x_device_inspection_marks": False})
        self.env.ref("wexplay_repair.device_condition_broken_screen").name = "Renamed condition"
        document.action_refresh_from_repair()
        self.assertEqual(document.action_request_signature(), request)
        self.assertEqual(document.snapshot_json, original)
        self.assertEqual(document.device_description, original_text)
        for values in ({"snapshot_json": "{}"}, {"device_description": "Changed"},
                       {"legal_text": "Changed"}, {"state": "draft"},
                       {"repair_order_id": self.repair.id}):
            with self.assertRaises(UserError), self.cr.savepoint():
                document.write(values)
        self._present(document)
        document.action_refresh_from_repair()
        self.assertEqual(document.snapshot_json, original)
        with self.assertRaises(UserError), self.cr.savepoint():
            document.write({"snapshot_json": "{}"})

    def test_cancel_and_resend_capture_new_inspection(self):
        document = self._inspection()
        request = self._present(document)
        original = document.snapshot_json
        self.repair.x_device_description = "New reception text"
        request.action_requeue_clean()
        self.assertEqual(request.state, "cancelled")
        self.assertNotEqual(document.snapshot_json, original)
        self.assertEqual(document.device_description, "New reception text")
        self.assertEqual(document.active_request_id.state, "queued")
        self.assertNotEqual(document.active_request_id, request)
        with self.assertRaises(UserError), self.cr.savepoint():
            request.action_sign_request("Cliente", self.signature, signer_vat="TEST-001")

    def test_signed_snapshot_and_pdf_cannot_be_rewritten(self):
        document = self._inspection()
        request = self._present(document)
        with patch.object(type(document), "action_generate_signed_pdf", return_value=True):
            request.action_sign_request("Cliente SAT", self.signature, signer_vat="TEST-001")
        original = document.snapshot_json
        self.repair.x_device_description = "Changed after signature"
        document.action_refresh_from_repair()
        self.assertEqual(document.snapshot_json, original)
        for values in ({"state": "draft"}, {"snapshot_json": "{}"},
                       {"device_description": "New"}, {"signature_image": self.signature},
                       {"pdf_file": base64.b64encode(b"new")}, {"legal_data_protection": False}):
            with self.assertRaises(UserError), self.cr.savepoint():
                document.with_context(force_regenerate_consent_pdf=True).write(values)

    def test_no_live_svg_reads_after_snapshot(self):
        document = self._inspection("console", "handheld_pc")
        request = document.action_request_signature()
        original = document._get_reception_inspection_snapshot()
        with patch.object(type(self.repair), "_prepare_device_inspection_snapshot", side_effect=AssertionError("live read")):
            document.action_refresh_from_repair()
            self.assertEqual(document.action_request_signature(), request)
            self.assertEqual(document._get_reception_inspection_snapshot(), original)
            report = self.env.ref(document._get_report_xmlid())
            rendered, _ = self.env["ir.actions.report"]._render_qweb_html(report.report_name, document.ids)
        tree = html.fromstring(rendered)
        self.assertEqual(len(tree.xpath("//table[@class='wex_consent_pdf_faces']//img")), 2)

    def test_empty_legacy_and_delivery_have_no_inspection_block(self):
        document = self.env["wex.consent.document"].get_or_create_from_repair(self.repair, "reception")
        self.repair.x_device_description = False
        document.action_refresh_from_repair()
        self.assertFalse(document._get_reception_inspection_snapshot())
        document.snapshot_json = json.dumps({"device_description": "Legacy"})
        self.assertFalse(document._get_reception_inspection_snapshot())
        delivery = self.env["wex.consent.document"].get_or_create_from_repair(self.repair, "delivery")
        self.assertNotIn("device_inspection", delivery._get_document_snapshot())
        self.assertFalse(delivery._get_reception_inspection_snapshot())

    def test_text_tags_only_and_console_metadata(self):
        document = self._inspection("console", "desktop")
        self.repair.x_device_inspection_marks = {"device_type": "console", "console_format": "desktop", "front": [], "back": []}
        document.action_refresh_from_repair()
        inspection = document._get_reception_inspection_snapshot()
        self.assertEqual(document._get_document_snapshot()["console_format"], "desktop")
        self.assertTrue(inspection["conditions"])
        self.assertFalse(inspection["views"])

    def test_signed_pdf_generation_archives_and_blocks_regeneration(self):
        document = self._inspection()
        request = self._present(document)
        report_model = type(self.env["ir.actions.report"])
        pdf = b"%PDF-1.4 consent integration test"
        with patch.object(report_model, "_render_qweb_pdf", return_value=(pdf, "pdf")):
            request.action_sign_request("Cliente SAT", self.signature, signer_vat="TEST-001")
        self.assertEqual(base64.b64decode(document.pdf_file), pdf)
        self.assertEqual(base64.b64decode(document.dms_file_id.content), pdf)
        self.assertEqual(document.dms_file_id.directory_id.name, "SIGNATURES")
        with self.assertRaises(UserError), self.cr.savepoint():
            document.with_context(force_regenerate_consent_pdf=True).action_generate_signed_pdf()

    def test_pdf_failure_rolls_back_signature(self):
        document = self._inspection()
        request = self._present(document)
        with self.assertRaises(UserError), self.cr.savepoint():
            with patch.object(type(self.env["ir.actions.report"]), "_render_qweb_pdf", return_value=(b"%PDF test", "pdf")), patch.object(
                type(document), "_store_pdf_in_dms", side_effect=UserError("DMS unavailable")
            ):
                request.action_sign_request("Cliente", self.signature, signer_vat="TEST-001")
        self.assertEqual(document.state, "pending_signature")
        self.assertEqual(request.state, "presented")
        self.assertFalse(document.pdf_file)
        self.assertFalse(document.signature_image)

    def test_queued_request_cannot_be_signed(self):
        document = self._inspection()
        request = document.action_request_signature()
        with self.assertRaises(UserError), self.cr.savepoint():
            request.action_sign_request("Cliente", self.signature, signer_vat="TEST-001")
        with self.assertRaises(UserError), self.cr.savepoint():
            document.action_register_signature("Cliente", self.signature, signer_vat="TEST-001")

    def test_manager_cannot_edit_frozen_document_through_orm(self):
        document = self._inspection()
        document.action_request_signature()
        manager = new_test_user(self.env, login="consent_snapshot_manager",
            groups="wex_consent.group_wex_consent_manager", company_id=self.company.id,
            company_ids=[Command.set(self.company.ids)])
        with self.assertRaises(UserError), self.cr.savepoint():
            document.with_user(manager).write({"device_description": "Direct API edit"})

    def test_other_company_cannot_read_snapshot(self):
        document = self._inspection()
        other_company = self.env["res.company"].create({"name": "Other consent company"})
        manager = new_test_user(self.env, login="consent_other_company",
            groups="wex_consent.group_wex_consent_manager", company_id=other_company.id,
            company_ids=[Command.set(other_company.ids)])
        with self.assertRaises(AccessError):
            document.with_user(manager).read(["snapshot_json"])
