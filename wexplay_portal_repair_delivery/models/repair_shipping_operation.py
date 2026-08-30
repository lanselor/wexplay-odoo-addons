# -*- coding: utf-8 -*-

import logging

from odoo import _, models


_logger = logging.getLogger(__name__)


class WexRepairShippingOperation(models.Model):
    _inherit = "wex.repair.shipping.operation"

    def write(self, vals):
        result = super().write(vals)
        self._queue_portal_shipping_notifications_if_ready()
        return result

    def action_get_label(self):
        result = super().action_get_label()
        self._queue_portal_shipping_notifications_if_ready()
        return result

    def _queue_portal_shipping_notifications_if_ready(self):
        template = self.env.ref(
            "wexplay_portal_repair_delivery.mail_template_portal_repair_shipping_ready",
            raise_if_not_found=False,
        )
        if not template:
            _logger.error("Portal shipping notification template is not available.")
            return

        for operation in self:
            if not operation._is_portal_shipping_notification_ready():
                continue
            operation._queue_portal_shipping_notifications(template)

    def _is_portal_shipping_notification_ready(self):
        self.ensure_one()
        shipment = self.mrw_shipment_id
        return bool(
            self.company_id.x_portal_shipping_notifications_enabled
            and self.repair_id.x_requires_shipping
            and self.operation_type in ("pickup", "delivery")
            and shipment
            and shipment.mrw_shipment_number
            and self.label_attachment_id
            and self._get_portal_shipping_notification_url()
        )

    def _get_portal_shipping_notification_recipients(self):
        self.ensure_one()
        commercial_partner = self.repair_id.partner_id.commercial_partner_id
        users = self.env["res.users"].sudo().search(
            [
                ("active", "=", True),
                ("share", "=", True),
                (
                    "partner_id.commercial_partner_id",
                    "=",
                    commercial_partner.id,
                ),
            ]
        )
        return users.filtered(
            lambda user: user.has_group("base.group_portal")
            and not user._is_internal()
            and user.email
        )

    def _get_portal_shipping_notification_url(self):
        self.ensure_one()
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        if not base_url or not self.repair_id:
            return False
        return "%s/my/repairs/%s" % (base_url.rstrip("/"), self.repair_id.id)

    def _get_portal_shipping_notification_operation_label(self):
        self.ensure_one()
        return dict(self._fields["operation_type"].selection).get(
            self.operation_type,
            _("Operación logística"),
        )

    def _queue_portal_shipping_notifications(self, template):
        self.ensure_one()
        Notification = self.env["wex.portal.repair.shipping.notification"].sudo()
        for user in self._get_portal_shipping_notification_recipients():
            if Notification.search_count(
                [
                    ("operation_id", "=", self.id),
                    ("recipient_user_id", "=", user.id),
                ]
            ):
                continue

            notification = Notification.create(
                {
                    "operation_id": self.id,
                    "recipient_user_id": user.id,
                    "recipient_email": user.email,
                    "state": "queued",
                }
            )
            try:
                mail_id = template.sudo().send_mail(
                    self.id,
                    force_send=False,
                    email_values={"email_to": user.email},
                )
            except Exception as error:
                _logger.exception(
                    "Unable to queue portal shipping notification for operation %s.",
                    self.display_name,
                )
                notification.write(
                    {"state": "error", "error_message": str(error)}
                )
                continue
            notification.write({"mail_id": mail_id})
