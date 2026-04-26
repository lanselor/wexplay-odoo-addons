from odoo import fields, models


class WexItSoftwareType(models.Model):
    _name = "wex.it.software.type"
    _description = "Tipo de software/licencia IT Wex"
    _order = "sequence, name, id"

    name = fields.Char(required=True, translate=True)
    code = fields.Char(required=True, index=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one("res.company", index=True)
    default_renewal_required = fields.Boolean(string="Renovación habitual")
    default_managed_by_wex = fields.Boolean(string="Gestionado por Wexplay por defecto")
    description = fields.Text()

    _sql_constraints = [
        ("wex_it_software_type_code_company_uniq", "unique(code, company_id)", "El código debe ser único por compañía."),
    ]
