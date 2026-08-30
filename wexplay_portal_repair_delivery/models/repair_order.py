# -*- coding: utf-8 -*-

from odoo import _, models
from odoo.exceptions import AccessError


class RepairOrder(models.Model):
    _inherit = "repair.order"

    def _get_portal_shipping_operations(self, user=None):
        self.ensure_one()
        user = user or self.env.user
        if not self._can_portal_user_access(user):
            raise AccessError(_("No puedes acceder a esta reparacion desde el portal."))
        if not self.x_requires_shipping:
            return self.env["wex.repair.shipping.operation"]
        return self.sudo().x_shipping_operation_ids.filtered(
            lambda operation: operation.operation_type in ("pickup", "delivery")
        )

    def _get_portal_shipping_values(self, user=None):
        self.ensure_one()
        operations = self._get_portal_shipping_operations(user=user)
        if not self.x_requires_shipping:
            return {"show": False, "operations": []}

        operation_by_type = {
            operation.operation_type: operation for operation in operations
        }
        return {
            "show": True,
            "operations": [
                self._prepare_portal_shipping_operation_values(
                    operation_by_type.get(operation_type),
                    operation_type,
                )
                for operation_type in ("pickup", "delivery")
            ],
        }

    def _prepare_portal_shipping_operation_values(self, operation, operation_type):
        self.ensure_one()
        operation_labels = dict(
            self.env["wex.repair.shipping.operation"]._fields[
                "operation_type"
            ].selection
        )
        if not operation:
            title = operation_labels.get(operation_type, _("Operación logística"))
            return {
                "operation_type": operation_type,
                "title": title,
                "exists": False,
                "empty_message": _(
                    "Todavía no hay una operación de %s creada para esta reparación."
                )
                % title.lower(),
            }

        shipment = operation.mrw_shipment_id
        state_labels = dict(operation._fields["state"].selection)
        return {
            "operation_type": operation_type,
            "title": operation_labels.get(operation_type, _("Operación logística")),
            "exists": True,
            "operation_id": operation.id,
            "status": (
                shipment.mrw_tracking_status_description
                or state_labels.get(operation.state, operation.state or "")
            ),
            "tracking_reference": operation.tracking_ref or operation.mrw_shipment_number,
            "effective_shipping_date": shipment.mrw_effective_shipping_date,
            "tracking_url": operation.tracking_url,
            "has_label": bool(operation.label_attachment_id),
        }

    def _get_portal_shipping_label_download_values(self, operation_id, user=None):
        self.ensure_one()
        operation = self._get_portal_shipping_operations(user=user).filtered(
            lambda record: record.id == operation_id
        )
        if not operation:
            raise AccessError(_("No puedes acceder a esta etiqueta desde el portal."))

        attachment = operation.label_attachment_id
        if not attachment or not attachment.datas:
            return {}
        return {
            "content": attachment.datas,
            "filename": attachment.name or "shipping-label.pdf",
            "mimetype": attachment.mimetype or "application/pdf",
        }
