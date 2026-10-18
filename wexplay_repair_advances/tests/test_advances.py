from odoo import Command
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import TransactionCase, tagged, new_test_user


@tagged("post_install", "-at_install")
class TestRepairAdvances(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.groups_id = [Command.link(cls.env.ref(
            "wexplay_repair_advances.group_advance_operator").id)]
        account = cls.env["account.account"]
        cls.receivable = account.create({
            "name": "Advance test receivable", "code": "WADVREC",
            "account_type": "asset_receivable", "reconcile": True,
        })
        cls.income = account.create({
            "name": "Advance test income", "code": "WADVINC", "account_type": "income",
        })
        cls.liquidity = account.create({
            "name": "Advance test liquidity", "code": "WADVBANK", "account_type": "asset_cash",
        })
        cls.outstanding = account.create({
            "name": "Advance test outstanding", "code": "WADVOUT",
            "account_type": "asset_current", "reconcile": True,
        })
        cls.journal = cls.env["account.journal"].create({
            "name": "Advance test bank", "code": "WADV", "type": "bank",
            "default_account_id": cls.liquidity.id,
        })
        cls.method = cls.journal.inbound_payment_method_line_ids[:1]
        cls.method.payment_account_id = cls.outstanding
        cls.sale_journal = cls.env["account.journal"].create({
            "name": "Advance test sales", "code": "WADVS", "type": "sale",
            "default_account_id": cls.income.id,
        })
        cls.env.company.wex_advance_journal_ids = [Command.link(cls.journal.id)]
        cls.partner = cls.env["res.partner"].create({
            "name": "Advance customer", "property_account_receivable_id": cls.receivable.id,
        })
        cls.product = cls.env["product.product"].create({"name": "Test device"})
        cls.repair = cls.env["repair.order"].create({
            "partner_id": cls.partner.id, "product_id": cls.product.id,
        })

    def _wizard(self, amount=20):
        return self.env["wex.repair.advance.register"].create({
            "repair_id": self.repair.id, "amount": amount,
            "journal_id": self.journal.id, "payment_method_line_id": self.method.id,
        })

    def _payment(self, amount=20):
        wizard = self._wizard(amount)
        wizard.action_register()
        return wizard.payment_id

    def _invoice(self, amount=80, repair=None):
        repair = repair or self.repair
        order = self.env["sale.order"].create({"partner_id": self.partner.id})
        repair.sale_order_id = order
        line = self.env["sale.order.line"].create({
            "order_id": order.id, "name": "Repair service", "product_id": self.product.id,
            "product_uom_qty": 1, "price_unit": amount, "tax_id": [Command.clear()],
        })
        invoice = self.env["account.move"].create({
            "move_type": "out_invoice", "partner_id": self.partner.id,
            "journal_id": self.sale_journal.id,
            "invoice_line_ids": [Command.create({
                "name": "Repair service", "quantity": 1, "price_unit": amount,
                "account_id": self.income.id, "tax_ids": [Command.clear()],
                "sale_line_ids": [Command.link(line.id)],
            })],
        })
        invoice.action_post()
        return invoice

    def test_register_without_service_and_retry(self):
        wizard = self._wizard()
        wizard.action_register()
        payment = wizard.payment_id
        wizard.action_register()
        self.assertEqual(payment, wizard.payment_id)
        self.assertFalse(self.repair.sale_order_id)
        self.assertEqual(payment.move_id.state, "posted")
        self.assertEqual(payment.wex_advance_available, 20)

    def test_window_actions_include_explicit_views(self):
        register = self.repair.action_register_advance()
        history = self.repair.action_open_advances()
        wizard = self._wizard()
        payment_action = wizard.action_register()
        refund = wizard.payment_id.action_refund_available_advance()
        for action in (register, history, payment_action, refund):
            self.assertEqual(action["type"], "ir.actions.act_window")
            self.assertEqual(
                [view[1] for view in action["views"]], action["view_mode"].split(","),
            )

    def test_apply_preserves_invoice_total_and_native_balance(self):
        payment = self._payment()
        invoice = self._invoice()
        invoice.action_apply_repair_advances()
        self.assertEqual(invoice.amount_total, 80)
        self.assertEqual(invoice.amount_residual, 60)
        self.assertEqual(payment.wex_advance_available, 0)
        invoice.action_apply_repair_advances()
        self.assertEqual(invoice.amount_residual, 60)

    def test_excess_and_unreconcile_restore_available(self):
        payment = self._payment(100)
        invoice = self._invoice()
        invoice.action_apply_repair_advances()
        self.assertEqual(invoice.amount_residual, 0)
        self.assertEqual(payment.wex_advance_available, 20)
        invoice.line_ids.remove_move_reconcile()
        self.assertEqual(payment.wex_advance_available, 100)

    def test_same_customer_other_repair_is_not_consumed(self):
        payment = self._payment()
        other = self.repair.copy({"sale_order_id": False})
        invoice = self._invoice(repair=other)
        invoice.action_apply_repair_advances()
        self.assertEqual(invoice.amount_residual, 80)
        self.assertEqual(payment.wex_advance_available, 20)

    def test_invalid_amount_and_restricted_journal(self):
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self._wizard(0).action_register()
        self.env.company.wex_advance_journal_ids = [Command.set(self.sale_journal.ids)]
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self._wizard().action_register()

    def test_empty_configuration_uses_existing_company_journals(self):
        self.env.company.wex_advance_journal_ids = [Command.clear()]
        wizard = self._wizard()
        self.assertIn(self.journal, wizard.allowed_journal_ids)
        self.assertNotIn(self.sale_journal, wizard.allowed_journal_ids)
        self.assertIn(self.method, wizard.available_payment_method_line_ids)
        wizard.action_register()
        self.assertEqual(wizard.payment_id.amount, 20)

    def test_switching_journal_refreshes_payment_methods(self):
        other = self.journal.copy({"name": "Second advance bank", "code": "WAD2"})
        wizard = self._wizard()
        wizard.journal_id = other
        self.assertEqual(wizard.available_payment_method_line_ids, other.inbound_payment_method_line_ids)
        self.assertIn(wizard.payment_method_line_id, other.inbound_payment_method_line_ids)
        self.assertNotIn(self.method, wizard.available_payment_method_line_ids)

    def test_credit_card_journal_can_register_and_apply_advance(self):
        journal = self.env["account.journal"].create({
            "name": "Advance card terminal", "code": "WCRD", "type": "credit",
        })
        method = journal.inbound_payment_method_line_ids[:1]
        method.payment_account_id = self.outstanding
        self.env.company.wex_advance_journal_ids = [Command.clear()]
        wizard = self._wizard()
        self.assertIn(journal, wizard.allowed_journal_ids)
        wizard.journal_id = journal
        self.assertIn(method, wizard.available_payment_method_line_ids)
        wizard.action_register()
        self.assertEqual(wizard.payment_id.move_id.state, "posted")
        self.assertEqual(wizard.payment_id.wex_advance_available, 20)
        invoice = self._invoice()
        invoice.action_apply_repair_advances()
        self.assertEqual(invoice.amount_total, 80)
        self.assertEqual(invoice.amount_residual, 60)
        self.assertEqual(wizard.payment_id.wex_advance_available, 0)

    def test_explicit_journal_selection_can_include_credit_card(self):
        journal = self.env["account.journal"].create({
            "name": "Allowed card terminal", "code": "WCR2", "type": "credit",
        })
        self.env.company.wex_advance_journal_ids = [Command.set(journal.ids)]
        wizard = self._wizard()
        self.assertEqual(wizard.allowed_journal_ids, journal)
        with self.assertRaises(ValidationError), self.cr.savepoint():
            wizard.action_register()

    def test_customer_and_confirmed_amount_cannot_change(self):
        payment = self._payment()
        with self.assertRaises(ValidationError), self.cr.savepoint():
            payment.amount = 30
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.repair.partner_id = self.env["res.partner"].create({"name": "Other"})

    def test_operator_permission_is_required(self):
        user = new_test_user(self.env, login="advance_no_permission", groups="account.group_account_invoice")
        with self.assertRaises(AccessError):
            self._wizard().with_user(user).repair_id._check_advance_access()

    def test_receipt_has_received_amount(self):
        self.partner.name = "Álex Muñoz"
        payment = self._payment()
        html, _ = self.env["ir.actions.report"]._render_qweb_html(
            "wexplay_repair_advances.advance_receipt", payment.ids,
        )
        self.assertIn(b"RESGUARDO DE ANTICIPO", html)
        self.assertIn(self.repair.name.encode(), html)
        self.assertIn("Álex Muñoz".encode(), html)
        self.assertIn(b'charset="utf-8"', html)

    def test_native_refund_clears_available(self):
        payment = self._payment()
        action = payment.action_refund_available_advance()
        method = self.journal.outbound_payment_method_line_ids[:1]
        method.payment_account_id = self.outstanding
        wizard = self.env["account.payment.register"].with_context(**action["context"]).create({
            "journal_id": self.journal.id, "payment_method_line_id": method.id,
        })
        self.assertEqual(wizard.payment_type, "outbound")
        refunds = wizard._create_payments()
        self.assertEqual(refunds.amount, 20)
        self.assertEqual(payment.wex_advance_available, 0)
        self.assertFalse(self.repair.sale_order_id)

    def test_draft_invoice_is_rejected(self):
        self._payment()
        invoice = self._invoice()
        invoice.button_draft()
        with self.assertRaises(ValidationError):
            invoice.action_apply_repair_advances()

    def test_multiple_advances_and_final_native_payment(self):
        first = self._payment(20)
        second = self._payment(10)
        invoice = self._invoice()
        invoice.action_apply_repair_advances()
        self.assertEqual(invoice.amount_residual, 50)
        wizard = self.env["account.payment.register"].with_context(
            active_model="account.move", active_ids=invoice.ids,
        ).create({"journal_id": self.journal.id, "payment_method_line_id": self.method.id})
        self.assertEqual(wizard.amount, 50)
        wizard.action_create_payments()
        self.assertEqual(invoice.amount_residual, 0)
        self.assertEqual(invoice.amount_total, 80)
        self.assertEqual(first.wex_advance_available + second.wex_advance_available, 0)
        self.assertNotEqual(self.repair.state, "delivered")

    def test_different_company_is_rejected(self):
        other = self.env["res.company"].create({"name": "Other advances company"})
        vals = self._wizard()._prepare_payment_values()
        vals["company_id"] = other.id
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.env["account.payment"].create(vals)

    def test_confirmed_payment_cannot_be_deleted(self):
        payment = self._payment()
        with self.assertRaises(ValidationError):
            payment.unlink()

    def test_other_customer_payment_is_rejected(self):
        vals = self._wizard()._prepare_payment_values()
        vals["partner_id"] = self.env["res.partner"].create({"name": "Other customer"}).id
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.env["account.payment"].create(vals)

    def test_full_advance_offers_delivery_without_delivering(self):
        if "action_offer_delivery_after_payment" not in dir(self.repair):
            self.skipTest("Optional delivery module is not installed")
        pending = self.env["stock.location"].create({"name": "Advance pending pickup", "usage": "internal"})
        delivered = self.env["stock.location"].create({"name": "Advance delivered", "usage": "internal"})
        self.env.company.write({
            "x_repair_state_location_done_id": pending.id,
            "x_repair_state_location_delivered_id": delivered.id,
        })
        self.repair.write({"state": "done", "product_location_src_id": pending.id})
        self._payment(80)
        invoice = self._invoice()
        action = invoice.action_apply_repair_advances()
        self.assertEqual(invoice.amount_residual, 0)
        self.assertEqual(action.get("res_model"), "wex.repair.delivery.wizard")
        self.assertEqual(self.repair.state, "done")

    def test_refund_of_applied_advance_is_rejected(self):
        payment = self._payment()
        self._invoice().action_apply_repair_advances()
        with self.assertRaises(ValidationError):
            payment.action_refund_available_advance()

    def test_notices_follow_available_balance_on_all_documents(self):
        self.assertFalse(self.repair.wex_advance_notice)
        payment = self._payment()
        invoice = self._invoice()
        order = self.repair.sale_order_id
        for document in (self.repair, order, invoice):
            self.assertTrue(document.wex_advance_notice)
            self.assertIn(self.repair.name, document.wex_advance_notice_detail)
        invoice.action_apply_repair_advances()
        for document in (self.repair, order, invoice):
            self.assertFalse(document.wex_advance_notice)
        invoice.line_ids.remove_move_reconcile()
        self.assertEqual(payment.wex_advance_available, 20)
        for document in (self.repair, order, invoice):
            self.assertTrue(document.wex_advance_notice)

    def test_multiple_sat_notice_has_breakdown(self):
        self._payment()
        invoice = self._invoice()
        order = self.repair.sale_order_id
        other = self.repair.copy({"sale_order_id": order.id})
        wizard = self._wizard(10)
        wizard.repair_id = other
        wizard.action_register()
        for document in (order, invoice):
            self.assertIn("VARIOS SAT", document.wex_advance_notice)
            self.assertIn(self.repair.name, document.wex_advance_notice_detail)
            self.assertIn(other.name, document.wex_advance_notice_detail)

    def test_refund_removes_notices(self):
        payment = self._payment()
        invoice = self._invoice()
        order = self.repair.sale_order_id
        self.assertTrue(invoice.wex_advance_notice)
        action = payment.action_refund_available_advance()
        method = self.journal.outbound_payment_method_line_ids[:1]
        method.payment_account_id = self.outstanding
        self.env["account.payment.register"].with_context(**action["context"]).create({
            "journal_id": self.journal.id, "payment_method_line_id": method.id,
        })._create_payments()
        for document in (self.repair, order, invoice):
            self.assertFalse(document.wex_advance_notice)

    def test_paid_invoice_does_not_warn_about_unused_excess(self):
        self._payment(100)
        invoice = self._invoice()
        invoice.action_apply_repair_advances()
        self.assertFalse(invoice.wex_advance_notice)
        self.assertTrue(self.repair.wex_advance_notice)
        self.assertTrue(self.repair.sale_order_id.wex_advance_notice)
