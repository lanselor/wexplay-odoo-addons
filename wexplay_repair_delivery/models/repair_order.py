# -*- coding: utf-8 -*-
import logging

from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class RepairOrder(models.Model):
    _inherit = "repair.order"

    _SAT_CHANNEL_NAMES = ["SAT-Reparaciones", "SAT - Reparaciones"]
    _SAT_BUDGET_ACCEPTED_TEMPLATE = (
        "wexplay_repair_delivery.sat_budget_accepted_channel_message"
    )

    state = fields.Selection(
        selection_add=[("delivered", "Entregado")],
        ondelete={"delivered": "set default"},
    )

    x_is_delivered = fields.Boolean(
        string="Entregado",
        compute="_compute_x_is_delivered",
        store=False,
    )
    x_pending_delivery_filter = fields.Boolean(
        string="Pendiente de entrega",
        compute="_compute_x_pending_delivery_filter",
        store=True,
        index=True,
    )
    x_can_mark_delivered = fields.Boolean(
        string="Puede marcarse como entregada",
        compute="_compute_x_can_mark_delivered",
        store=False,
    )
    x_requires_shipping = fields.Boolean(
        string="Requiere envío / recogida",
        tracking=True,
        help="Activa la gestión logística desde la reparación.",
    )
    x_shipping_operation_ids = fields.One2many(
        comodel_name="wex.repair.shipping.operation",
        inverse_name="repair_id",
        string="Operaciones logísticas",
        copy=False,
    )
    x_pickup_operation_id = fields.Many2one(
        comodel_name="wex.repair.shipping.operation",
        string="Recogida",
        compute="_compute_x_shipping_operations",
    )
    x_delivery_operation_id = fields.Many2one(
        comodel_name="wex.repair.shipping.operation",
        string="Entrega",
        compute="_compute_x_shipping_operations",
    )
    x_has_pickup = fields.Boolean(
        string="Tiene recogida",
        compute="_compute_x_shipping_operations",
    )
    x_has_delivery = fields.Boolean(
        string="Tiene entrega",
        compute="_compute_x_shipping_operations",
    )

    @api.depends("x_shipping_operation_ids.operation_type")
    def _compute_x_shipping_operations(self):
        for rec in self:
            pickup = rec.x_shipping_operation_ids.filtered(
                lambda operation: operation.operation_type == "pickup"
            )[:1]
            delivery = rec.x_shipping_operation_ids.filtered(
                lambda operation: operation.operation_type == "delivery"
            )[:1]
            rec.x_pickup_operation_id = pickup
            rec.x_delivery_operation_id = delivery
            rec.x_has_pickup = bool(pickup)
            rec.x_has_delivery = bool(delivery)

    @api.depends("state")
    def _compute_x_is_delivered(self):
        for rec in self:
            rec.x_is_delivered = rec.state == "delivered"

    @api.depends(
        "state",
        "product_location_src_id",
        "company_id",
        "company_id.x_repair_state_location_done_id",
    )
    def _compute_x_pending_delivery_filter(self):
        for rec in self:
            rec.x_pending_delivery_filter = rec._is_pending_delivery_candidate()

    @api.depends(
        "state",
        "product_location_src_id",
        "company_id",
        "company_id.x_repair_state_location_done_id",
        "company_id.x_repair_state_location_delivered_id",
    )
    def _compute_x_can_mark_delivered(self):
        for rec in self:
            rec.x_can_mark_delivered = rec._can_mark_delivered()

    def action_create_pickup_operation(self):
        self.ensure_one()
        if not self.x_requires_shipping:
            raise UserError(_("Activa primero 'Requiere envío / recogida'."))
        return self._create_shipping_operation("pickup")

    def action_create_delivery_operation(self):
        self.ensure_one()
        if not self.x_requires_shipping:
            raise UserError(_("Activa primero 'Requiere envío / recogida'."))
        return self._create_shipping_operation("delivery")

    def _create_shipping_operation(self, operation_type):
        self.ensure_one()
        existing = self.x_shipping_operation_ids.filtered(
            lambda operation: operation.operation_type == operation_type
        )
        if existing:
            raise UserError(
                _(
                    "Esta reparación ya tiene una operación logística de este tipo."
                )
            )
        operation = self.env["wex.repair.shipping.operation"].create(
            {
                "repair_id": self.id,
                "operation_type": operation_type,
            }
        )
        return {
            "type": "ir.actions.act_window",
            "name": _("Operación logística"),
            "res_model": "wex.repair.shipping.operation",
            "res_id": operation.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_open_pickup_operation(self):
        self.ensure_one()
        if not self.x_pickup_operation_id:
            raise UserError(_("Todavía no hay operación de recogida."))
        return self.x_pickup_operation_id.action_open_current_record()

    def action_open_delivery_operation(self):
        self.ensure_one()
        if not self.x_delivery_operation_id:
            raise UserError(_("Todavía no hay operación de entrega."))
        return self.x_delivery_operation_id.action_open_current_record()

    def _is_pending_delivery_candidate(self):
        self.ensure_one()
        pending_pickup_location = self.company_id.x_repair_state_location_done_id
        return bool(
            pending_pickup_location
            and self.state in ("done", "cancel")
            and self.product_location_src_id == pending_pickup_location
        )

    def _can_mark_delivered(self):
        self.ensure_one()
        if self.state == "delivered":
            return False
        return bool(
            self._is_pending_delivery_candidate()
            and self.company_id.x_repair_state_location_delivered_id
        )

    def _get_delivered_location(self):
        self.ensure_one()
        delivered_location = self.company_id.x_repair_state_location_delivered_id
        if not delivered_location:
            raise UserError(
                _(
                    "Configura primero la ubicacion 'Entregada' en Ajustes > Wexplay SAT."
                )
            )
        return delivered_location

    def _check_can_mark_delivered(self):
        self.ensure_one()
        if self.state == "delivered":
            return False
        if not self._is_pending_delivery_candidate():
            raise UserError(
                _(
                    "Solo se puede marcar como entregada una reparacion en estado 'Finalizada' o 'Cancelada' que este en la ubicacion 'Pendiente de recogida'."
                )
            )
        if not self.company_id.x_repair_state_location_delivered_id:
            self._get_delivered_location()
        return True

    def action_mark_delivered(self):
        for rec in self:
            if not rec._check_can_mark_delivered():
                continue
            rec.write({"state": "delivered"})
        return True

    def action_mark_delivered_multi(self):
        self.action_mark_delivered()
        return {"type": "ir.actions.client", "tag": "reload"}

    def action_budget_accept(self):
        previous_budget_stages = {repair.id: repair.x_budget_stage for repair in self}
        result = super().action_budget_accept()
        repairs_to_notify = self.filtered(
            lambda repair: previous_budget_stages.get(repair.id) == "waiting_customer"
            and repair.x_budget_stage == "accepted"
        )
        if repairs_to_notify:
            repairs_to_notify._post_budget_accepted_to_sat_channel()
        return result

    def _get_sat_channel(self):
        self.ensure_one()
        channel_id = self.env["ir.config_parameter"].sudo().get_param(
            "wexplay_repair_delivery.sat_budget_accepted_channel_id"
        )
        configured_channel = self.env["discuss.channel"]
        if channel_id and str(channel_id).isdigit():
            configured_channel = self.env["discuss.channel"].browse(
                int(channel_id)
            ).exists()
        if configured_channel:
            return configured_channel

        return self.env["discuss.channel"].search(
            [("name", "in", self._SAT_CHANNEL_NAMES)],
            limit=1,
        )

    def _get_sat_budget_message_values(self):
        self.ensure_one()
        technician = self.user_id
        return {
            "repair_name": self.name or _("Sin referencia"),
            "cliente": self.partner_id.name if self.partner_id else _("Sin cliente"),
            "producto": (
                self.product_id.display_name
                if self.product_id
                else _("Producto no especificado")
            ),
            "tecnico_nombre": technician.name if technician else _("Sin asignar"),
            "enlace": f"/web#id={self.id}&model={self._name}",
        }

    def _build_sat_budget_accepted_message(self):
        self.ensure_one()
        html = self.env["ir.qweb"]._render(
            self._SAT_BUDGET_ACCEPTED_TEMPLATE,
            self._get_sat_budget_message_values(),
        )
        return Markup(html)

    def _post_budget_accepted_to_sat_channel(self):
        for repair in self:
            channel_sat = repair._get_sat_channel()
            if not channel_sat:
                _logger.warning(
                    "SAT notification skipped because no repair channel was found for %s.",
                    repair.display_name,
                )
                continue

            partner = repair.user_id.partner_id if repair.user_id else False
            msg_kwargs = {
                "body": repair._build_sat_budget_accepted_message(),
                "message_type": "comment",
                "subtype_xmlid": "mail.mt_comment",
            }
            if partner:
                msg_kwargs["partner_ids"] = [partner.id]

            try:
                channel_sat.sudo().message_post(**msg_kwargs)
            except Exception:
                _logger.exception(
                    "Error posting SAT budget acceptance notification for %s.",
                    repair.display_name,
                )
