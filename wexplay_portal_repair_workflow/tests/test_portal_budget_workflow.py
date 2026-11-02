# -*- coding: utf-8 -*-

from unittest.mock import patch

from odoo.exceptions import AccessError, UserError
from odoo.tests.common import TransactionCase


class TestPortalBudgetWorkflow(TransactionCase):
    def setUp(self):
        super().setUp()

        def run_in_test_transaction(repair, method_name, user=None, event_type=None,
                                    rejection_reason=None, **context_flags):
            # Los datos ficticios del test no están confirmados para otro cursor.
            backend = repair.sudo().with_context(**context_flags)
            backend._apply_portal_budget_workflow_action(
                method_name, user or repair.env.user, event_type, rejection_reason,
            )
            return True

        runner = patch.object(
            type(self.env['repair.order']), '_run_portal_budget_workflow_action',
            run_in_test_transaction,
        )
        runner.start()
        self.addCleanup(runner.stop)

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

    def test_rejection_posts_escaped_internal_note_and_prevents_repeat(self):
        repair, sale_order = self._create_budget_repair(self.company_partner)
        portal_repair = repair.with_user(self.portal_user)
        portal_repair.action_portal_reject_budget(
            rejection_reason='<script>alert(1)</script>\nDemasiado caro',
        )
        notes = repair.message_ids.filtered(
            lambda message: 'Presupuesto rechazado desde el portal' in (message.body or '')
        )
        self.assertEqual(len(notes), 1)
        self.assertEqual(notes.author_id, self.contact_partner)
        self.assertEqual(notes.subtype_id, self.env.ref('mail.mt_note'))
        self.assertIn('&lt;script&gt;', notes.body)
        self.assertNotIn('<script>', notes.body)
        self.assertIn('<br', notes.body)
        self.assertFalse(notes.notification_ids.filtered(lambda n: n.res_partner_id == self.contact_partner))
        with self.assertRaises(UserError):
            portal_repair.action_portal_reject_budget(rejection_reason='Segundo envío')
        self.assertEqual(sale_order.state, 'cancel')
        self.assertEqual(len(repair.message_ids.filtered(
            lambda m: 'Presupuesto rechazado desde el portal' in (m.body or '')
        )), 1)

    def test_rejection_without_reason_posts_fallback(self):
        repair, _sale_order = self._create_budget_repair(self.company_partner)
        repair.with_user(self.portal_user).action_portal_reject_budget(rejection_reason='  ')
        self.assertTrue(repair.message_ids.filtered(
            lambda m: 'El cliente no ha indicado un motivo.' in (m.body or '')
        ))

    def test_rejection_validates_reason_before_changing_budget(self):
        repair, sale_order = self._create_budget_repair(self.company_partner)
        for reason in ['x' * 4001, 42, ['texto']]:
            with self.assertRaises(UserError):
                repair.with_user(self.portal_user).action_portal_reject_budget(rejection_reason=reason)
        self.assertEqual(repair.x_budget_stage, 'waiting_customer')
        self.assertEqual(sale_order.state, 'draft')

    def test_foreign_rejection_is_denied(self):
        repair, sale_order = self._create_budget_repair(self.other_partner)
        with self.assertRaises(AccessError):
            repair.with_user(self.portal_user).action_portal_reject_budget(rejection_reason='No')
        self.assertEqual(sale_order.state, 'draft')

    def test_note_failure_rolls_back_rejection_and_event(self):
        repair, sale_order = self._create_budget_repair(self.company_partner)
        with self.assertRaises(UserError), self.cr.savepoint():
            with patch.object(type(repair), '_post_portal_budget_rejection', side_effect=UserError('Test')):
                repair.with_user(self.portal_user).action_portal_reject_budget(rejection_reason='Precio')
        self.assertEqual(sale_order.state, 'draft')
        self.assertEqual(repair.x_budget_stage, 'waiting_customer')
        self.assertFalse(self.env['wex.portal.repair.event'].search([
            ('repair_id', '=', repair.id), ('event_type', '=', 'budget_rejected'),
        ]))

    def test_portal_reject_after_reestimate_resets_budget_consistently(self):
        repair, sale_order = self._create_budget_repair(self.company_partner)

        repair.with_user(self.portal_user).action_portal_accept_budget(user=self.portal_user)
        repair.with_context(
            skip_budget_reestimate_quote_reset_confirm=True
        ).action_budget_reestimate()
        repair.action_budget_wait_customer()

        repair.with_user(self.portal_user).action_portal_reject_budget(user=self.portal_user)

        self.assertEqual(sale_order.state, "cancel")
        self.assertEqual(repair.x_budget_stage, "rejected")

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

    def test_portal_budget_summary_after_reject_uses_prepared_values(self):
        repair, _sale_order = self._create_budget_repair(self.company_partner)

        repair.with_user(self.portal_user).action_portal_reject_budget(user=self.portal_user)
        values = repair.with_user(self.portal_user)._get_portal_budget_summary_values()

        self.assertEqual(values["status"]["key"], "rejected")
        self.assertFalse(values["can_accept"])
        self.assertFalse(values["can_reject"])
        self.assertEqual(len(values["line_values"]), 1)

    def test_portal_budget_debug_values_include_state_snapshot(self):
        repair, sale_order = self._create_budget_repair(self.company_partner)

        debug_values = repair.with_user(self.portal_user)._get_portal_budget_debug_values(
            user=self.portal_user
        )

        self.assertEqual(debug_values["repair_id"], repair.id)
        self.assertEqual(debug_values["sale_order_state"], "draft")
        self.assertTrue(debug_values["can_portal_access"])
        self.assertTrue(debug_values["can_portal_review_budget"])
        self.assertTrue(debug_values["can_portal_reject_budget"])

    def test_native_quotation_is_hidden_while_budget_waits_for_customer(self):
        repair, sale_order = self._create_budget_repair(self.company_partner)

        quotation_values = repair.with_user(
            self.portal_user
        )._get_portal_related_quotation_values()

        self.assertEqual(len(quotation_values), 1)
        self.assertEqual(quotation_values[0]["name"], sale_order.name)
        self.assertFalse(quotation_values[0]["can_open_portal_url"])
        self.assertFalse(quotation_values[0]["portal_url"])

    def test_native_quotation_is_available_again_after_budget_accept(self):
        repair, sale_order = self._create_budget_repair(self.company_partner)

        repair.with_user(self.portal_user).action_portal_accept_budget(user=self.portal_user)
        quotation_values = repair.with_user(
            self.portal_user
        )._get_portal_related_quotation_values()

        self.assertEqual(len(quotation_values), 1)
        self.assertEqual(quotation_values[0]["name"], sale_order.name)
        self.assertTrue(quotation_values[0]["can_open_portal_url"])
        self.assertTrue(quotation_values[0]["portal_url"])

    def test_pending_budget_alert_values_only_include_waiting_customer_repairs(self):
        pending_repair, _sale_order = self._create_budget_repair(self.company_partner)
        accepted_repair, _sale_order = self._create_budget_repair(self.company_partner)
        accepted_repair.write({"x_budget_stage": "accepted"})
        foreign_pending_repair, _sale_order = self._create_budget_repair(self.other_partner)

        alert_values = self.env["repair.order"].with_user(
            self.portal_user
        )._get_portal_pending_budget_alert_values(user=self.portal_user)

        self.assertTrue(alert_values["show"])
        self.assertEqual(alert_values["total_count"], 1)
        self.assertEqual(len(alert_values["items"]), 1)
        self.assertEqual(alert_values["items"][0]["id"], pending_repair.id)
        self.assertEqual(
            alert_values["items"][0]["budget_url"],
            "/my/repairs/%s/budget" % pending_repair.id,
        )
        self.assertEqual(alert_values["list_url"], "/my/repairs?filterby=pending_budget")
        self.assertEqual(alert_values["reminder_interval_hours"], 5)
        self.assertIn(str(self.portal_user.id), alert_values["reminder_key"])
        self.assertNotEqual(alert_values["items"][0]["id"], accepted_repair.id)
        self.assertNotEqual(alert_values["items"][0]["id"], foreign_pending_repair.id)
