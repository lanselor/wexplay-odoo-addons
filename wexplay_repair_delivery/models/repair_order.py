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
        search="_search_x_pending_delivery_filter",
        store=False,
    )

    x_can_mark_delivered = fields.Boolean(
        string="Puede marcarse como entregada",
        compute="_compute_x_can_mark_delivered",
        store=False,
    )

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

    def _search_x_pending_delivery_filter(self, operator, value):
        if operator not in ("=", "!=") or value not in (True, False):
            raise UserError(_("Busqueda no soportada para 'Pendiente de entrega'."))

        repairs = self.env["repair.order"].search([
            ("state", "in", ("done", "cancel")),
        ])
        repair_ids = repairs.filtered(
            lambda repair: repair._is_pending_delivery_candidate()
        ).ids
        positive = (operator == "=" and value is True) or (
            operator == "!=" and value is False
        )
        return [("id", "in" if positive else "not in", repair_ids)]

    def _get_sat_channel(self):
        self.ensure_one()
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
                    "Solo se puede marcar como entregada una reparacion en estado 'Reparada' o 'Cancelada' que este en la ubicacion 'Pendiente de recogida'."
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

    def write(self, vals):
        previous_states = {}
        track_confirmed_transition = "state" in vals

        if track_confirmed_transition:
            previous_states = {rec.id: rec.state for rec in self}

        res = super().write(vals)

        if vals.get("state") == "confirmed":
            repairs_to_notify = self.filtered(
                lambda r: previous_states.get(r.id) != "confirmed"
                and r.state == "confirmed"
            )
            if repairs_to_notify:
                repairs_to_notify._post_budget_accepted_to_sat_channel()

        return res
