from odoo import fields, models

from odoo.addons.wexplay_repair.models.device_constants import DEVICE_TYPE_SELECTION


class WexTeardownTemplate(models.Model):
    _name = "wex.teardown.template"
    _description = "Plantilla de despiece"
    _order = "device_type, name"

    name = fields.Char(string="Nombre", required=True)
    device_type = fields.Selection(DEVICE_TYPE_SELECTION, string="Tipo de dispositivo", required=True, index=True)
    default_missing_part_number_confirmed = fields.Boolean(
        string="Marcar piezas sin part number por defecto",
        help="Si se activa, las lineas del despiece se cargan ya confirmadas como piezas que seguiran sin part number.",
    )
    line_ids = fields.One2many("wex.teardown.template.line", "template_id", string="Líneas")
    active = fields.Boolean(string="Activa", default=True)
