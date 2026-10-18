from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    wex_advance_journal_ids = fields.Many2many(
        "account.journal", string="Diarios de anticipos SAT",
        domain="[('company_id', '=', id), ('type', 'in', ['bank', 'cash', 'credit'])]",
        help="Vacío: usar los diarios de banco, caja y tarjeta de crédito compatibles de la compañía. Selecciona diarios para restringirlos.",
    )

    def _get_advance_journals(self):
        self.ensure_one()
        domain = [
            ("company_id", "=", self.id), ("type", "in", ("bank", "cash", "credit")),
            ("inbound_payment_method_line_ids", "!=", False),
            "|", ("currency_id", "=", False), ("currency_id", "=", self.currency_id.id),
        ]
        if self.wex_advance_journal_ids:
            domain.append(("id", "in", self.wex_advance_journal_ids.ids))
        return self.env["account.journal"].search(domain)


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    wex_advance_journal_ids = fields.Many2many(
        related="company_id.wex_advance_journal_ids", readonly=False,
    )
