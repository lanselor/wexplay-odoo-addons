# -*- coding: utf-8 -*-

import logging

from odoo import _, fields, models
from odoo.exceptions import UserError


_logger = logging.getLogger(__name__)


NOTIFICATION_EVENT_SELECTION = [
    ("shipment_created", "Envío MRW creado"),
    ("pickup_label_ready", "Etiqueta de recogida disponible"),
]


class MrwShippingNotification(models.Model):
    _name = "mrw.shipping.notification"
    _description = "Notificación al cliente MRW"
    _order = "create_date desc, id desc"

    shipment_id = fields.Many2one(
        comodel_name="mrw.shipping.shipment",
        string="Envío MRW",
        required=True,
        index=True,
        ondelete="cascade",
    )
    company_id = fields.Many2one(related="shipment_id.company_id", store=True)
    event_type = fields.Selection(
        selection=NOTIFICATION_EVENT_SELECTION,
        string="Tipo de aviso",
        required=True,
    )
    recipient_email = fields.Char(string="Destinatario", required=True)
    template_id = fields.Many2one(
        comodel_name="mail.template",
        string="Plantilla",
        required=True,
        ondelete="restrict",
    )
    attachment_id = fields.Many2one(
        comodel_name="ir.attachment",
        string="Adjunto",
        readonly=True,
        ondelete="set null",
    )
    mail_id = fields.Many2one(
        comodel_name="mail.mail",
        string="Correo",
        readonly=True,
        ondelete="set null",
    )
    state = fields.Selection(
        selection=[("sent", "Enviado"), ("error", "Error")],
        string="Resultado",
        required=True,
        readonly=True,
    )
    sent_at = fields.Datetime(string="Fecha de envío", readonly=True)
    sent_by_id = fields.Many2one(
        comodel_name="res.users",
        string="Enviado por",
        readonly=True,
    )
    error_message = fields.Text(string="Error", readonly=True)

    def _get_template_for_event(self, shipment, event_type):
        config = shipment.config_id
        if event_type == "shipment_created":
            return (
                config.notification_shipment_created_template_id
                or self.env.ref(
                    "mrw_shipping_connector.mail_template_mrw_shipment_created",
                    raise_if_not_found=False,
                )
            )
        if event_type == "pickup_label_ready":
            return (
                config.notification_pickup_label_template_id
                or self.env.ref(
                    "mrw_shipping_connector.mail_template_mrw_pickup_label_ready",
                    raise_if_not_found=False,
                )
            )
        return self.env["mail.template"]

    def _get_attachment_for_event(self, shipment, event_type):
        if event_type != "pickup_label_ready":
            return self.env["ir.attachment"]
        if shipment.movement_type != "pickup":
            raise UserError(_("La etiqueta solo se puede enviar en una recogida de cliente."))
        if not shipment.label_attachment_id:
            raise UserError(_("Primero debes obtener la etiqueta MRW de la recogida."))
        return shipment.label_attachment_id

    def _check_event_is_available(self, shipment, event_type):
        if not shipment.mrw_shipment_number:
            raise UserError(_("El envío debe estar confirmado por MRW antes de notificar al cliente."))
        self._get_attachment_for_event(shipment, event_type)

    def send_customer_notification(self, shipment, event_type, recipient_email, template=None):
        shipment.ensure_one()
        recipient_email = (recipient_email or "").strip()
        if not recipient_email:
            raise UserError(_("Indica un correo electrónico para el cliente."))

        self._check_event_is_available(shipment, event_type)
        template = template or self._get_template_for_event(shipment, event_type)
        if not template:
            raise UserError(_("No hay una plantilla configurada para este aviso MRW."))
        if template.model_id.model != "mrw.shipping.shipment":
            raise UserError(_("La plantilla seleccionada no es válida para envíos MRW."))

        attachment = self._get_attachment_for_event(shipment, event_type)
        values = {
            "shipment_id": shipment.id,
            "event_type": event_type,
            "recipient_email": recipient_email,
            "template_id": template.id,
            "attachment_id": attachment.id,
            "sent_by_id": self.env.user.id,
        }
        try:
            email_values = {"email_to": recipient_email}
            if attachment:
                email_values["attachment_ids"] = [(4, attachment.id)]
            mail_id = template.send_mail(
                shipment.id,
                force_send=True,
                email_values=email_values,
            )
        except Exception as error:
            _logger.exception("Unable to send MRW notification for %s", shipment.display_name)
            values.update({"state": "error", "error_message": str(error)})
            return self.create(values)

        values.update(
            {
                "state": "sent",
                "sent_at": fields.Datetime.now(),
                "mail_id": mail_id,
            }
        )
        return self.create(values)
