from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    wex_return_location_id = fields.Many2one(
        related="company_id.wex_return_location_id", readonly=False,
        string="Ubicación de devoluciones",
    )
