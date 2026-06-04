# -*- coding: utf-8 -*-

from odoo.tests.common import SavepointCase
from odoo.exceptions import UserError


class TestBudgetWorkflow(SavepointCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "Cliente workflow SAT"})
        cls.product = cls.env["product.product"].create(
            {
                "name": "Equipo workflow SAT",
                "type": "service",
                "list_price": 99.0,
            }
        )

    @classmethod
    def _create_sale_order(cls):
        return cls.env["sale.order"].create(
            {
                "partner_id": cls.partner.id,
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
            "partner_id": cls.partner.id,
            "product_id": cls.product.id,
            "product_uom": cls.product.uom_id.id,
            "product_qty": 1.0,
            "x_reported_issue": "No enciende",
        }
        vals.update(extra_vals)
        return cls.env["repair.order"].create(vals)

    def test_wait_customer_without_quote_opens_confirmation(self):
        repair = self._create_repair(x_budget_stage="estimating")

        action = repair.action_budget_wait_customer()

        self.assertEqual(action["res_model"], "wex.budget.workflow.confirm.wizard")
        self.assertEqual(
            action["context"]["default_action_key"], "wait_customer_without_quote"
        )
        self.assertEqual(repair.x_budget_stage, "estimating")

    def test_start_budget_supports_multiple_repairs(self):
        repair_a = self._create_repair()
        repair_b = self._create_repair()

        (repair_a | repair_b).action_start_budget()

        self.assertEqual(repair_a.x_budget_stage, "estimating")
        self.assertEqual(repair_b.x_budget_stage, "estimating")
        self.assertTrue(repair_a.x_budget_started_at)
        self.assertTrue(repair_b.x_budget_started_at)

    def test_accept_budget_requires_sale_order_and_confirms_repair(self):
        repair = self._create_repair(x_budget_stage="waiting_customer")

        with self.assertRaises(UserError):
            repair.action_budget_accept()

        sale_order = self._create_sale_order()
        repair.sale_order_id = sale_order

        repair.action_budget_accept()

        self.assertEqual(sale_order.state, "sale")
        self.assertEqual(repair.state, "confirmed")
        self.assertEqual(repair.x_budget_stage, "accepted")

    def test_reject_budget_confirmation_cancels_sale_order(self):
        sale_order = self._create_sale_order()
        repair = self._create_repair(
            x_budget_stage="waiting_customer",
            sale_order_id=sale_order.id,
        )

        action = repair.action_budget_reject()
        self.assertEqual(action["res_model"], "wex.budget.workflow.confirm.wizard")
        self.assertEqual(action["context"]["default_action_key"], "reject_budget")

        wizard = self.env["wex.budget.workflow.confirm.wizard"].with_context(
            action["context"]
        ).create({})
        wizard.action_confirm()

        self.assertEqual(sale_order.state, "cancel")
        self.assertEqual(repair.x_budget_stage, "rejected")

    def test_reestimate_from_accepted_opens_confirmation_and_resets_sale_order(self):
        sale_order = self._create_sale_order()
        repair = self._create_repair(
            x_budget_stage="waiting_customer",
            sale_order_id=sale_order.id,
        )
        repair.action_budget_accept()

        action = repair.action_budget_reestimate()
        self.assertEqual(action["res_model"], "wex.budget.workflow.confirm.wizard")
        self.assertEqual(
            action["context"]["default_action_key"], "reestimate_budget_reset_quote"
        )

        wizard = self.env["wex.budget.workflow.confirm.wizard"].with_context(
            action["context"]
        ).create({})
        wizard.action_confirm()

        self.assertEqual(sale_order.state, "draft")
        self.assertEqual(repair.x_budget_stage, "estimating")

    def test_reject_after_reestimate_can_cancel_sale_order_again(self):
        sale_order = self._create_sale_order()
        repair = self._create_repair(
            x_budget_stage="waiting_customer",
            sale_order_id=sale_order.id,
        )
        repair.action_budget_accept()

        reestimate_action = repair.action_budget_reestimate()
        reestimate_wizard = self.env["wex.budget.workflow.confirm.wizard"].with_context(
            reestimate_action["context"]
        ).create({})
        reestimate_wizard.action_confirm()

        repair.action_budget_wait_customer()
        reject_action = repair.action_budget_reject()
        reject_wizard = self.env["wex.budget.workflow.confirm.wizard"].with_context(
            reject_action["context"]
        ).create({})
        reject_wizard.action_confirm()

        self.assertEqual(sale_order.state, "cancel")
        self.assertEqual(repair.x_budget_stage, "rejected")
