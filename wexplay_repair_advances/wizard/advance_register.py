from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class RepairAdvanceRegister(models.TransientModel):
    _name = "wex.repair.advance.register"
    _description = "Registrar anticipo SAT"

    repair_id = fields.Many2one("repair.order", string="SAT", required=True, readonly=True)
    company_id = fields.Many2one(related="repair_id.company_id")
    currency_id = fields.Many2one(related="company_id.currency_id")
    amount = fields.Monetary(string="Importe", required=True)
    journal_id = fields.Many2one("account.journal", string="Diario", required=True)
    allowed_journal_ids = fields.Many2many("account.journal", compute="_compute_allowed_journals")
    available_payment_method_line_ids = fields.One2many(
        related="journal_id.inbound_payment_method_line_ids",
    )
    payment_method_line_id = fields.Many2one(
        "account.payment.method.line", string="Medio de pago", required=True,
        compute="_compute_payment_method", store=True, readonly=False,
    )
    date = fields.Date(string="Fecha", default=fields.Date.context_today, required=True)
    memo = fields.Char(string="Concepto", required=True, default="Anticipo SAT")
    payment_id = fields.Many2one("account.payment", readonly=True, copy=False)

    @api.depends("company_id", "company_id.wex_advance_journal_ids", "company_id.currency_id")
    def _compute_allowed_journals(self):
        for wizard in self:
            wizard.allowed_journal_ids = wizard.company_id._get_advance_journals() if wizard.company_id else False

    @api.depends("journal_id")
    def _compute_payment_method(self):
        for wizard in self:
            wizard.payment_method_line_id = wizard.journal_id.inbound_payment_method_line_ids[:1]

    def _check_advance_values(self):
        self.repair_id._check_advance_access()
        if self.currency_id.compare_amounts(self.amount, 0) <= 0:
            raise ValidationError(_("El importe debe ser positivo."))
        if (self.journal_id not in self.company_id._get_advance_journals()
                or self.journal_id.company_id != self.company_id
                or self.journal_id.type not in ("cash", "bank", "credit")
                or (self.journal_id.currency_id and self.journal_id.currency_id != self.currency_id)):
            raise ValidationError(_("Selecciona un diario autorizado para anticipos SAT en esta compañía y moneda."))
        if self.payment_method_line_id not in self.journal_id.inbound_payment_method_line_ids:
            raise ValidationError(_("Selecciona un medio de cobro del diario."))

    def _prepare_payment_values(self):
        return {
            "wex_advance_repair_id": self.repair_id.id,
            "partner_id": self.repair_id.partner_id.commercial_partner_id.id,
            "company_id": self.company_id.id, "currency_id": self.currency_id.id,
            "payment_type": "inbound", "partner_type": "customer",
            "amount": self.amount, "date": self.date, "journal_id": self.journal_id.id,
            "payment_method_line_id": self.payment_method_line_id.id,
            "memo": "%s — %s" % (self.repair_id.name, self.memo),
        }

    def action_register(self):
        self.ensure_one()
        self.check_access("write")
        self.env.cr.execute("SELECT id FROM wex_repair_advance_register WHERE id = %s FOR UPDATE", [self.id])
        self.invalidate_recordset(["payment_id"])
        if self.payment_id:
            return self._get_payment_action()
        self._check_advance_values()
        payment = self.env["account.payment"].with_company(self.company_id).create(
            self._prepare_payment_values()
        )
        payment.action_post()
        if not payment.move_id or payment.move_id.state != "posted":
            raise ValidationError(_("El diario debe generar un asiento contabilizado. Revisa las cuentas de cobros pendientes."))
        self.payment_id = payment
        return self._get_payment_action()

    def _get_payment_action(self):
        return {"type": "ir.actions.act_window", "res_model": "account.payment",
                "res_id": self.payment_id.id, "view_mode": "form",
                "views": [(False, "form")], "target": "current"}
