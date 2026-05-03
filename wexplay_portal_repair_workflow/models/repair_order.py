# -*- coding: utf-8 -*-

from odoo import _, models
from odoo.exceptions import AccessError, UserError


class RepairOrder(models.Model):
    _inherit = "repair.order"

    _PORTAL_BUDGET_QUOTATION_STATES = ("draft", "sent")

    def _get_portal_budget_sale_order(self):
        self.ensure_one()
        return self.sudo().sale_order_id

    def _has_portal_budget_sale_order(self):
        self.ensure_one()
        return bool(self._get_portal_budget_sale_order())

    def _is_portal_budget_waiting_customer(self):
        self.ensure_one()
        return self.x_budget_stage == "waiting_customer"

    def _is_portal_budget_sale_order_accept_ready(self):
        self.ensure_one()
        sale_order = self._get_portal_budget_sale_order()
        return bool(sale_order and sale_order.state in self._PORTAL_BUDGET_QUOTATION_STATES)

    def _is_portal_budget_sale_order_already_accepted(self):
        self.ensure_one()
        sale_order = self._get_portal_budget_sale_order()
        return bool(sale_order and sale_order.state == "sale")

    def _is_portal_budget_sale_order_cancelled(self):
        self.ensure_one()
        sale_order = self._get_portal_budget_sale_order()
        return bool(sale_order and sale_order.state == "cancel")

    def _can_portal_review_budget(self):
        self.ensure_one()
        return (
            self._has_portal_budget_sale_order()
            and self.x_budget_stage in ("waiting_customer", "accepted", "rejected")
        )

    def _can_portal_accept_budget(self):
        self.ensure_one()
        return (
            self._is_portal_budget_waiting_customer()
            and self._is_portal_budget_sale_order_accept_ready()
            and self._can_accept_budget()
        )

    def _can_portal_reject_budget(self):
        self.ensure_one()
        return (
            self._is_portal_budget_waiting_customer()
            and self._is_portal_budget_sale_order_accept_ready()
            and self._can_reject_budget()
        )

    def _check_portal_budget_access(self, user=None):
        self.ensure_one()
        user = user or self.env.user
        if not user.has_group("base.group_portal"):
            raise AccessError(_("Solo un usuario portal puede actuar sobre este presupuesto."))
        if not self._can_portal_user_access(user):
            raise AccessError(_("No puedes acceder a esta reparacion desde el portal."))
        return True

    def _check_can_portal_accept_budget(self, user=None):
        self.ensure_one()
        self._check_portal_budget_access(user=user)
        if not self._get_portal_budget_sale_order():
            raise UserError(_("Esta reparacion no tiene una cotizacion vinculada."))
        if self._is_portal_budget_sale_order_cancelled():
            raise UserError(
                _("La cotizacion vinculada esta cancelada. Contacta con Wexplay para revisarla.")
            )
        if not self._can_portal_accept_budget():
            raise UserError(_("Este presupuesto no se puede aceptar desde el portal."))
        return True

    def _check_can_portal_reject_budget(self, user=None):
        self.ensure_one()
        self._check_portal_budget_access(user=user)
        if not self._get_portal_budget_sale_order():
            raise UserError(_("Esta reparacion no tiene una cotizacion vinculada."))
        if not self._can_portal_reject_budget():
            raise UserError(_("Este presupuesto no se puede rechazar desde el portal."))
        return True

    def _get_portal_budget_device_label(self):
        self.ensure_one()
        values = [
            self._get_portal_brand_label(),
            self._get_portal_model_label(),
        ]
        device = " / ".join(value for value in values if value)
        return device or self._get_portal_product_label() or self._get_portal_device_type_label()

    def _get_portal_budget_status_values(self):
        self.ensure_one()
        sale_order = self._get_portal_budget_sale_order()
        if not sale_order:
            return {
                "key": "missing",
                "label": _("Sin cotizacion vinculada"),
                "message": _("Todavia no hay una cotizacion vinculada a esta reparacion."),
            }
        if self.x_budget_stage == "accepted" or sale_order.state == "sale":
            return {
                "key": "accepted",
                "label": _("Presupuesto aceptado"),
                "message": _("Este presupuesto ya esta aceptado."),
            }
        if self.x_budget_stage == "rejected" or sale_order.state == "cancel":
            return {
                "key": "rejected",
                "label": _("Presupuesto rechazado"),
                "message": _("Este presupuesto no esta disponible para aceptacion."),
            }
        if self.x_budget_stage == "waiting_customer":
            return {
                "key": "pending",
                "label": _("Pendiente de aceptacion"),
                "message": _("Revisa el resumen antes de aceptar o rechazar el presupuesto."),
            }
        return {
            "key": "info",
            "label": _("Presupuesto en revision"),
            "message": _("El presupuesto todavia no esta pendiente de aceptacion."),
        }

    def _prepare_portal_budget_line_values(self, line):
        line.ensure_one()
        return {
            "name": line.product_id.display_name or line.name,
            "description": line.name or "",
            "quantity": line.product_uom_qty,
            "uom": line.product_uom.display_name if line.product_uom else "",
            "price_unit": line.price_unit,
            "subtotal": line.price_subtotal,
            "currency": line.currency_id,
        }

    def _get_portal_budget_line_values(self):
        self.ensure_one()
        sale_order = self.sudo()._get_portal_budget_sale_order()
        if not sale_order:
            return []
        lines = sale_order.order_line.filtered(lambda line: not line.display_type)
        return [self._prepare_portal_budget_line_values(line) for line in lines]

    def _get_portal_budget_summary_values(self):
        self.ensure_one()
        self._check_portal_related_read_access()
        sale_order = self.sudo()._get_portal_budget_sale_order()
        currency = sale_order.currency_id if sale_order else self.company_id.currency_id
        return {
            "repair": self,
            "sale_order": sale_order,
            "status": self._get_portal_budget_status_values(),
            "can_accept": self._can_portal_accept_budget(),
            "can_reject": self._can_portal_reject_budget(),
            "device_label": self._get_portal_budget_device_label() or "-",
            "line_values": self._get_portal_budget_line_values(),
            "amount_untaxed": sale_order.amount_untaxed if sale_order else 0.0,
            "amount_tax": sale_order.amount_tax if sale_order else 0.0,
            "amount_total": sale_order.amount_total if sale_order else 0.0,
            "currency": currency,
        }

    def _get_portal_related_quotation_records(self):
        self.ensure_one()
        self._check_portal_related_read_access()
        sale_order = self._get_portal_budget_sale_order()
        if not sale_order:
            return self.env["sale.order"]
        return sale_order.sudo()

    def _get_portal_related_quotation_values(self):
        self.ensure_one()
        values = []
        for sale_order in self._get_portal_related_quotation_records():
            values.append(
                {
                    "name": sale_order.name,
                    "date": sale_order.date_order,
                    "amount_total": sale_order.amount_total,
                    "currency": sale_order.currency_id,
                    "state": sale_order.state,
                    "state_label": dict(sale_order._fields["state"].selection).get(
                        sale_order.state, sale_order.state or ""
                    ),
                    "portal_url": sale_order.get_portal_url(),
                }
            )
        return values

    def _get_portal_event_sale_order_state_label(self, sale_order):
        sale_order.ensure_one()
        return dict(sale_order._fields["state"].selection).get(
            sale_order.state, sale_order.state or ""
        )

    def _prepare_portal_repair_event_vals(self, event_type, user=None):
        self.ensure_one()
        repair = self.sudo()
        sale_order = repair._get_portal_budget_sale_order()
        user = user or self.env.user
        currency = sale_order.currency_id or repair.company_id.currency_id
        return {
            "event_type": event_type,
            "repair_id": repair.id,
            "sale_order_id": sale_order.id if sale_order else False,
            "partner_id": repair.partner_id.id,
            "commercial_partner_id": repair.partner_id.commercial_partner_id.id,
            "user_id": user.id if user else False,
            "responsible_user_id": repair.user_id.id,
            "company_id": repair.company_id.id,
            "currency_id": currency.id,
            "amount_total": sale_order.amount_total if sale_order else 0.0,
            "repair_state": dict(repair._fields["state"].selection).get(
                repair.state, repair.state or ""
            ),
            "budget_stage": repair._get_budget_stage_label(repair.x_budget_stage),
            "sale_order_state": (
                repair._get_portal_event_sale_order_state_label(sale_order)
                if sale_order
                else ""
            ),
        }

    def _create_portal_repair_event(self, event_type, user=None):
        self.ensure_one()
        vals = self._prepare_portal_repair_event_vals(event_type, user=user)
        return self.env["wex.portal.repair.event"].sudo().create(vals)

    def _get_portal_repair_context_bar_values(self):
        self.ensure_one()
        values = super()._get_portal_repair_context_bar_values()
        status = self._get_portal_budget_status_values()
        if status["key"] not in ("missing", "info"):
            values["status"] = status
        if self._can_portal_review_budget():
            values.update(
                {
                    "show_budget_action": True,
                    "budget_url": "/my/repairs/%s/budget" % self.id,
                }
            )
        return values

    def action_portal_accept_budget(self, user=None):
        self.ensure_one()
        self._check_can_portal_accept_budget(user=user)
        repair = self.sudo()
        sale_order = repair._get_portal_budget_sale_order()
        if sale_order.state in self._PORTAL_BUDGET_QUOTATION_STATES:
            sale_order.action_confirm()
        if repair.x_budget_stage != "accepted":
            repair.action_budget_accept()
        repair._create_portal_repair_event("budget_accepted", user=user)
        return True

    def action_portal_reject_budget(self, user=None):
        self.ensure_one()
        self._check_can_portal_reject_budget(user=user)
        repair = self.sudo()
        sale_order = repair._get_portal_budget_sale_order()
        if sale_order.state in self._PORTAL_BUDGET_QUOTATION_STATES:
            sale_order.action_cancel()
        if repair.x_budget_stage != "rejected":
            repair.action_budget_reject()
        repair._create_portal_repair_event("budget_rejected", user=user)
        return True
