# -*- coding: utf-8 -*-

from odoo import api, models


class AccountMoveSendWizard(models.TransientModel):
    _inherit = "account.move.send.wizard"

    @api.depends("move_id")
    def _compute_display_pdf_report_id(self):
        available_templates_count = self.env["ir.actions.report"].search_count(
            [("is_invoice_report", "=", True)],
            limit=2,
        )
        for wizard in self:
            can_override_existing_pdf = (
                wizard.move_id._has_sat_repair_context()
                and bool(wizard.move_id.invoice_pdf_report_id)
            )
            wizard.display_pdf_report_id = bool(
                available_templates_count > 1
                and (not wizard.move_id.invoice_pdf_report_id or can_override_existing_pdf)
            )

    def _can_regenerate_selected_pdf_report(self):
        self.ensure_one()
        return bool(
            self.move_id
            and self.move_id._has_sat_repair_context()
            and self.move_id.invoice_pdf_report_id
            and self.pdf_report_id
        )

    def _reset_generated_invoice_pdf(self):
        self.ensure_one()
        invoice_pdf = self.move_id.invoice_pdf_report_id
        if not invoice_pdf:
            return

        if self.move_id.message_main_attachment_id == invoice_pdf:
            self.move_id.message_main_attachment_id = False

        invoice_pdf.unlink()
        self.move_id.invalidate_recordset(
            fnames=["invoice_pdf_report_id", "invoice_pdf_report_file"]
        )

    def action_send_and_print(self, allow_fallback_pdf=False):
        self.ensure_one()
        if self._can_regenerate_selected_pdf_report():
            self._reset_generated_invoice_pdf()
        return super().action_send_and_print(allow_fallback_pdf=allow_fallback_pdf)
