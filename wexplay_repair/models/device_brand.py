from odoo import models, fields


class WexRepairBrand(models.Model):
    _name = "wex.repair.brand"  # Nombre del modelo
    _description = "Wexplay - Marcas de dispositivo"  # Descripción del modelo
    _order = "name"  # Orden por defecto al listar registros

    name = fields.Char(string="Marca", required=True, index=True)  # Nombre de la marca (obligatorio, indexado)
    active = fields.Boolean(default=True)  # Indica si la marca está activa
    _sql_constraints = [
        ("brand_name_uniq", "unique(name)", "Ya existe una marca con ese nombre."),  # Restricción SQL: el nombre de la marca debe ser único
    ]

