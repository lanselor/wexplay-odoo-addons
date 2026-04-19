# -*- coding: utf-8 -*-
# wexplay_repair/models/account_move.py

from odoo import _, api, fields, models
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
        """Return sale orders linked to the invoice through invoice lines."""
        self.ensure_one()
        return self.invoice_line_ids.sale_line_ids.order_id.filtered(lambda order: order)

    def _get_sat_repairs(self):
        """Return SAT repair orders linked to the invoice sale orders."""
        self.ensure_one()
        sale_orders = self._get_sale_orders_from_invoice()
        if not sale_orders:
            return self.env["repair.order"]

        return self.env["repair.order"].search(
            [("sale_order_id", "in", sale_orders.ids)],
            order="id desc",
        )

    def _get_primary_sat_repair(self):
        self.ensure_one()
        return self._get_sat_repairs()[:1]

    def _get_sat_invoice_report_sale_orders(self):
        self.ensure_one()
        return self._get_sale_orders_from_invoice()

    def _get_sat_invoice_report_sale_order_names(self):
        self.ensure_one()
        sale_orders = self._get_sat_invoice_report_sale_orders()
        return ", ".join(sale_orders.mapped("name")) or "-"

    def _get_sat_invoice_report_repair(self):
        self.ensure_one()
        return self._get_primary_sat_repair()

    def _get_sat_invoice_report_spare_moves(self):
        self.ensure_one()
        repair = self._get_sat_invoice_report_repair()
        if not repair:
            return self.env["stock.move"]
        return repair.move_ids.filtered(
            lambda move: move.repair_line_type == "add" and move.state != "cancel"
        )

    def _has_sat_repair_context(self):
        self.ensure_one()
        return bool(self._get_primary_sat_repair())

    def _get_sat_invoice_report(self):
        self.ensure_one()
        return self.env.ref("wexplay_repair.action_report_invoice_sat")

    def _should_use_sat_invoice_report(self):
        self.ensure_one()
        return self._has_sat_repair_context()

    def _should_use_sat_mail_template(self):
        self.ensure_one()
        return self.move_type == "out_invoice" and self._has_sat_repair_context()

    def _get_sat_mail_subject_suffix(self):
        self.ensure_one()
        repair = self._get_primary_sat_repair()
        if not repair:
            return ""

        parts = [repair.name or _("Parte SAT")]
        if repair.product_id:
            parts.append(repair.product_id.display_name)
        return " | ".join(filter(None, parts))

    def _prepare_qz_print_action(self, tag, params):
        self.ensure_one()
        return {
            "type": "ir.actions.client",
            "tag": tag,
            "params": params,
        }

    def _prepare_qz_report_action(self, report_name, kind="a4", document_code=False):
        self.ensure_one()
        return self._prepare_qz_print_action(
            "wexplay_sat_print.print_report_qz",
            {
                "kind": kind,
                "report_name": report_name,
                "res_id": self.id,
                "document_code": document_code or False,
            },
        )

    # ---------------------------------------------------------
    # QZ (headless) actions
    # ---------------------------------------------------------
    def action_qz_print_sat(self):
        """Print SAT label/ticket directly via QZ."""
        self.ensure_one()
        repair = self._get_primary_sat_repair()
        if not repair:
            raise UserError(_("No hay una orden de reparacion SAT vinculada a esta factura."))

        return self._prepare_qz_print_action(
            "wexplay_sat_print.qz_print_sat",
            {"resId": repair.id},
        )

    def action_qz_print_invoice_sat(self):
        """Print the SAT invoice via QZ."""
        self.ensure_one()
        return self._prepare_qz_report_action("wexplay_repair.report_invoice_sat", document_code="sat_a4")

    def action_qz_print_invoice_standard(self):
        """Print the standard invoice via QZ."""
        self.ensure_one()
        return self._prepare_qz_report_action("account.report_invoice")

    # ---------------------------------------------------------
    # Computes / Standard PDF
    # ---------------------------------------------------------
    @api.depends("invoice_line_ids.sale_line_ids.order_id")
    def _compute_has_sat_related(self):
        for move in self:
            move.has_sat_related = bool(move._get_sat_repairs())

    def action_print_sat_pdf(self):
        """Download the SAT PDF report."""
        self.ensure_one()
        return self.env.ref("wexplay_repair.action_report_invoice_sat").report_action(self)

    def _get_mail_template(self):
        self.ensure_one()
        if self._should_use_sat_mail_template():
            return self.env.ref("wexplay_repair.email_template_edi_invoice_sat_v2")
        return super()._get_mail_template()
