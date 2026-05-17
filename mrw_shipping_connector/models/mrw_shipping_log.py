from odoo import fields, models

from .mrw_shipping_constants import LOG_OPERATION_SELECTION, LOG_STATUS_SELECTION


class MrwShippingLog(models.Model):
    _name = "mrw.shipping.log"
    _description = "Log técnico de envío MRW"
    _order = "create_date desc, id desc"

    shipment_id = fields.Many2one(
        comodel_name="mrw.shipping.shipment",
        string="Envío",
        readonly=True,
        ondelete="set null",
    )
    config_id = fields.Many2one(
        comodel_name="mrw.shipping.config",
        string="Configuración",
        readonly=True,
        ondelete="set null",
    )
    operation = fields.Selection(
        selection=LOG_OPERATION_SELECTION,
        string="Operación",
        required=True,
        readonly=True,
    )
    status = fields.Selection(
        selection=LOG_STATUS_SELECTION,
        string="Estado",
        required=True,
        readonly=True,
    )
    request_raw = fields.Text(string="Petición", readonly=True)
    response_raw = fields.Text(string="Respuesta", readonly=True)
    mrw_status = fields.Char(string="Estado MRW", readonly=True)
    mrw_message = fields.Text(string="Mensaje MRW", readonly=True)
    error_message = fields.Text(string="Error", readonly=True)
    duration_ms = fields.Integer(string="Duración ms", readonly=True)
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Usuario",
        required=True,
        readonly=True,
        default=lambda self: self.env.user,
    )
