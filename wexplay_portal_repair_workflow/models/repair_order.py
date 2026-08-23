# -*- coding: utf-8 -*-

import logging

from odoo import SUPERUSER_ID, _, api, models
from odoo.exceptions import AccessError, UserError

_logger = logging.getLogger(__name__)


class RepairOrder(models.Model):
    _inherit = "repair.order"

    _PORTAL_BUDGET_QUOTATION_STATES = ("draft", "sent")
    _PORTAL_PENDING_BUDGET_ALERT_PREVIEW_LIMIT = 5

    def _run_portal_budget_workflow_action(self, method_name, user=None, event_type=None, **context_flags):
        self.ensure_one()
        with self.env.registry.cursor() as new_cr:
            sudo_env = api.Environment(
                new_cr,
                SUPERUSER_ID,
                dict(self.env.context, **context_flags),
            )
            sudo_repair = sudo_env[self._name].browse(self.id)
            action = getattr(sudo_repair, method_name)()
            if isinstance(action, dict):
                raise UserError(
                    _("La accion del presupuesto requiere una confirmacion no esperada.")
                )
            if event_type:
                sudo_repair._create_portal_repair_event(event_type, user=user)
            sudo_repair._log_portal_budget_debug_snapshot(
                "isolated_%s_done" % method_name,
                user=user,
            )
            new_cr.commit()
        return True

    def _get_portal_budget_sale_order(self):
        self.ensure_one()
        return self.sudo().sale_order_id

    @api.model
    def _get_portal_pending_budget_domain(self, user=None):
        user = user or self.env.user
        return self._get_portal_visible_domain(user=user) + [
            ("x_budget_stage", "=", "waiting_customer")
        ]

    @api.model
    def _get_portal_pending_budget_alert_values(self, user=None):
        user = user or self.env.user
        domain = self._get_portal_pending_budget_domain(user=user)
        total_count = self.search_count(domain)
        preview_repairs = self.search(
            domain,
            order="create_date desc, id desc",
            limit=self._PORTAL_PENDING_BUDGET_ALERT_PREVIEW_LIMIT,
        )

        items = []
        for repair in preview_repairs:
            items.append(
                {
                    "id": repair.id,
                    "name": repair.name or "",
                    "device_label": repair._get_portal_budget_device_label() or "-",
                    "reported_issue": repair.x_reported_issue or "",
                    "create_date": repair.create_date,
                    "budget_url": "/my/repairs/%s/budget" % repair.id,
                }
            )

        return {
            "show": bool(total_count),
            "total_count": total_count,
            "preview_limit": self._PORTAL_PENDING_BUDGET_ALERT_PREVIEW_LIMIT,
            "remaining_count": max(total_count - len(items), 0),
            "items": items,
            "list_url": "/my/repairs?filterby=pending_budget",
            "reminder_interval_hours": 5,
            "reminder_key": "portal_pending_budget_alert_user_%s" % user.id,
        }

    def _get_portal_budget_debug_values(self, user=None):
        self.ensure_one()
        user = user or self.env.user
        repair = self.sudo()
        sale_order = repair._get_portal_budget_sale_order().sudo()
        partner = user.partner_id
        commercial_partner = partner.commercial_partner_id
        debug_values = {
            "repair_id": repair.id,
            "repair_name": repair.name or "",
            "repair_state": repair.state or "",
            "budget_stage": repair.x_budget_stage or "",
            "sale_order_id": sale_order.id if sale_order else False,
            "sale_order_name": sale_order.name if sale_order else "",
            "sale_order_state": sale_order.state if sale_order else "",
            "sale_order_line_count": len(sale_order.order_line) if sale_order else 0,
            "portal_user_id": user.id,
            "portal_user_login": user.login or "",
            "portal_partner_id": partner.id,
            "portal_partner_name": partner.display_name or "",
            "commercial_partner_id": commercial_partner.id,
            "commercial_partner_name": commercial_partner.display_name or "",
            "repair_partner_id": repair.partner_id.id,
            "repair_partner_name": repair.partner_id.display_name or "",
            "can_portal_access": repair._can_portal_user_access(user),
            "has_sale_order": bool(sale_order),
            "is_waiting_customer": repair._is_portal_budget_waiting_customer(),
            "is_sale_order_accept_ready": repair._is_portal_budget_sale_order_accept_ready(),
            "is_sale_order_already_accepted": (
                repair._is_portal_budget_sale_order_already_accepted()
            ),
            "is_sale_order_cancelled": repair._is_portal_budget_sale_order_cancelled(),
            "can_portal_review_budget": repair._can_portal_review_budget(),
            "can_portal_accept_budget": repair._can_portal_accept_budget(),
            "can_portal_reject_budget": repair._can_portal_reject_budget(),
        }
        return debug_values

    def _log_portal_budget_debug_snapshot(self, stage, user=None, extra=None):
        self.ensure_one()
        debug_values = self._get_portal_budget_debug_values(user=user)
        if extra:
            debug_values.update(extra)
        _logger.info("Portal budget debug [%s]: %s", stage, debug_values)
        return debug_values

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

    def _can_portal_open_native_quotation(self):
        self.ensure_one()
        return bool(
            self._has_portal_budget_sale_order()
            and self.x_budget_stage != "waiting_customer"
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
        if self.x_budget_stage == "not_repairable":
            return {
                "key": "rejected",
                "label": _("No reparable"),
                "message": _("Esta reparacion no tiene una solucion tecnica viable."),
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
        line = line.sudo()
        line.ensure_one()
        currency = line.currency_id.sudo()
        return {
            "name": line.product_id.display_name or line.name,
            "description": line.name or "",
            "quantity": line.product_uom_qty,
            "uom": line.product_uom.display_name if line.product_uom else "",
            "price_unit": line.price_unit,
            "subtotal": line.price_subtotal,
            "currency": currency,
        }

    def _get_portal_budget_line_values(self):
        self.ensure_one()
        sale_order = self.sudo()._get_portal_budget_sale_order().sudo()
        if not sale_order:
            return []
        lines = sale_order.order_line.sudo().filtered(lambda line: not line.display_type)
        return [self._prepare_portal_budget_line_values(line) for line in lines]

    def _get_portal_budget_summary_values(self):
        self.ensure_one()
        self._check_portal_related_read_access()
        repair = self.sudo()
        sale_order = repair._get_portal_budget_sale_order().sudo()
        currency = (
            sale_order.currency_id.sudo()
            if sale_order
            else repair.company_id.currency_id.sudo()
        )
        return {
            "repair": repair,
            "status": repair._get_portal_budget_status_values(),
            "can_accept": repair._can_portal_accept_budget(),
            "can_reject": repair._can_portal_reject_budget(),
            "device_label": repair._get_portal_budget_device_label() or "-",
            "line_values": repair._get_portal_budget_line_values(),
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
        can_open_native_quotation = self._can_portal_open_native_quotation()
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
                    "portal_url": sale_order.get_portal_url() if can_open_native_quotation else "",
                    "can_open_portal_url": can_open_native_quotation,
                }
            )
        return values

    def _get_portal_event_sale_order_state_label(self, sale_order):
        sale_order.ensure_one()
        return dict(sale_order._fields["state"].selection).get(
            sale_order.state, sale_order.state or ""
        )

    def _prepare_portal_repair_event_vals(self, event_type, user=None, extra_values=None):
        self.ensure_one()
        repair = self.sudo()
        sale_order = repair._get_portal_budget_sale_order()
        user = user or self.env.user
        currency = sale_order.currency_id or repair.company_id.currency_id
        values = {
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
        values.update(extra_values or {})
        return values

    def _create_portal_repair_event(self, event_type, user=None, extra_values=None):
        self.ensure_one()
        vals = self._prepare_portal_repair_event_vals(
            event_type,
            user=user,
            extra_values=extra_values,
        )
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
        repair._log_portal_budget_debug_snapshot("before_accept", user=user)
        if repair.x_budget_stage != "accepted":
            repair._run_portal_budget_workflow_action(
                "action_budget_accept",
                user=user,
                event_type="budget_accepted",
            )
        else:
            repair._create_portal_repair_event("budget_accepted", user=user)
        self.browse(self.id)._log_portal_budget_debug_snapshot("after_accept", user=user)
        return True

    def action_portal_reject_budget(self, user=None):
        self.ensure_one()
        self._check_can_portal_reject_budget(user=user)
        repair = self.sudo()
        repair._log_portal_budget_debug_snapshot("before_reject", user=user)
        if repair.x_budget_stage != "rejected":
            repair._run_portal_budget_workflow_action(
                "action_budget_reject",
                user=user,
                event_type="budget_rejected",
                skip_budget_reject_confirm=True,
            )
        else:
            repair._create_portal_repair_event("budget_rejected", user=user)
        self.browse(self.id)._log_portal_budget_debug_snapshot("after_reject", user=user)
        return True
