from odoo import fields, models


class WexItMaintenanceTemplate(models.Model):
    _name = "wex.it.maintenance.template"
    _description = "Plantilla de mantenimiento IT Wex"
    _order = "name, id"

    name = fields.Char(required=True)
    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company, index=True)
    active = fields.Boolean(default=True)
    notes = fields.Text()
    line_ids = fields.One2many("wex.it.maintenance.template.line", "template_id", string="Líneas de lista de comprobación")


class WexItMaintenanceTemplateLine(models.Model):
    _name = "wex.it.maintenance.template.line"
    _description = "Línea de plantilla de mantenimiento IT Wex"
    _order = "sequence, id"

    sequence = fields.Integer(default=10)
    template_id = fields.Many2one("wex.it.maintenance.template", required=True, ondelete="cascade", index=True)
    name = fields.Char(required=True)
    description = fields.Text()
