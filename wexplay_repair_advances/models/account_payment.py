from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError


class AccountPayment(models.Model):
    _inherit = "account.payment"

    wex_advance_repair_id = fields.Many2one(
        "repair.order", string="SAT del anticipo", index=True, copy=False,
        check_company=True, ondelete="restrict",
    )
    wex_advance_available = fields.Monetary(
        string="Disponible", compute="_compute_advance_available",
    )

    def _check_advance_operator(self):
        if not self.env.user.has_group("wexplay_repair_advances.group_advance_operator"):
            raise AccessError(_("No tienes permiso para gestionar anticipos SAT."))
        self.check_access("write")

    @api.model_create_multi
    def create(self, vals_list):
        if any(vals.get("wex_advance_repair_id") for vals in vals_list):
            self._check_advance_operator()
        return super().create(vals_list)

    def _get_available_advance_lines(self):
        return self.filtered(
            lambda p: p.wex_advance_repair_id and p.payment_type == "inbound"
            and p.state in ("in_process", "paid") and p.move_id.state == "posted"
        ).move_id.line_ids.filtered(
            lambda line: line.account_id.account_type == "asset_receivable"
            and not line.reconciled and line.amount_residual_currency < 0
        )

    @api.depends("wex_advance_repair_id", "payment_type", "state", "move_id.state", "move_id.line_ids.amount_residual_currency",
                 "move_id.line_ids.reconciled")
    def _compute_advance_available(self):
        for payment in self:
            payment.wex_advance_available = -sum(
                payment._get_available_advance_lines().mapped("amount_residual_currency")
            )

    @api.constrains("wex_advance_repair_id", "partner_id", "company_id",
                    "currency_id", "payment_type", "partner_type", "amount")
    def _check_advance_consistency(self):
        for payment in self.filtered("wex_advance_repair_id"):
            repair = payment.wex_advance_repair_id
            if (payment.company_id != repair.company_id
                    or payment.partner_id != repair.partner_id.commercial_partner_id
                    or payment.currency_id != repair.company_id.currency_id
                    or payment.payment_type != "inbound" or payment.partner_type != "customer"
                    or payment.amount <= 0):
                raise ValidationError(_("El anticipo debe ser un cobro positivo del cliente, compañía y moneda del SAT."))

    def write(self, vals):
        if vals.get("wex_advance_repair_id"):
            self._check_advance_operator()
        protected = {"wex_advance_repair_id", "partner_id", "company_id", "currency_id",
                     "amount", "journal_id", "payment_type", "partner_type", "date"}
        if protected.intersection(vals) and self.filtered(
            lambda p: p.wex_advance_repair_id and p.state != "draft"
        ):
            raise ValidationError(_("No se pueden cambiar los datos de un anticipo confirmado. Usa el circuito contable de corrección."))
        return super().write(vals)

    def unlink(self):
        if self.filtered(lambda p: p.wex_advance_repair_id and p.state != "draft"):
            raise ValidationError(_("No se puede eliminar un anticipo confirmado. Conserva su trazabilidad contable."))
        return super().unlink()

    def action_print_advance_receipt(self):
        self.ensure_one()
        self.check_access("read")
        self.wex_advance_repair_id.check_access("read")
        if not self.wex_advance_repair_id or self.state not in ("in_process", "paid"):
            raise ValidationError(_("Solo se puede imprimir un anticipo confirmado."))
        return self.env.ref("wexplay_repair_advances.action_advance_receipt").report_action(self)

    def action_refund_available_advance(self):
        self.ensure_one()
        self._check_advance_operator()
        if not self.env.user.has_group("account.group_account_manager"):
            raise AccessError(_("La devolución requiere permisos de responsable contable."))
        lines = self._get_available_advance_lines()
        if not lines:
            raise ValidationError(_("No hay importe disponible. Si ya está aplicado, revisa primero la factura y su corrección."))
        return {
            "type": "ir.actions.act_window", "name": _("Devolver anticipo disponible"),
            "res_model": "account.payment.register", "view_mode": "form",
            "views": [(False, "form")], "target": "new",
            "context": {"active_model": "account.move.line", "active_ids": lines.ids},
        }

