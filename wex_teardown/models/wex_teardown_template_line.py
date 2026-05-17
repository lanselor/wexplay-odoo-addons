from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class WexTeardownTemplateLine(models.Model):
    _name = "wex.teardown.template.line"
    _description = "Linea de plantilla de despiece"
    _order = "sequence, id"

    template_id = fields.Many2one(
        "wex.teardown.template",
        string="Plantilla",
        required=True,
        ondelete="cascade",
    )
    device_type = fields.Selection(
        related="template_id.device_type",
        string="Tipo de dispositivo",
        store=True,
        readonly=True,
    )
    sequence = fields.Integer(string="Secuencia", default=10)
    component_type_id = fields.Many2one(
        "wex.teardown.component.type",
        string="Componente",
        required=True,
        domain="[('device_type', '=', device_type)]",
        ondelete="restrict",
    )
    default_quantity = fields.Float(string="Cantidad", default=1.0, required=True)
    required = fields.Boolean(string="Requerida", default=True)

    @api.constrains("template_id", "component_type_id")
    def _check_component_device_type(self):
        for rec in self:
            if (
                rec.template_id
                and rec.component_type_id
                and rec.template_id.device_type != rec.component_type_id.device_type
            ):
                raise ValidationError(
                    _("El componente debe pertenecer al mismo tipo de dispositivo que la plantilla.")
                )
