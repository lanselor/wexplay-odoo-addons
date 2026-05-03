# -*- coding: utf-8 -*-

import base64
from unittest.mock import patch

from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import SavepointCase


class TestWexConsent(SavepointCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
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
            request.action_sign_request("Cliente SAT", "ZmFrZV9zaWduYXR1cmU=", False)

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
        self.assertEqual(dms_file.directory_id.parent_id.name, self.repair.name)
        self.assertEqual(
            dms_file.directory_id.parent_id.parent_id.name,
            "SAT",
        )
