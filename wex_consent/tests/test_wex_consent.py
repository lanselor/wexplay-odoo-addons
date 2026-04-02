# -*- coding: utf-8 -*-

import base64
from unittest.mock import patch

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
