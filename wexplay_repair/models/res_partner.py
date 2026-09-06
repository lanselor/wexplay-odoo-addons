from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    x_is_professional_sat_customer = fields.Boolean(
        string="Cliente SAT profesional",
        help="Empresa de reparaciones que encarga trabajos SAT a Wexplay.",
        tracking=True,
    )
