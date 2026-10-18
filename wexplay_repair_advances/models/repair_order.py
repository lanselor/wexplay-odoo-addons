from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError
from odoo.tools.misc import formatLang


class RepairOrder(models.Model):
    _inherit = "repair.order"

    wex_advance_payment_ids = fields.One2many(
        "account.payment", "wex_advance_repair_id", string="Anticipos", copy=False,
        groups="account.group_account_invoice",
    )
    wex_advance_allowed = fields.Boolean(compute="_compute_advance_allowed")
    wex_advance_notice = fields.Char(compute="_compute_advance_notice", groups="account.group_account_invoice")
    wex_advance_notice_detail = fields.Text(compute="_compute_advance_notice", groups="account.group_account_invoice")

    def _get_advance_notice_values(self, invoice=False):
        details = []
        for repair in self:
            amount = sum(repair.wex_advance_payment_ids.mapped("wex_advance_available"))
            currency = repair.company_id.currency_id
            if currency.compare_amounts(amount, 0) > 0:
                details.append((repair.name, formatLang(self.env, amount, currency_obj=currency)))
        if not details:
            return False, False
        detail = "\n".join("%s: %s" % item for item in details)
        if len(details) > 1:
            return _("ANTICIPOS EN VARIOS SAT · REVISAR"), detail
        label = _("ANTICIPO SAT POR APLICAR") if invoice else _("ANTICIPO DISPONIBLE")
        return "%s · %s" % (label, details[0][1]), detail

    @api.depends("name", "company_id.currency_id", "wex_advance_payment_ids.wex_advance_available")
    @api.depends_context("lang")
    def _compute_advance_notice(self):
        for repair in self:
            repair.wex_advance_notice, repair.wex_advance_notice_detail = repair._get_advance_notice_values()

    @api.depends_context("uid")
    def _compute_advance_allowed(self):
        allowed = (self.env.user.has_group("wexplay_repair_advances.group_advance_operator")
                   and self.env.user.has_group("account.group_account_invoice"))
        for repair in self:
            repair.wex_advance_allowed = allowed

    def _check_advance_access(self):
        self.ensure_one()
        self.check_access("write")
        if not self.wex_advance_allowed:
            raise AccessError(_("Se requieren permisos de anticipos SAT y facturación."))
        if not self.partner_id:
            raise ValidationError(_("Guarda el SAT con un cliente antes de registrar anticipos."))

    def action_register_advance(self):
        self._check_advance_access()
        return {
            "type": "ir.actions.act_window", "name": _("Registrar anticipo"),
            "res_model": "wex.repair.advance.register", "view_mode": "form",
            "views": [(False, "form")], "target": "new",
            "context": {"default_repair_id": self.id},
        }

    def action_open_advances(self):
        self._check_advance_access()
        return {
            "type": "ir.actions.act_window", "name": _("Anticipos SAT"),
            "res_model": "account.payment", "view_mode": "list,form",
            "views": [(False, "list"), (False, "form")],
            "domain": [("wex_advance_repair_id", "=", self.id)],
            "context": {"create": False},
        }

    def get_advance_summary(self):
        self._check_advance_access()
        payments = self.wex_advance_payment_ids.sorted(lambda p: (p.date, p.id), reverse=True)
        currency = self.company_id.currency_id
        return {
            "available": formatLang(self.env, sum(payments.mapped("wex_advance_available")), currency_obj=currency),
            "payments": [{
                "id": payment.id, "name": payment.display_name,
                "date": fields.Date.to_string(payment.date),
                "amount": formatLang(self.env, payment.amount, currency_obj=currency),
                "available": formatLang(self.env, payment.wex_advance_available, currency_obj=currency),
                "state": dict(payment._fields["state"]._description_selection(self.env))[payment.state],
            } for payment in payments],
        }

    def write(self, vals):
        if {"partner_id", "company_id"}.intersection(vals):
            for repair in self:
                changed = any(key in vals and vals[key] != repair[key].id
                              for key in ("partner_id", "company_id"))
                # La comprobación evita revelar importes a usuarios sin acceso contable.
                if changed and self.env["account.payment"].sudo().search_count([
                    ("wex_advance_repair_id", "=", repair.id),
                ]):
                    raise ValidationError(_("El SAT tiene anticipos. No se puede cambiar su cliente o compañía."))
        return super().write(vals)
