from odoo import models, fields
from .device_constants import DEVICE_TYPE_SELECTION

class WexRepairDeviceModel(models.Model):
    _name = "wex.repair.device_model"
    _description = "Wexplay - Modelos de dispositivo"
    _order = "device_type, brand_id, name"

    name = fields.Char(string="Modelo", required=True, index=True)

    device_type = fields.Selection(
        DEVICE_TYPE_SELECTION,
        string="Tipo de dispositivo",
        required=True,
        index=True,
    )

    brand_id = fields.Many2one(
        "wex.repair.brand",
        string="Marca",
        required=True,
        ondelete="restrict",
        index=True,
    )

    active = fields.Boolean(default=True)

    _sql_constraints = [
        (
            "model_unique_per_brand_type",
            "unique(name, brand_id, device_type)",
            "Ese modelo ya existe para esa marca y tipo de dispositivo.",
        ),
    ]
