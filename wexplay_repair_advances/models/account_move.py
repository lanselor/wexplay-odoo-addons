from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AccountMove(models.Model):
    _inherit = "account.move"

    wex_advance_notice = fields.Char(compute="_compute_advance_notice", groups="account.group_account_invoice")
    wex_advance_notice_detail = fields.Text(compute="_compute_advance_notice", groups="account.group_account_invoice")

    @api.depends("state", "move_type", "amount_residual", "partner_id", "company_id",
                 "invoice_line_ids.sale_line_ids.order_id.repair_order_ids.wex_advance_notice",
                 "invoice_line_ids.sale_line_ids.order_id.repair_order_ids.wex_advance_notice_detail")
    @api.depends_context("lang")
    def _compute_advance_notice(self):
        for move in self:
            move.wex_advance_notice = move.wex_advance_notice_detail = False
            if move.move_type != "out_invoice" or move.state == "cancel":
                continue
            if move.state == "posted" and move.currency_id.is_zero(move.amount_residual):
                continue
            repairs = move._get_sat_repairs().filtered(
                lambda r: r.company_id == move.company_id
                and r.partner_id.commercial_partner_id == move.partner_id.commercial_partner_id
            )
            move.wex_advance_notice, move.wex_advance_notice_detail = repairs._get_advance_notice_values(invoice=True)

    def _get_eligible_repair_advances(self):
        self.ensure_one()
        repairs = self._get_sat_repairs()
        if len(repairs) != 1:
            raise ValidationError(_("La factura debe estar vinculada a un único SAT para aplicar anticipos."))
        repairs._check_advance_access()
        if (self.state != "posted" or self.move_type != "out_invoice"
                or self.partner_id.commercial_partner_id != repairs.partner_id.commercial_partner_id
                or self.company_id != repairs.company_id
                or self.currency_id != repairs.company_id.currency_id):
            raise ValidationError(_("Se requiere una factura contabilizada del cliente, compañía y moneda del SAT."))
        return repairs.wex_advance_payment_ids

    def action_apply_repair_advances(self):
        self.ensure_one()
        self.check_access("write")
        payments = self._get_eligible_repair_advances()
        payments._check_advance_operator()
        # Serializa las aplicaciones a esta factura y a los mismos pagos.
        self.env.cr.execute("SELECT id FROM account_move WHERE id = %s FOR UPDATE", [self.id])
        if payments:
            self.env.cr.execute(
                "SELECT id FROM account_payment WHERE id IN %s ORDER BY id FOR UPDATE",
                [tuple(payments.ids)],
            )
        self.env["account.move.line"].invalidate_model([
            "amount_residual", "amount_residual_currency", "reconciled",
        ])
        self.invalidate_recordset(["amount_residual"])
        for line in payments.sorted(lambda p: (p.date, p.id))._get_available_advance_lines():
            if self.currency_id.is_zero(self.amount_residual):
                break
            receivables = self.line_ids.filtered(
                lambda item: item.account_id == line.account_id and not item.reconciled
            )
            if not receivables:
                raise ValidationError(_("La cuenta a cobrar del anticipo no coincide con la de la factura."))
            (line + receivables).reconcile()
        repair = self._get_sat_repairs()
        delivery_action = getattr(repair, "action_offer_delivery_after_payment", None)
        if delivery_action and self.currency_id.is_zero(self.amount_residual):
            return delivery_action(self)
        return {"type": "ir.actions.client", "tag": "reload"}
