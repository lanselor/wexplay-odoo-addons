# -*- coding: utf-8 -*-
import logging

from odoo import _, models

_logger = logging.getLogger(__name__)


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    def _get_active_invoices_from_context(self):
        """Return source invoices from the payment wizard context."""
        active_model = self.env.context.get("active_model")
        active_ids = self.env.context.get("active_ids", [])

        if not active_ids:
            return self.env["account.move"]

        if active_model == "account.move":
            return self.env["account.move"].browse(active_ids).exists()

        if active_model == "account.move.line":
            lines = self.env["account.move.line"].browse(active_ids).exists()
            return lines.mapped("move_id").exists()

        _logger.debug(
            "Skipping delivery check for unsupported payment wizard model: %s",
            active_model,
        )
        return self.env["account.move"]

    def _get_single_customer_invoice(self, invoices):
        customer_invoices = invoices.filtered(lambda move: move.move_type == "out_invoice")
        if len(customer_invoices) != 1:
            _logger.debug(
                "Skipping delivery wizard because %s customer invoices were found.",
                len(customer_invoices),
            )
            return self.env["account.move"]
        return customer_invoices[:1]

    def _reload_invoice_after_payment(self, invoice):
        return self.env["account.move"].browse(invoice.id).exists()

    def _get_delivery_repair_from_invoice(self, invoice):
        repairs = invoice.wex_get_sat_repairs()
        if not repairs:
            _logger.debug(
                "Skipping delivery wizard because invoice %s has no SAT repairs.",
                invoice.display_name,
            )
            return self.env["repair.order"]

        return repairs[:1]

    def _build_already_delivered_notification(self, repair):
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Orden ya entregada"),
                "message": _(
                    "La orden de trabajo %s ya estaba marcada como entregada."
                )
                % (repair.name or ""),
                "type": "success",
                "sticky": False,
            },
        }

    def _prepare_delivery_wizard_action(self, invoice, repair):
        return {
            "type": "ir.actions.act_window",
            "res_model": "wex.repair.delivery.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_repair_id": repair.id,
                "default_invoice_id": invoice.id,
            },
        }

    def action_create_payments(self):
        invoices_before = self._get_active_invoices_from_context()
        result = super().action_create_payments()

        invoice_before = self._get_single_customer_invoice(invoices_before)
        if not invoice_before:
            return result

        invoice = self._reload_invoice_after_payment(invoice_before)
        if not invoice:
            _logger.debug(
                "Skipping delivery wizard because invoice %s was not found after payment.",
                invoice_before.id,
            )
            return result

        if invoice.payment_state != "paid":
            _logger.debug(
                "Skipping delivery wizard because invoice %s is still in payment_state=%s.",
                invoice.display_name,
                invoice.payment_state,
            )
            return result

        repair = self._get_delivery_repair_from_invoice(invoice)
        if not repair:
            return result

        if repair.state == "delivered":
            return self._build_already_delivered_notification(repair)

        return self._prepare_delivery_wizard_action(invoice, repair)
