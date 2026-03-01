# -*- coding: utf-8 -*-
# wexplay_repair/models/account_move.py

from odoo import api, fields, models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    has_sat_related = fields.Boolean(
        string="Has SAT related",
        compute="_compute_has_sat_related",
        store=False,
    )

    # ---------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------
    def _get_sale_orders_from_invoice(self):
        """Devuelve sale.order relacionados con la factura via líneas."""
        self.ensure_one()
        sale_orders = self.invoice_line_ids.sale_line_ids.order_id
        return sale_orders.filtered(lambda so: so)

    def _get_sat_repairs(self):
        """Devuelve repair.order vinculadas a los sale.order de esta factura."""
        self.ensure_one()
        sale_orders = self._get_sale_orders_from_invoice()
        if not sale_orders:
            return self.env["repair.order"]

        # Relación confirmada: repair.order.sale_order_id
        return self.env["repair.order"].search(
            [("sale_order_id", "in", sale_orders.ids)],
            order="id desc",
        )

    # ---------------------------------------------------------
    # QZ (headless) actions
    # ---------------------------------------------------------
    def action_qz_print_sat(self):
        """
        Imprime SAT (label 29x90 + ticket 80x170) por QZ (sin modal).
        Requiere client action JS:
          registry.category("actions").add("wexplay_sat_print.qz_print_sat", ...)
        """
        self.ensure_one()
        repair = self._get_sat_repairs()[:1]
        if not repair:
            raise UserError("No hay una orden de reparación SAT vinculada a esta factura.")

        return {
            "type": "ir.actions.client",
            "tag": "wexplay_sat_print.qz_print_sat",
            "params": {"resId": repair.id},
        }

    def action_qz_print_invoice_sat(self):
        """Imprime la Factura SAT (A4) por QZ (sin modal)."""
        self.ensure_one()
        return {
            "type": "ir.actions.client",
            "tag": "wexplay_sat_print.print_report_qz",
            "params": {
                "kind": "a4",
                "report_name": "wexplay_repair.report_invoice_sat",
                "res_id": self.id,
            },
        }

    def action_qz_print_invoice_standard(self):
        """Imprime la factura estándar (A4) por QZ (sin modal)."""
        self.ensure_one()
        return {
            "type": "ir.actions.client",
            "tag": "wexplay_sat_print.print_report_qz",
            "params": {
                "kind": "a4",
                "report_name": "account.report_invoice",  # ajusta si tu instancia usa otro report
                "res_id": self.id,
            },
        }

    # ---------------------------------------------------------
    # Computes / Standard PDF
    # ---------------------------------------------------------
    @api.depends("invoice_line_ids.sale_line_ids.order_id")
    def _compute_has_sat_related(self):
        Repair = self.env["repair.order"]
        for move in self:
            sale_orders = move.invoice_line_ids.sale_line_ids.order_id.filtered(lambda so: so)
            move.has_sat_related = bool(sale_orders) and bool(
                Repair.search_count([("sale_order_id", "in", sale_orders.ids)])
            )

    def action_print_sat_pdf(self):
        """Descarga el PDF del reporte SAT."""
        self.ensure_one()
        return self.env.ref("wexplay_repair.action_report_invoice_sat").report_action(self)