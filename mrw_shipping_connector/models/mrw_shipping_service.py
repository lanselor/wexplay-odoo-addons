from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from .mrw_shipping_constants import SERVICE_TYPE_SELECTION


class MrwShippingService(models.Model):
    _name = "mrw.shipping.service"
    _description = "Servicio de envío MRW"
    _order = "sequence, name"

    name = fields.Char(string="Nombre", required=True, translate=True)
    code = fields.Char(string="Código", required=True)
    service_type = fields.Selection(
        selection=SERVICE_TYPE_SELECTION,
        string="Tipo de servicio",
        required=True,
        default="national",
    )
    active = fields.Boolean(string="Activo", default=True)
    sequence = fields.Integer(string="Secuencia", default=10)
    used_in_shipment = fields.Boolean(
        compute="_compute_used_in_shipment",
        string="Usado en envíos",
    )

    _sql_constraints = [
        (
            "code_service_type_uniq",
            "unique(code, service_type)",
            "The MRW service code must be unique per service type.",
        ),
    ]

    @api.depends("code")
    def _compute_used_in_shipment(self):
        Shipment = self.env["mrw.shipping.shipment"]
        Carrier = self.env["delivery.carrier"]
        for service in self:
            shipment = Shipment.search([("service_id", "=", service.id)], limit=1)
            carrier = Carrier.search([("mrw_service_id", "=", service.id)], limit=1)
            service.used_in_shipment = bool(service.id and (shipment or carrier))

    def write(self, vals):
        if "code" in vals:
            for service in self:
                if service.used_in_shipment and vals["code"] != service.code:
                    raise ValidationError(
                        _("You cannot change the code of a service already used.")
                    )
        return super().write(vals)
