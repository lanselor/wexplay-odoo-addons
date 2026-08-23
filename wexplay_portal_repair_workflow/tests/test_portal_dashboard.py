# -*- coding: utf-8 -*-

from odoo.tests.common import SavepointCase


class TestPortalDashboard(SavepointCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product = cls.env["product.product"].create(
            {
                "name": "Servicio SAT Dashboard",
                "type": "service",
                "list_price": 120.0,
            }
        )
        cls.partner = cls.env["res.partner"].create({"name": "Cliente Dashboard"})
        cls.partner_contact = cls.env["res.partner"].create(
            {
                "name": "Contacto Cliente Dashboard",
                "parent_id": cls.partner.id,
                "type": "contact",
            }
        )
        cls.portal_group = cls.env.ref("base.group_portal")
        cls.portal_user = cls.env["res.users"].with_context(no_reset_password=True).create(
            {
                "name": "Portal Dashboard User",
                "login": "portal.dashboard@example.com",
                "email": "portal.dashboard@example.com",
                "partner_id": cls.partner_contact.id,
                "groups_id": [(6, 0, [cls.portal_group.id])],
            }
        )
        cls.no_portal_partner = cls.env["res.partner"].create({"name": "Cliente sin portal Dashboard"})

    @classmethod
    def _create_repair_with_sale_order(cls, budget_stage="waiting_customer", partner=None):
        partner = partner or cls.partner
        sale_order = cls.env["sale.order"].create(
            {
                "partner_id": partner.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": cls.product.id,
                            "name": "Intervención Dashboard",
                            "product_uom_qty": 1.0,
                            "product_uom": cls.product.uom_id.id,
                            "price_unit": 120.0,
                        },
                    )
                ],
            }
        )
        repair = cls.env["repair.order"].create(
            {
                "partner_id": partner.id,
                "product_id": cls.product.id,
                "product_uom": cls.product.uom_id.id,
                "product_qty": 1.0,
                "sale_order_id": sale_order.id,
                "x_budget_stage": budget_stage,
                "x_reported_issue": "Prueba dashboard",
            }
        )
        return repair, sale_order

    def test_dashboard_data_includes_attention_summary_and_activity(self):
        repair, _sale_order = self._create_repair_with_sale_order()
        repair._create_portal_repair_event("budget_viewed")
        accepted_event = repair._create_portal_repair_event("budget_accepted")
        rejected_event = repair._create_portal_repair_event("budget_rejected")

        data = self.env["wex.portal.dashboard"].get_dashboard_data(period_days=7)

        self.assertEqual(data["period_days"], 7)
        self.assertEqual(len(data["attention_cards"]), 4)
        self.assertEqual(len(data["summary_cards"]), 6)
        self.assertTrue(data["activity_preview"]["rows"])
        self.assertTrue(data["quick_actions"])

        pending_map = {card["title"]: card["value"] for card in data["attention_cards"]}
        self.assertEqual(pending_map["Eventos pendientes"], 2)
        self.assertEqual(pending_map["Aceptaciones por revisar"], 1)
        self.assertEqual(pending_map["Rechazos por revisar"], 1)
        self.assertEqual(pending_map["SAT esperando cliente"], 1)

        preview_event_ids = [row["id"] for row in data["activity_preview"]["rows"]]
        self.assertIn(accepted_event.id, preview_event_ids)
        self.assertIn(rejected_event.id, preview_event_ids)

    def test_dashboard_defaults_invalid_period_to_seven_days(self):
        data = self.env["wex.portal.dashboard"].get_dashboard_data(period_days=999)

        self.assertEqual(data["period_days"], 7)

    def test_active_portal_repairs_only_include_customers_with_active_portal_user(self):
        portal_repair, _sale_order = self._create_repair_with_sale_order()
        no_portal_repair, _sale_order = self._create_repair_with_sale_order(
            partner=self.no_portal_partner
        )

        dashboard = self.env["wex.portal.dashboard"]
        domain = dashboard._get_portal_enabled_active_repair_domain()
        repairs = self.env["repair.order"].search(domain)

        self.assertIn(portal_repair, repairs)
        self.assertNotIn(no_portal_repair, repairs)
