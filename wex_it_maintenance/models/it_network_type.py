from odoo import fields, models


class WexItNetworkType(models.Model):
    _name = "wex.it.network.type"
    _description = "Tipo de red IT Wex"
    _order = "sequence, name, id"

    name = fields.Char(required=True, translate=True)
    code = fields.Char(required=True, index=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one("res.company", index=True)
    description = fields.Text()

    _sql_constraints = [
        ("wex_it_network_type_code_company_uniq", "unique(code, company_id)", "El código debe ser único por compañía."),
    ]
