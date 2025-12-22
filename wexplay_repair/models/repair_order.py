from odoo import models, fields, api
from .device_constants import DEVICE_TYPE_SELECTION


class RepairOrder(models.Model):
    _inherit = "repair.order"

    x_device_type = fields.Selection(
        DEVICE_TYPE_SELECTION,
        string="Tipo de dispositivo",
    )

    # Datos del cliente (related)
    x_partner_mobile = fields.Char(
        string="Móvil",
        related="partner_id.mobile",
        readonly=True,
        store=False,
    )
    x_partner_phone = fields.Char(
        string="Teléfono",
        related="partner_id.phone",
        readonly=True,
        store=False,
    )

    # ✅ NUEVO: Marca/Modelo normalizados (catálogo)
    x_brand_id = fields.Many2one(
        "wex.repair.brand",
        string="Marca",
        compute="_compute_brand_from_model",
        store=True,
        readonly=True,
    )

    x_model_id = fields.Many2one(
        "wex.repair.device_model",
        string="Modelo",
        ondelete="restrict",
        domain="[('device_type', '=', x_device_type)]",
    )

    # Desbloqueo
    x_unlock_type = fields.Selection(
        [
            ("pin", "PIN"),
            ("pattern", "Patrón"),
            ("password", "Contraseña"),
            ("none", "Sin bloqueo"),
            ("unknown", "No indicado"),
        ],
        string="Tipo de desbloqueo",
    )

    x_unlock_code = fields.Char(string="Código / Contraseña")
    x_unlock_pattern = fields.Char(string="Patrón (descripción)")
    x_unlock_notes = fields.Text(string="Notas de desbloqueo")



    # Mantengo tus campos actuales por compatibilidad (opcional)
    x_brand = fields.Char(string="Marca (texto)")
    x_model = fields.Char(string="Modelo (texto)")
    x_imei = fields.Char(string="IMEI / Nº de serie")

    x_accessories = fields.Text(string="Accesorios entregados")
    x_reported_issue = fields.Text(string="Avería descrita por el cliente")
    x_internal_notes = fields.Text(string="Observaciones internas (técnico)")

    # --- Automatismos ---

    @api.onchange("x_device_type")
    def _onchange_x_device_type_reset_model_brand(self):
        """Si cambia el tipo, limpiamos modelo/marca para evitar inconsistencias."""
        for rec in self:
            rec.x_model_id = False
            rec.x_brand_id = False

    @api.onchange("x_model_id")
    def _onchange_x_model_id_set_brand(self):
        """Al escoger un modelo, rellenamos automáticamente la marca."""
        for rec in self:
            if rec.x_model_id:
                rec.x_brand_id = rec.x_model_id.brand_id
