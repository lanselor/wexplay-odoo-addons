from odoo import fields
from odoo.tests.common import SavepointCase


class TestWexAccountingPortalSecurity(SavepointCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.portal_group = cls.env.ref("base.group_portal")
        cls.accounting_portal_group = cls.env.ref(
            "wex_accounting_portal.group_wex_accounting_portal"
        )

        cls.company = cls.env.company
        cls.other_company = cls.env["res.company"].create({"name": "Other Wex Company"})
        cls.portal_partner = cls.env["res.partner"].create(
            {
                "name": "Accounting Portal Contact",
                "wex_accounting_portal_enabled": True,
            }
        )
        cls.portal_user = cls.env["res.users"].with_context(no_reset_password=True).create(
            {
                "name": "Accounting Portal User",
                "login": "accounting.portal@example.com",
                "email": "accounting.portal@example.com",
                "partner_id": cls.portal_partner.id,
                "groups_id": [(6, 0, [cls.portal_group.id, cls.accounting_portal_group.id])],
                "company_id": cls.company.id,
                "company_ids": [(6, 0, [cls.company.id])],
            }
        )

        cls.customer = cls.env["res.partner"].create(
            {
                "name": "Portal Customer",
                "vat": "B12345678",
            }
        )
        cls.service_product = cls.env["product.product"].create(
            {
                "name": "Accounting Portal Service",
                "type": "service",
            }
        )
        cls.sale_order = cls.env["sale.order"].create(
            {
                "partner_id": cls.customer.id,
                "order_line": [
                    (
                        0,
                        0,
                        {
                            "product_id": cls.service_product.id,
                            "product_uom_qty": 1.0,
                            "price_unit": 100.0,
                            "name": cls.service_product.display_name,
                        },
                    )
                ],
            }
        )
        cls.sale_order.action_confirm()
        cls.invoice = cls.sale_order._create_invoices()
        cls.invoice.invoice_date = fields.Date.to_date("2026-05-10")
        cls.refund = cls.env["account.move"].create(
            {
                "move_type": "out_refund",
                "partner_id": cls.customer.id,
                "invoice_date": fields.Date.to_date("2026-05-12"),
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": cls.service_product.id,
                            "name": "Portal refund",
                            "quantity": 1.0,
                            "price_unit": -20.0,
                            "account_id": cls.invoice.invoice_line_ids.filtered(
                                lambda line: not line.display_type
                            )[:1].account_id.id,
                        },
                    )
                ],
            }
        )
        cls.vendor_bill = cls.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": cls.customer.id,
                "invoice_date": fields.Date.to_date("2026-05-15"),
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": cls.service_product.id,
                            "name": "Vendor bill",
                            "quantity": 1.0,
                            "price_unit": 30.0,
                            "account_id": cls.invoice.invoice_line_ids.filtered(
                                lambda line: not line.display_type
                            )[:1].account_id.id,
                        },
                    )
                ],
            }
        )
        cls.foreign_invoice = cls.env["account.move"].with_company(cls.other_company).create(
            {
                "move_type": "out_invoice",
                "company_id": cls.other_company.id,
                "partner_id": cls.customer.id,
                "invoice_date": fields.Date.to_date("2026-04-03"),
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": cls.service_product.id,
                            "name": "Foreign invoice",
                            "quantity": 1.0,
                            "price_unit": 50.0,
                            "account_id": cls.invoice.invoice_line_ids.filtered(
                                lambda line: not line.display_type
                            )[:1].account_id.id,
                        },
                    )
                ],
            }
        )

    def test_invoice_domain_only_keeps_sale_documents_for_user_companies(self):
        records = self.env["account.move"]._get_wex_accounting_portal_records(self.portal_user)

        self.assertIn(self.invoice, records)
        self.assertIn(self.refund, records)
        self.assertNotIn(self.vendor_bill, records)
        self.assertNotIn(self.foreign_invoice, records)

    def test_invoice_access_helper_rejects_documents_outside_scope(self):
        self.assertTrue(self.invoice._can_user_access_wex_accounting_portal_record(self.portal_user))
        self.assertFalse(
            self.vendor_bill._can_user_access_wex_accounting_portal_record(self.portal_user)
        )
        self.assertFalse(
            self.foreign_invoice._can_user_access_wex_accounting_portal_record(self.portal_user)
        )

    def test_pos_domain_keeps_only_allowed_company_and_states(self):
        domain = self.env["pos.order"]._get_wex_accounting_portal_domain(self.portal_user)
        self.assertIn(("company_id", "in", [self.company.id]), domain)
        self.assertIn(("state", "in", ("paid", "done", "invoiced")), domain)

    def test_enabled_flag_helper_is_explicit(self):
        self.assertTrue(self.portal_partner._is_wex_accounting_portal_enabled_partner())
        self.portal_partner.wex_accounting_portal_enabled = False
        self.assertFalse(self.portal_partner._is_wex_accounting_portal_enabled_partner())

    def test_invoice_period_domain_adds_date_range(self):
        domain = self.env["account.move"]._get_wex_accounting_portal_domain(
            self.portal_user,
            start_date=fields.Date.to_date("2026-05-01"),
            end_date=fields.Date.to_date("2026-05-31"),
        )
        self.assertIn(("invoice_date", ">=", fields.Date.to_date("2026-05-01")), domain)
        self.assertIn(("invoice_date", "<=", fields.Date.to_date("2026-05-31")), domain)

    def test_invoice_summary_values_calculate_net_sales(self):
        summary = self.env["account.move"]._get_wex_accounting_portal_summary_values(
            self.portal_user,
            start_date=fields.Date.to_date("2026-05-01"),
            end_date=fields.Date.to_date("2026-05-31"),
        )

        self.assertEqual(summary["invoice_count"], 1)
        self.assertEqual(summary["refund_count"], 1)
        self.assertEqual(summary["invoice_untaxed_total"], 100.0)
        self.assertEqual(summary["refund_untaxed_total"], 20.0)
        self.assertEqual(summary["net_untaxed_total"], 80.0)
        self.assertEqual(summary["invoice_total"], 100.0)
        self.assertEqual(summary["refund_total"], 20.0)
        self.assertEqual(summary["net_invoiced_total"], 80.0)

    def test_pos_period_domain_uses_datetime_boundaries(self):
        domain = self.env["pos.order"]._get_wex_accounting_portal_period_domain(
            start_date=fields.Date.to_date("2026-05-01"),
            end_date=fields.Date.to_date("2026-05-31"),
        )

        self.assertEqual(domain[0][0], "date_order")
        self.assertEqual(domain[0][1], ">=")
        self.assertEqual(domain[1][0], "date_order")
        self.assertEqual(domain[1][1], "<")

    def test_invoice_search_can_filter_by_customer_vat(self):
        records = self.env["account.move"]._get_wex_accounting_portal_records(
            self.portal_user,
            search_in="vat",
            search="B12345678",
        )

        self.assertIn(self.invoice, records)
        self.assertIn(self.refund, records)
        self.assertNotIn(self.vendor_bill, records)
