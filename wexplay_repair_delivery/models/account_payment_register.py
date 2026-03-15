# -*- coding: utf-8 -*-
import logging

from odoo import models, _

_logger = logging.getLogger(__name__)


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    def _wex_get_invoices_from_context(self):
        """Obtener facturas origen desde el contexto del wizard de pago."""
        active_model = self.env.context.get("active_model")
        active_ids = self.env.context.get("active_ids", [])

        _logger.warning(
            "WEX DELIVERY DEBUG | _wex_get_invoices_from_context | active_model=%s active_ids=%s",
            active_model, active_ids
        )

        if not active_ids:
            return self.env["account.move"]

        # Caso 1: el wizard viene desde la propia factura
        if active_model == "account.move":
            invoices = self.env["account.move"].browse(active_ids).exists()
            _logger.warning(
                "WEX DELIVERY DEBUG | invoices from account.move ids=%s",
                invoices.ids
            )
            return invoices

        # Caso 2: el wizard viene desde líneas contables
        if active_model == "account.move.line":
            lines = self.env["account.move.line"].browse(active_ids).exists()
            invoices = lines.mapped("move_id").exists()
            _logger.warning(
                "WEX DELIVERY DEBUG | invoices from account.move.line ids=%s names=%s",
                invoices.ids,
                invoices.mapped("name"),
            )
            return invoices

        _logger.warning(
            "WEX DELIVERY DEBUG | unsupported active_model=%s",
            active_model
        )
        return self.env["account.move"]

    def action_create_payments(self):
        _logger.warning("WEX DELIVERY DEBUG | START action_create_payments")

        # 1) Guardamos referencia a facturas antes del pago
        invoices_before = self._wex_get_invoices_from_context()

        _logger.warning(
            "WEX DELIVERY DEBUG | invoices_before ids=%s move_types=%s payment_states=%s",
            invoices_before.ids,
            invoices_before.mapped("move_type"),
            invoices_before.mapped("payment_state"),
        )

        # 2) Ejecutar lógica estándar de Odoo
        result = super().action_create_payments()

        _logger.warning("WEX DELIVERY DEBUG | super() finished | result=%s", result)

        # 3) Filtrar solo facturas de cliente
        invoices_before = invoices_before.filtered(lambda m: m.move_type == "out_invoice")

        _logger.warning(
            "WEX DELIVERY DEBUG | customer invoices filtered ids=%s names=%s",
            invoices_before.ids,
            invoices_before.mapped("name"),
        )

        if len(invoices_before) != 1:
            _logger.warning(
                "WEX DELIVERY DEBUG | EXIT len(invoices_before) != 1 | len=%s",
                len(invoices_before)
            )
            return result

        # 4) Recargar factura DESPUÉS del pago
        invoice = self.env["account.move"].browse(invoices_before.id).exists()

        _logger.warning(
            "WEX DELIVERY DEBUG | invoice reloaded id=%s exists=%s payment_state=%s state=%s name=%s",
            invoice.id if invoice else False,
            bool(invoice),
            invoice.payment_state if invoice else False,
            invoice.state if invoice else False,
            invoice.name if invoice else False,
        )

        if not invoice:
            _logger.warning("WEX DELIVERY DEBUG | EXIT invoice not found after reload")
            return result

        # 5) Comprobar después del pago
        if invoice.payment_state != "paid":
            _logger.warning(
                "WEX DELIVERY DEBUG | EXIT invoice not paid | payment_state=%s",
                invoice.payment_state
            )
            return result

        # 6) Buscar SAT relacionado
        repairs = invoice.wex_get_sat_repairs()

        _logger.warning(
            "WEX DELIVERY DEBUG | repairs found ids=%s names=%s states=%s",
            repairs.ids,
            repairs.mapped("name"),
            repairs.mapped("state"),
        )

        if not repairs:
            _logger.warning("WEX DELIVERY DEBUG | EXIT no SAT repairs linked to invoice")
            return result

        repair = repairs[:1]

        _logger.warning(
            "WEX DELIVERY DEBUG | selected repair id=%s name=%s state=%s",
            repair.id,
            repair.name,
            repair.state,
        )

        # 7) Si ya estaba entregada
        if repair.state == "delivered":
            _logger.warning(
                "WEX DELIVERY DEBUG | repair already delivered | repair=%s",
                repair.name
            )
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Orden ya entregada"),
                    "message": _(
                        "La orden de trabajo %s ya estaba marcada como entregada."
                    ) % (repair.name or ""),
                    "type": "success",
                    "sticky": False,
                },
            }

        # 8) Abrir wizard
        _logger.warning(
            "WEX DELIVERY DEBUG | OPEN wizard for invoice=%s repair=%s",
            invoice.name, repair.name
        )

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