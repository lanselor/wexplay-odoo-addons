from odoo import Command
from odoo.exceptions import AccessError, UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestPortalBilling(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({
            "name": "Billing company", "is_company": True, "x_is_professional_sat_customer": True,
        })
        cls.contact = cls.env["res.partner"].create({"name": "Billing contact", "parent_id": cls.partner.id})
        cls.portal_user = cls.env["res.users"].with_context(no_reset_password=True).create({
            "name": "Billing portal", "login": "billing.test@example.com", "partner_id": cls.contact.id,
            "groups_id": [Command.set([cls.env.ref("base.group_portal").id])],
        })
        cls.product = cls.env["product.product"].create({
            "name": "Billing service", "type": "service", "invoice_policy": "order",
        })
        cls.device = cls.env["product.product"].create({"name": "Billing device"})

    def _repair(self, reference="E0453795HG", state="under_repair", device_type="laptop"):
        order = self.env["sale.order"].create({
            "partner_id": self.partner.id,
            "order_line": [Command.create({"product_id": self.product.id, "product_uom_qty": 1, "price_unit": 20})],
        })
        order.action_confirm()
        return self.env["repair.order"].create({
            "partner_id": self.contact.id, "product_id": self.device.id,
            "sale_order_id": order.id, "x_customer_reference": reference,
            "state": state, "x_budget_stage": "accepted", "x_device_type": device_type,
        })

    def test_manual_is_idempotent_and_does_not_invoice(self):
        repair = self._repair()
        repair.action_add_portal_billing()
        added = repair.wex_portal_billing_added_at
        repair.action_add_portal_billing()
        self.assertEqual(repair.wex_portal_billing_added_at, added)
        self.assertFalse(repair.sale_order_id.invoice_ids)

    def test_missing_quote_stays_visible(self):
        repair = self._repair()
        repair.sale_order_id = False
        repair.action_add_portal_billing()
        self.assertTrue(repair.wex_billing_issue)
        with self.assertRaises(UserError):
            repair.action_create_portal_billing_invoices()

    def test_finish_prompt_does_not_mark_until_confirmed(self):
        repair = self._repair()
        action = repair.action_repair_end()
        self.assertEqual(action["res_model"], "wex.finish.repair.glue.choice.wizard")
        self.assertFalse(repair.wex_portal_billing_pending)
        wizard = self.env[action["res_model"]].create({"repair_id": repair.id})
        wizard.action_finish_with_billing()
        self.assertEqual(repair.state, "done")
        self.assertTrue(repair.wex_portal_billing_pending)

    def test_finish_without_mark(self):
        repair = self._repair()
        wizard = self.env["wex.finish.repair.glue.choice.wizard"].create({"repair_id": repair.id})
        wizard.action_finish_without_billing()
        self.assertEqual(repair.state, "done")
        self.assertFalse(repair.wex_portal_billing_pending)

    def test_automatic_finish_and_warranty_exclusion(self):
        self.partner.wex_auto_portal_billing = True
        repair = self._repair()
        repair.action_repair_end()
        self.assertTrue(repair.wex_portal_billing_pending)
        warranty = self._repair()
        warranty.under_warranty = True
        self.assertFalse(warranty._should_offer_portal_billing())

    def test_glue_requires_choice_and_finishes_in_one_wizard(self):
        repair = self._repair(device_type="mobile")
        action = repair.action_repair_end()
        wizard = self.env[action["res_model"]].create({"repair_id": repair.id})
        self.assertTrue(wizard.wex_requires_glue)
        with self.assertRaises(UserError):
            wizard._finish_and_set_location(False)
        self.assertFalse(repair.wex_portal_billing_pending)
        wizard.wex_billing_choice = "yes"
        wizard._finish_and_set_location(False)
        self.assertEqual(repair.state, "done")
        self.assertTrue(repair.wex_portal_billing_pending)

    def test_portal_cannot_mark(self):
        repair = self._repair()
        with self.assertRaises(AccessError):
            repair.with_user(self.portal_user).action_add_portal_billing()

    def test_native_grouped_invoice_references_and_snapshot(self):
        repairs = self._repair("E-FIRST") | self._repair("E-SECOND")
        repairs.action_add_portal_billing()
        action = repairs.action_create_portal_billing_invoices()
        wizard = self.env["sale.advance.payment.inv"].with_context(action["context"]).create({"advance_payment_method": "delivered"})
        wizard.create_invoices()
        invoices = repairs.sale_order_id.invoice_ids
        self.assertEqual(len(invoices), 1)
        self.assertEqual(invoices.state, "draft")
        for repair in repairs:
            line = invoices.invoice_line_ids.filtered(lambda l: repair.sale_order_id in l.sale_line_ids.order_id)
            self.assertIn(repair.x_customer_reference, line.name)
        names = invoices.invoice_line_ids.mapped("name")
        repairs.write({"x_customer_reference": "CHANGED"})
        self.assertEqual(invoices.invoice_line_ids.mapped("name"), names)
        self.assertFalse(any(repairs.mapped("wex_portal_billing_pending")))
        self.assertTrue(all(repairs.mapped("wex_portal_billing_tracked")))
        with self.assertRaises(UserError):
            repairs.action_create_portal_billing_invoices()

    def test_no_reference_and_no_economic_change(self):
        repair = self._repair("")
        line = repair.sale_order_id.order_line
        original = line._prepare_invoice_line()
        repair.x_customer_reference = "E-SNAPSHOT"
        modified = line._prepare_invoice_line()
        self.assertNotEqual(original.pop("name"), modified.pop("name"))
        self.assertEqual(original, modified)

    def test_ambiguous_order_is_not_silently_misattributed(self):
        repairs = self._repair("E-ONE") | self._repair("E-TWO")
        repairs[1].sale_order_id = repairs[0].sale_order_id
        with self.assertRaises(UserError):
            repairs[0].sale_order_id.order_line._prepare_invoice_line()

    def test_unrelated_sale_keeps_description(self):
        order = self.env["sale.order"].create({
            "partner_id": self.partner.id,
            "order_line": [Command.create({"product_id": self.product.id, "name": "Unrelated sale", "price_unit": 20})],
        })
        self.assertNotIn("Referencia del cliente", order.order_line._prepare_invoice_line()["name"])

    def test_revoked_portal_blocks_manual_add(self):
        repair = self._repair()
        self.portal_user.active = False
        self.partner.invalidate_recordset(["wex_has_active_portal"])
        with self.assertRaises(UserError):
            repair.action_add_portal_billing()
        self.assertFalse(repair.wex_portal_billing_pending)

    def test_mixed_clients_do_not_open_invoice_wizard(self):
        repairs = self._repair("E-ONE") | self._repair("E-TWO")
        repairs.action_add_portal_billing()
        other = self.env["res.partner"].create({"name": "Other client", "is_company": True})
        repairs[1].partner_id = other
        with self.assertRaises(UserError):
            repairs.action_create_portal_billing_invoices()

    def test_native_finish_failure_does_not_enroll(self):
        from unittest.mock import patch
        from odoo.addons.repair.models.repair import Repair as NativeRepair
        repair = self._repair()
        self.partner.wex_auto_portal_billing = True
        with patch.object(NativeRepair, "action_repair_end", side_effect=UserError("Native validation failure")):
            with self.assertRaises(UserError):
                repair.action_repair_end()
        self.assertFalse(repair.wex_portal_billing_pending)
        self.assertEqual(repair.state, "under_repair")

    def test_cancel_draft_reconfirm_preserves_tracking(self):
        repair = self._repair()
        repair.action_add_portal_billing()
        order = repair.sale_order_id
        order.with_context(disable_cancel_warning=True).action_cancel()
        self.assertFalse(repair.wex_portal_billing_pending)
        self.assertEqual(repair.wex_billing_tracking_state, "cancelled")
        order.action_draft()
        self.assertFalse(repair.wex_portal_billing_pending)
        order.order_line.price_unit = 25
        order.action_confirm()
        self.assertTrue(repair.wex_portal_billing_pending)

    def test_delete_draft_invoice_reopens(self):
        repair = self._repair()
        repair.action_add_portal_billing()
        invoice = repair.sale_order_id._create_invoices()
        self.assertFalse(repair.wex_portal_billing_pending)
        invoice.unlink()
        self.assertTrue(repair.wex_portal_billing_pending)

    def test_cancel_invoice_reopens(self):
        repair = self._repair()
        repair.action_add_portal_billing()
        invoice = repair.sale_order_id._create_invoices()
        self.assertFalse(repair.wex_portal_billing_pending)
        invoice.button_cancel()
        self.assertTrue(repair.wex_portal_billing_pending)

    def test_manual_removal_survives_order_and_invoice_changes(self):
        repair = self._repair()
        repair.action_add_portal_billing()
        repair.action_remove_portal_billing()
        self.assertEqual(repair.wex_billing_removed_by, self.env.user)
        self.assertEqual(repair.wex_billing_tracking_state, "manual")
        order = repair.sale_order_id
        order.with_context(disable_cancel_warning=True).action_cancel()
        order.action_draft()
        order.action_confirm()
        self.assertFalse(repair.wex_portal_billing_pending)
        self.assertFalse(repair._should_offer_portal_billing())
        repair.action_add_portal_billing()
        self.assertTrue(repair.wex_portal_billing_pending)

    def test_partial_and_advance_do_not_remove(self):
        repair = self._repair()
        repair.action_add_portal_billing()
        order = repair.sale_order_id
        wizard = self.env["sale.advance.payment.inv"].with_context(
            active_model="sale.order", active_ids=order.ids,
        ).create({"advance_payment_method": "fixed", "fixed_amount": 5})
        wizard.create_invoices()
        self.assertTrue(repair.wex_portal_billing_pending)
        order._create_invoices(final=True)
        invoice_line = order.order_line.filtered(lambda l: not l.is_downpayment).invoice_lines
        invoice_line.quantity = 0.5
        self.assertTrue(repair.wex_portal_billing_pending)

    def test_untracked_order_never_enters_queue(self):
        repair = self._repair()
        order = repair.sale_order_id
        order.with_context(disable_cancel_warning=True).action_cancel()
        order.action_draft()
        order.action_confirm()
        self.assertFalse(repair.wex_portal_billing_pending)

    def test_portal_cannot_remove(self):
        repair = self._repair()
        repair.action_add_portal_billing()
        with self.assertRaises(AccessError):
            repair.with_user(self.portal_user).action_remove_portal_billing()
        self.assertTrue(repair.wex_portal_billing_pending)
