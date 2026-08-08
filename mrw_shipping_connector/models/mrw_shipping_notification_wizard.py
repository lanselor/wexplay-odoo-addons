# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from .mrw_shipping_notification import NOTIFICATION_EVENT_SELECTION


class MrwShippingNotificationWizard(models.TransientModel):
    _name = "mrw.shipping.notification.wizard"
    _description = "Enviar notificación MRW al cliente"

    shipment_id = fields.Many2one(
        comodel_name="mrw.shipping.shipment",
        string="Envío MRW",
        required=True,
        readonly=True,
    )
    event_type = fields.Selection(
        selection=NOTIFICATION_EVENT_SELECTION,
        string="Tipo de aviso",
        required=True,
    )
    recipient_email = fields.Char(string="Correo del cliente", required=True)
    template_id = fields.Many2one(
        comodel_name="mail.template",
        string="Plantilla",
        required=True,
        domain="[('model_id.model', '=', 'mrw.shipping.shipment')]",
    )
    attachment_id = fields.Many2one(
        comodel_name="ir.attachment",
        string="Adjunto",
        readonly=True,
    )
    attachment_required = fields.Boolean(compute="_compute_attachment_required")

    @api.depends("event_type")
    def _compute_attachment_required(self):
        for wizard in self:
            wizard.attachment_required = wizard.event_type == "pickup_label_ready"

    @api.onchange("shipment_id", "event_type")
    def _onchange_notification_context(self):
        for wizard in self:
            if not wizard.shipment_id:
                continue
            wizard.recipient_email = wizard.shipment_id.partner_id.email
            wizard.template_id = self.env["mrw.shipping.notification"]._get_template_for_event(
                wizard.shipment_id, wizard.event_type
            )
            wizard.attachment_id = self.env["mrw.shipping.notification"]._get_attachment_for_event(
                wizard.shipment_id, wizard.event_type
            )

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        shipment = self.env["mrw.shipping.shipment"].browse(
            values.get("shipment_id") or self.env.context.get("default_shipment_id")
        ).exists()
        if not shipment:
            return values
        event_type = values.get("event_type") or shipment._get_notification_default_event_type()
        notification = self.env["mrw.shipping.notification"]
        values.update(
            {
                "shipment_id": shipment.id,
                "event_type": event_type,
                "recipient_email": shipment.partner_id.email,
                "template_id": notification._get_template_for_event(shipment, event_type).id,
                "attachment_id": notification._get_attachment_for_event(shipment, event_type).id,
            }
        )
        return values

    def action_send(self):
        self.ensure_one()
        if not self.template_id:
            raise UserError(_("Selecciona una plantilla de correo."))
        notification = self.env["mrw.shipping.notification"].send_customer_notification(
            self.shipment_id,
            self.event_type,
            self.recipient_email,
            template=self.template_id,
        )
        if notification.state == "error":
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("No se pudo enviar el correo"),
                    "message": notification.error_message,
                    "type": "danger",
                    "sticky": True,
                },
            }
        return {"type": "ir.actions.act_window_close"}
