# -*- coding: utf-8 -*-

from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestRepairWarranty(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "Cliente garantia"})
        cls.repair_product = cls.env["product.product"].create({"name": "Equipo SAT"})
        cls.sale_product = cls.env["product.product"].create({"name": "Producto facturable"})

        cls.service_product_basic = cls.env["product.product"].create(
            {
                "name": "Servicio basico SAT",
                "type": "service",
            }
        )
        cls.service_product_basic.product_tmpl_id.write(
            {
                "x_warranty_parts_months": 6,
                "x_warranty_labor_months": 3,
            }
        )

        cls.service_product_premium = cls.env["product.product"].create(
            {
                "name": "Servicio premium SAT",
                "type": "service",
            }
        )
        cls.service_product_premium.product_tmpl_id.write(
            {
                "x_warranty_parts_months": 12,
                "x_warranty_labor_months": 6,
            }
        )

    @classmethod
    def _create_sale_order(cls):
        sale_order = cls.env["sale.order"].create(
            {
                "partner_id": cls.partner.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": cls.sale_product.id,
                            "product_uom_qty": 1.0,
                            "price_unit": 100.0,
                            "name": cls.sale_product.display_name,
                        },
                    )
                ],
            }
        )
        sale_order.action_confirm()
        return sale_order

    @classmethod
    def _create_posted_invoice(cls, sale_order, invoice_date):
        invoice = sale_order._create_invoices()
        invoice.invoice_date = invoice_date
        invoice.action_post()
        return invoice

    @classmethod
    def _create_additional_posted_invoice(cls, base_invoice, invoice_date):
        invoice_line_vals = []
        for line in base_invoice.invoice_line_ids.filtered(lambda l: not l.display_type):
            invoice_line_vals.append(
                (
                    0,
                    0,
                    {
                        "product_id": line.product_id.id,
                        "name": line.name,
                        "quantity": line.quantity,
                        "price_unit": line.price_unit,
                        "account_id": line.account_id.id,
                        "tax_ids": [(6, 0, line.tax_ids.ids)],
                        "sale_line_ids": [(6, 0, line.sale_line_ids.ids)],
                    },
                )
            )

        invoice = cls.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": base_invoice.partner_id.id,
                "invoice_date": invoice_date,
                "invoice_line_ids": invoice_line_vals,
            }
        )
        invoice.action_post()
        return invoice

    @classmethod
    def _create_repair(cls, sale_order, service_products, **extra_vals):
        vals = {
            "partner_id": cls.partner.id,
            "product_id": cls.repair_product.id,
            "product_uom": cls.repair_product.uom_id.id,
            "product_qty": 1.0,
            "sale_order_id": sale_order.id,
            "repair_service_ids": [
                (
                    0,
                    0,
                    {
                        "product_id": product.id,
                        "product_uom_qty": 1.0,
                    },
                )
                for product in service_products
            ],
        }
        vals.update(extra_vals)
        return cls.env["repair.order"].create(vals)

    def test_snapshot_uses_first_posted_invoice_and_best_service(self):
        sale_order = self._create_sale_order()
        first_invoice = self._create_posted_invoice(
            sale_order, fields.Date.to_date("2026-01-10")
        )
        second_invoice = self._create_additional_posted_invoice(
            first_invoice, fields.Date.to_date("2026-02-10")
        )

        repair = self._create_repair(
            sale_order,
            [self.service_product_basic, self.service_product_premium],
        )

        self.assertEqual(repair.x_warranty_source_invoice_id, first_invoice)
        self.assertEqual(repair.x_warranty_source_invoice_date, first_invoice.invoice_date)
        self.assertEqual(repair.x_warranty_parts_months, 12)
        self.assertEqual(repair.x_warranty_labor_months, 6)
        self.assertIn(second_invoice, repair._get_posted_customer_invoices())

    def test_snapshot_refreshes_when_service_is_added_after_invoice(self):
        sale_order = self._create_sale_order()
        invoice_date = fields.Date.context_today(self.env.user) - relativedelta(days=1)
        self._create_posted_invoice(sale_order, invoice_date)

        repair = self._create_repair(sale_order, [])

        self.assertEqual(repair.x_warranty_parts_months, 0)
        self.assertEqual(repair.x_warranty_labor_months, 0)

        repair.write(
            {
                "repair_service_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.service_product_basic.id,
                            "product_uom_qty": 1.0,
                        },
                    )
                ]
            }
        )

        self.assertEqual(repair.x_warranty_parts_months, 6)
        self.assertEqual(repair.x_warranty_labor_months, 3)
        self.assertEqual(
            repair.x_warranty_labor_deadline,
            invoice_date + relativedelta(months=3),
        )
        self.assertTrue(repair.x_is_any_warranty_valid)

        child_repair = repair._create_warranty_child_repair()
        self.assertEqual(child_repair.product_id, repair.product_id)
        self.assertTrue(child_repair.x_is_warranty_case)

    def test_force_no_warranty_zeroes_snapshot(self):
        sale_order = self._create_sale_order()
        self._create_posted_invoice(sale_order, fields.Date.to_date("2026-03-05"))

        repair = self._create_repair(
            sale_order,
            [self.service_product_premium],
            x_force_no_warranty=True,
        )

        self.assertEqual(repair.x_warranty_parts_months, 0)
        self.assertEqual(repair.x_warranty_labor_months, 0)
        self.assertEqual(repair.x_warranty_status, "forced_no_warranty")

    def test_create_warranty_child_repair_keeps_traceability(self):
        sale_order = self._create_sale_order()
        self._create_posted_invoice(sale_order, fields.Date.to_date("2026-04-01"))

        repair = self._create_repair(sale_order, [self.service_product_premium])
        child_repair = repair._create_warranty_child_repair()

        self.assertTrue(child_repair.x_is_warranty_case)
        self.assertEqual(child_repair.x_warranty_origin_repair_id, repair)
        self.assertEqual(
            child_repair.x_warranty_source_invoice_id,
            repair.x_warranty_source_invoice_id,
        )
        self.assertEqual(
            child_repair.x_warranty_parts_months,
            repair.x_warranty_parts_months,
        )
        self.assertEqual(child_repair.x_warranty_claim_admission, "automatic")
        self.assertFalse(child_repair.repair_service_ids)
        self.assertTrue(child_repair.name.startswith("SATRMA"))

    def test_forced_warranty_claim_allows_exception_without_coverage(self):
        sale_order = self._create_sale_order()
        repair = self._create_repair(sale_order, [])
        repair.write({"x_force_warranty_claim": True})

        wizard = self.env["wex.repair.warranty.claim.wizard"].create(
            {"repair_id": repair.id}
        )
        action = wizard.action_confirm_claim()
        child_repair = self.env["repair.order"].browse(action["res_id"])

        self.assertTrue(child_repair.exists())
        self.assertEqual(child_repair.x_warranty_origin_repair_id, repair)
        self.assertEqual(child_repair.x_warranty_claim_admission, "exception")

    def test_force_no_warranty_blocks_forced_warranty_claim(self):
        sale_order = self._create_sale_order()
        repair = self._create_repair(sale_order, [])

        with self.assertRaises(ValidationError):
            repair.write(
                {
                    "x_force_no_warranty": True,
                    "x_force_warranty_claim": True,
                }
            )

    def test_warranty_case_accept_does_not_require_sale_order(self):
        sale_order = self._create_sale_order()
        self._create_posted_invoice(sale_order, fields.Date.to_date("2026-04-01"))

        repair = self._create_repair(sale_order, [self.service_product_premium])
        warranty_repair = repair._create_warranty_child_repair()
        warranty_repair.write({"x_budget_stage": "waiting_customer"})

        warranty_repair.action_budget_accept()

        self.assertEqual(warranty_repair.x_budget_stage, "accepted")
        self.assertEqual(warranty_repair.state, "confirmed")
        self.assertFalse(warranty_repair.sale_order_id)

    def test_warranty_case_reject_does_not_require_or_cancel_sale_order(self):
        sale_order = self._create_sale_order()
        self._create_posted_invoice(sale_order, fields.Date.to_date("2026-04-01"))

        repair = self._create_repair(sale_order, [self.service_product_premium])
        warranty_repair = repair._create_warranty_child_repair()
        warranty_repair.write({"x_budget_stage": "waiting_customer"})

        action = warranty_repair.action_budget_reject()

        self.assertEqual(action["res_model"], "wex.budget.workflow.confirm.wizard")
        self.assertIn("garantia", action["context"]["default_message"].lower())

        wizard = self.env["wex.budget.workflow.confirm.wizard"].with_context(
            action["context"]
        ).create({})
        wizard.action_confirm()

        self.assertEqual(warranty_repair.x_budget_stage, "rejected")
        self.assertFalse(warranty_repair.sale_order_id)

    def test_warranty_case_reestimate_does_not_try_to_reset_sale_order(self):
        sale_order = self._create_sale_order()
        self._create_posted_invoice(sale_order, fields.Date.to_date("2026-04-01"))

        repair = self._create_repair(sale_order, [self.service_product_premium])
        warranty_repair = repair._create_warranty_child_repair()
        warranty_repair.write({"x_budget_stage": "accepted"})

        result = warranty_repair.action_budget_reestimate()

        self.assertTrue(result)
        self.assertEqual(warranty_repair.x_budget_stage, "estimating")
