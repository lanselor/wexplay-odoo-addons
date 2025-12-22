from odoo import models, fields


class WexRepairBrand(models.Model):
    _name = "wex.repair.brand"
    _description = "Wexplay - Marcas de dispositivo"
    _order = "name"

    name = fields.Char(string="Marca", required=True, index=True)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ("brand_name_uniq", "unique(name)", "Ya existe una marca con ese nombre."),
    ]
