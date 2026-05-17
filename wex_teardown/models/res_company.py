from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    wex_teardown_default_location_id = fields.Many2one(
        "stock.location",
        string="Ubicación destino de despieces",
        domain="[('usage', '=', 'internal')]",
        check_company=True,
        help="Ubicación interna donde entran las piezas creadas desde despieces.",
    )
