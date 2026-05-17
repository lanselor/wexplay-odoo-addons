# -*- coding: utf-8 -*-

from odoo.exceptions import UserError
from odoo.tests.common import SavepointCase


class TestWhatsappPortalLink(SavepointCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.portal_group = cls.env.ref("base.group_portal")
        cls.product = cls.env["product.product"].create(
            {
                "name": "Equipo SAT portal WhatsApp",
                "type": "service",
                "list_price": 99.0,
            }
        )
        cls.company_partner = cls.env["res.partner"].create(
            {"name": "Cliente portal WhatsApp"}
        )
        cls.contact_partner = cls.env["res.partner"].create(
            {
                "name": "Contacto portal WhatsApp",
                "parent_id": cls.company_partner.id,
                "type": "contact",
            }
        )
        cls.portal_user = cls.env["res.users"].with_context(no_reset_password=True).create(
            {
                "name": "Portal WhatsApp",
                "login": "portal_whatsapp_test",
                "email": "portal_whatsapp_test@example.com",
                "partner_id": cls.contact_partner.id,
                "groups_id": [(6, 0, [cls.portal_group.id])],
            }
        )

    @classmethod
    def _create_sale_order(cls):
        return cls.env["sale.order"].create(
            {
                "partner_id": cls.company_partner.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": cls.product.id,
                            "name": cls.product.display_name,
                            "product_uom_qty": 1.0,
                            "product_uom": cls.product.uom_id.id,
                            "price_unit": 99.0,
                        },
                    )
                ],
            }
        )

    @classmethod
    def _create_repair(cls, **extra_vals):
        vals = {
            "partner_id": cls.company_partner.id,
            "product_id": cls.product.id,
            "product_uom": cls.product.uom_id.id,
            "product_qty": 1.0,
            "x_reported_issue": "No enciende",
        }
        vals.update(extra_vals)
        return cls.env["repair.order"].create(vals)

    def _create_wizard(self, repair):
        return self.env["whatsapp.compose.wizard"].with_context(
            default_res_model="repair.order",
            default_res_id=repair.id,
        ).create(
            {
                "partner_id": self.contact_partner.id,
                "phone_source": "custom",
                "phone_number": "600000000",
                "portal_link_type": "repair_b2b",
                "rendered_body": "${enlaceportalB2B}",
            }
        )

    def test_insert_portal_link_blocks_when_budget_is_not_ready(self):
        repair = self._create_repair(x_budget_stage="estimating")
        wizard = self._create_wizard(repair)

        with self.assertRaisesRegex(UserError, "presupuesto no ha sido iniciado"):
            wizard.action_insert_portal_link()

    def test_insert_portal_link_blocks_when_quote_is_missing(self):
        repair = self._create_repair(
            x_budget_stage="waiting_customer",
            x_budget_started_at="2026-05-09 10:00:00",
        )
        wizard = self._create_wizard(repair)

        with self.assertRaisesRegex(UserError, "cotización vinculada"):
            wizard.action_insert_portal_link()

    def test_insert_portal_link_replaces_placeholder_when_budget_is_ready(self):
        sale_order = self._create_sale_order()
        repair = self._create_repair(
            x_budget_stage="waiting_customer",
            x_budget_started_at="2026-05-09 10:00:00",
            sale_order_id=sale_order.id,
        )
        wizard = self._create_wizard(repair)

        wizard.action_insert_portal_link()

        self.assertIn("/my/repairs/%s" % repair.id, wizard.rendered_body)
        self.assertNotIn("${enlaceportalB2B}", wizard.rendered_body)
