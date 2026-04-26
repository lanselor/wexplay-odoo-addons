from odoo import fields, models


class WexItServiceType(models.Model):
    _name = "wex.it.service.type"
    _description = "Tipo de servicio IT Wex"
    _order = "sequence, name, id"

    name = fields.Char(required=True, translate=True)
    code = fields.Char(required=True, index=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one("res.company", index=True)
    default_template_id = fields.Many2one("wex.it.maintenance.template", string="Plantilla sugerida")
    description = fields.Text()

    _sql_constraints = [
        ("wex_it_service_type_code_company_uniq", "unique(code, company_id)", "El código debe ser único por compañía."),
    ]
