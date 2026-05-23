from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    wex_accounting_portal_enabled = fields.Boolean(
        string="Acceso portal contable Wexplay",
        default=False,
    )

    def _is_wex_accounting_portal_enabled_partner(self):
        self.ensure_one()
        return bool(self.wex_accounting_portal_enabled)
