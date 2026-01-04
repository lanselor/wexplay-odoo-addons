from odoo import models, fields
from .device_constants import DEVICE_TYPE_SELECTION

class WexRepairDeviceModel(models.Model):
    _name = "wex.repair.device_model"  # Nombre del modelo
    _description = "Wexplay - Modelos de dispositivo"  # Descripción del modelo
    _order = "device_type, brand_id, name"  # Orden por defecto al listar registros

    name = fields.Char(string="Modelo", required=True, index=True)  # Nombre del modelo (obligatorio, indexado)
    device_type = fields.Selection(
        DEVICE_TYPE_SELECTION,
        string="Tipo de dispositivo",
        required=True,
        index=True,
    )

    brand_id = fields.Many2one(
        "wex.repair.brand",  # Relación con el modelo de marca
        string="Marca",
        required=True,
        ondelete="restrict",  # No permite borrar la marca si está en uso en un modelo
        index=True,
    )

    active = fields.Boolean(default=True)  # Indica si el modelo está activo

    _sql_constraints = [
        (
            "model_unique_per_brand_type",
            "unique(name, brand_id, device_type)",
            "Ese modelo ya existe para esa marca y tipo de dispositivo.",  # Restricción SQL: el modelo debe ser único por marca y tipo de dispositivo
        ),
    ]

