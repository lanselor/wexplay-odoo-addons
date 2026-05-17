from odoo import _, fields, models
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = "stock.picking"

    mrw_shipment_id = fields.Many2one(
        comodel_name="mrw.shipping.shipment",
        string="Envío MRW",
        copy=False,
        readonly=True,
    )
    mrw_state = fields.Selection(
        related="mrw_shipment_id.state",
        string="Estado MRW",
        readonly=True,
    )
    mrw_request_number = fields.Char(
        related="mrw_shipment_id.mrw_request_number",
        string="Número de solicitud MRW",
        readonly=True,
    )
    mrw_effective_shipping_date = fields.Date(
        related="mrw_shipment_id.mrw_effective_shipping_date",
        string="Fecha efectiva MRW",
        readonly=True,
    )
    mrw_label_attachment_id = fields.Many2one(
        related="mrw_shipment_id.label_attachment_id",
        string="Etiqueta MRW",
        readonly=True,
    )
    mrw_last_error = fields.Text(
        related="mrw_shipment_id.last_error",
        string="Último error MRW",
        readonly=True,
    )
    mrw_log_count = fields.Integer(
        related="mrw_shipment_id.log_count",
        string="Logs MRW",
        readonly=True,
    )

    def action_open_mrw_shipment(self):
        self.ensure_one()
        if not self.mrw_shipment_id:
            raise UserError(_("No linked MRW shipment was found."))
        return {
            "type": "ir.actions.act_window",
            "name": _("Envío MRW"),
            "res_model": "mrw.shipping.shipment",
            "res_id": self.mrw_shipment_id.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_open_mrw_tracking(self):
        self.ensure_one()
        if self.carrier_id.delivery_type != "mrw":
            raise UserError(_("The delivery carrier is not configured as MRW."))
        tracking_url = self.carrier_tracking_url
        if not tracking_url and self.carrier_tracking_ref:
            tracking_url = self.carrier_id.get_tracking_link(self)
        if not tracking_url:
            raise UserError(_("No MRW tracking link is available yet."))
        return {
            "type": "ir.actions.act_url",
            "url": tracking_url,
            "target": "new",
        }

    def action_get_mrw_label(self):
        self.ensure_one()
        if not self.mrw_shipment_id:
            raise UserError(_("No linked MRW shipment was found."))
        result = self.mrw_shipment_id.action_get_mrw_label()
        if self.mrw_label_attachment_id:
            self.message_post(
                body=_("MRW label %s is available.")
                % self.mrw_label_attachment_id.name
            )
        return result

    def action_open_mrw_label(self):
        self.ensure_one()
        if not self.mrw_label_attachment_id:
            raise UserError(_("No MRW label attachment is available."))
        return {
            "type": "ir.actions.act_window",
            "name": _("Etiqueta MRW"),
            "res_model": "ir.attachment",
            "res_id": self.mrw_label_attachment_id.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_download_mrw_label(self):
        self.ensure_one()
        if not self.mrw_label_attachment_id:
            raise UserError(_("No MRW label attachment is available."))
        return {
            "type": "ir.actions.act_url",
            "url": "/web/content/%s?download=true" % self.mrw_label_attachment_id.id,
            "target": "self",
        }

    def action_request_mrw_cancellation(self):
        self.ensure_one()
        if not self.mrw_shipment_id:
            raise UserError(_("No linked MRW shipment was found."))
        if self.carrier_id.delivery_type != "mrw":
            raise UserError(_("The delivery carrier is not configured as MRW."))
        self.cancel_shipment()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Cancelación MRW solicitada."),
                "message": _("MRW ha confirmado la cancelación del envío."),
                "type": "success",
                "sticky": False,
            },
        }

    def action_preview_mrw_cancellation(self):
        self.ensure_one()
        if not self.mrw_shipment_id:
            raise UserError(_("No linked MRW shipment was found."))
        return self.mrw_shipment_id.action_preview_cancel_request()

    def action_open_mrw_logs(self):
        self.ensure_one()
        if not self.mrw_shipment_id:
            raise UserError(_("No linked MRW shipment was found."))
        return self.mrw_shipment_id.action_open_logs()
