from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class MrwShippingPackage(models.Model):
    _name = "mrw.shipping.package"
    _description = "Bulto MRW"
    _order = "shipment_id, sequence, id"

    shipment_id = fields.Many2one(
        comodel_name="mrw.shipping.shipment",
        string="Envío",
        required=True,
        ondelete="cascade",
    )
    sequence = fields.Integer(string="Secuencia", required=True, default=1)
    weight = fields.Float(string="Peso", required=True, default=1.0)
    height = fields.Float(string="Alto", default=1.0)
    width = fields.Float(string="Ancho", default=1.0)
    length = fields.Float(string="Largo", default=1.0)
    dimension_code = fields.Char(string="Código dimensión", default="3")
    internal_reference = fields.Char(string="Referencia interna")
    notes = fields.Text(string="Observaciones")

    _sql_constraints = [
        (
            "shipment_sequence_uniq",
            "unique(shipment_id, sequence)",
            "Package sequence must be unique per shipment.",
        ),
    ]

    @api.constrains("weight", "height", "width", "length")
    def _check_positive_values(self):
        for package in self:
            if package.weight <= 0:
                raise ValidationError(_("Package weight must be greater than zero."))
            if package.height < 0 or package.width < 0 or package.length < 0:
                raise ValidationError(_("Package dimensions cannot be negative."))
