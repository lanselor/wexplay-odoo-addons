from odoo import fields, models

from .device_constants import DEVICE_TYPE_SELECTION


class RepairDeviceCondition(models.Model):
    _name = "wex.repair.device.condition"
    _description = "Device reception condition"
    _order = "sequence, name, id"

    name = fields.Char(string="Desperfecto", required=True, translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    device_type = fields.Selection(
        DEVICE_TYPE_SELECTION,
        string="Tipo de dispositivo",
        help="Sin tipo: disponible para todos los dispositivos.",
    )
