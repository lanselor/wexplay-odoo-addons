# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase


class TestMrwWhatsapp(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.country = cls.env.ref("base.es")
        cls.partner = cls.env["res.partner"].create(
            {
                "name": "MRW WhatsApp Customer",
                "mobile": "600000000",
                "street": "Calle de prueba 1",
                "zip": "15001",
                "city": "A Coruna",
                "country_id": cls.country.id,
            }
        )
        cls.service = cls.env["mrw.shipping.service"].create(
            {"name": "MRW WhatsApp Test", "code": "WA001", "service_type": "national"}
        )
        cls.config = cls.env["mrw.shipping.config"].create(
            {
                "name": "MRW WhatsApp Test",
                "company_id": cls.env.company.id,
                "agency_code": "01400",
                "subscriber_code": "003429",
                "username": "test",
                "password": "test",
            }
        )
        cls.shipment = cls.env["mrw.shipping.shipment"].create(
            {
                "company_id": cls.env.company.id,
                "config_id": cls.config.id,
                "service_id": cls.service.id,
                "partner_id": cls.partner.id,
                "recipient_name": cls.partner.name,
                "recipient_phone": cls.partner.mobile,
                "street": cls.partner.street,
                "zip": cls.partner.zip,
                "city": cls.partner.city,
                "country_id": cls.country.id,
                "mrw_shipment_number": "MRW-WHATSAPP-TEST",
            }
        )

    def test_mrw_action_opens_whatsapp_wizard_in_shipment_context(self):
        action = self.shipment.action_open_mrw_whatsapp()

        self.assertEqual(action["res_model"], "whatsapp.compose.wizard")
        self.assertEqual(action["context"]["default_res_model"], "mrw.shipping.shipment")
        self.assertEqual(action["context"]["default_res_id"], self.shipment.id)

    def test_mrw_tracking_placeholders_are_rendered(self):
        wizard = self.env["whatsapp.compose.wizard"].new(
            {
                "res_model": "mrw.shipping.shipment",
                "res_model_ctx": "mrw.shipping.shipment",
                "res_id_ctx": self.shipment.id,
                "partner_id": self.partner.id,
                "phone_source": "mobile",
                "phone_number": self.partner.mobile,
            }
        )

        rendered = wizard._render_text(
            "${mrw_reference} ${mrw_tracking_number} ${mrw_tracking_url}"
        )

        self.assertIn(self.shipment.reference, rendered)
        self.assertIn(self.shipment.mrw_shipment_number, rendered)
        self.assertIn("MRW_historico_nacional.asp", rendered)
