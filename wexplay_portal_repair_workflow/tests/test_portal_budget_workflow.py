# -*- coding: utf-8 -*-

from odoo.exceptions import AccessError
from odoo.tests.common import SavepointCase


class TestPortalBudgetWorkflow(SavepointCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.portal_group = cls.env.ref("base.group_portal")
        cls.company_partner = cls.env["res.partner"].create({"name": "Empresa Portal Budget"})
        cls.contact_partner = cls.env["res.partner"].create(
            {
                "name": "Contacto Portal Budget",
                "parent_id": cls.company_partner.id,
                "type": "contact",
            }
        )
        cls.other_partner = cls.env["res.partner"].create({"name": "Otra Empresa Budget"})
        cls.product = cls.env["product.product"].create(
            {
                "name": "Servicio SAT Portal Budget",
                "type": "service",
                "list_price": 89.0,
            }
        )
        cls.portal_user = cls.env["res.users"].with_context(no_reset_password=True).create(
            {
                "name": "Portal Budget User",
                "login": "portal.budget.wexplay@example.com",
                "email": "portal.budget.wexplay@example.com",
                "partner_id": cls.contact_partner.id,
                "groups_id": [(6, 0, [cls.portal_group.id])],
            }
        )

    @classmethod
    def _create_budget_repair(cls, partner):
        sale_order = cls.env["sale.order"].create(
            {
                "partner_id": partner.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": cls.product.id,
                            "name": "Revision SAT",
                            "product_uom_qty": 1.0,
                            "product_uom": cls.product.uom_id.id,
                            "price_unit": 89.0,
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
                "x_budget_stage": "waiting_customer",
                "x_reported_issue": "No enciende",
            }
        )
        return repair, sale_order

    def test_portal_accept_confirms_sale_order_and_budget(self):
        repair, sale_order = self._create_budget_repair(self.company_partner)

        repair.with_user(self.portal_user).action_portal_accept_budget(user=self.portal_user)

        self.assertEqual(sale_order.state, "sale")
        self.assertEqual(repair.x_budget_stage, "accepted")
        event = self.env["wex.portal.repair.event"].search(
            [
                ("repair_id", "=", repair.id),
                ("event_type", "=", "budget_accepted"),
            ]
        )
        self.assertEqual(len(event), 1)
        self.assertEqual(event.handled_state, "pending")
        self.assertEqual(event.user_id, self.portal_user)

    def test_portal_reject_cancels_sale_order_and_budget(self):
        repair, sale_order = self._create_budget_repair(self.company_partner)

        repair.with_user(self.portal_user).action_portal_reject_budget(user=self.portal_user)

        self.assertEqual(sale_order.state, "cancel")
        self.assertEqual(repair.x_budget_stage, "rejected")
        event = self.env["wex.portal.repair.event"].search(
            [
                ("repair_id", "=", repair.id),
                ("event_type", "=", "budget_rejected"),
            ]
        )
        self.assertEqual(len(event), 1)
        self.assertEqual(event.handled_state, "pending")
        self.assertEqual(event.sale_order_id, sale_order)

    def test_portal_user_cannot_accept_foreign_budget(self):
        repair, _sale_order = self._create_budget_repair(self.other_partner)

        with self.assertRaises(AccessError):
            repair.with_user(self.portal_user).action_portal_accept_budget(
                user=self.portal_user
            )

    def test_budget_view_event_is_traceability_not_pending_work(self):
        repair, sale_order = self._create_budget_repair(self.company_partner)

        event = repair.with_user(self.portal_user)._create_portal_repair_event(
            "budget_viewed",
            user=self.portal_user,
        )

        self.assertEqual(event.repair_id, repair)
        self.assertEqual(event.sale_order_id, sale_order)
        self.assertEqual(event.handled_state, "done")
