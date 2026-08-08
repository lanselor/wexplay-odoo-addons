from unittest.mock import patch

from odoo.addons.wex_whatsapp_chatter.models.whatsapp_compose_wizard import (
    WhatsappComposeWizard,
)
from odoo.tests.common import SavepointCase


class TestWhatsappComposeWizard(SavepointCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create(
            {
                "name": "WhatsApp Wizard Test Partner",
                "mobile": "600000000",
            }
        )

    def test_repair_wizard_create_does_not_post_normalization_note(self):
        with patch.object(WhatsappComposeWizard, "_post_guardrail_note") as post_note:
            self.env["whatsapp.compose.wizard"].with_context(
                default_res_model="repair.order",
                default_res_id=1,
            ).create(
                {
                    "res_model": "repair.order",
                    "res_model_ctx": "repair.order",
                    "res_id_ctx": 1,
                    "partner_id": self.partner.id,
                    "phone_source": "mobile",
                    "phone_number": self.partner.mobile,
                }
            )

        post_note.assert_not_called()

    def test_relational_placeholder_value_is_limited_to_five_records(self):
        categories = self.env["res.partner.category"].create(
            [{"name": f"Category {index}"} for index in range(7)]
        )
        self.partner.category_id = categories
        wizard = self.env["whatsapp.compose.wizard"].new(
            {
                "res_model": "res.partner",
                "partner_id": self.partner.id,
                "phone_source": "mobile",
                "phone_number": self.partner.mobile,
            }
        )

        value = wizard._safe_getattr_path(self.partner, "category_id")

        self.assertEqual(len(value), 5)
        self.assertEqual(
            wizard._format_value(self.partner, self.partner.category_id),
            ", ".join(categories[:5].mapped("display_name")),
        )

    def test_quick_access_configuration_has_been_removed(self):
        self.assertNotIn("is_quick_access", self.env["whatsapp.template"]._fields)
