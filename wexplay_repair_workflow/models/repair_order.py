# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class RepairOrder(models.Model):
    _inherit = "repair.order"

    _BUDGET_SALE_ORDER_ACCEPT_READY_STATES = ("draft", "sent")
    _BUDGET_SALE_ORDER_ACCEPTED_STATES = ("sale",)
    _BUDGET_SALE_ORDER_REJECT_READY_STATES = ("draft", "sent")

    x_budget_stage = fields.Selection(
        [
            ("none", "Sin presupuesto"),
            ("estimating", "Revision"),
            ("waiting_customer", "Espera Cliente"),
            ("accepted", "Aceptado"),
            ("rejected", "Rechazado"),
            ("not_repairable", "No reparable"),
        ],
        string="Estado presupuesto",
        default="none",
        tracking=True,
        copy=False,
    )

    x_budget_started_at = fields.Datetime(
        string="Presupuesto iniciado el",
        readonly=True,
        copy=False,
        tracking=True,
    )

    x_budget_resolved_at = fields.Datetime(
        string="Presupuesto resuelto el",
        readonly=True,
        copy=False,
        tracking=True,
    )

    x_waiting_spare_started_at = fields.Datetime(
        string="Pendiente de repuesto desde",
        readonly=True,
        copy=False,
        tracking=True,
    )

    x_is_in_glue_desk = fields.Boolean(
        string="Esta en Mesa Pegado",
        compute="_compute_x_is_in_glue_desk",
        store=False,
    )

    x_is_waiting_spare_location = fields.Boolean(
        string="Esta en Pendiente de repuesto",
        compute="_compute_x_is_waiting_spare_location",
        store=False,
    )

    _BUDGET_TRANSITIONS = {
        "none": {"estimating"},
        "estimating": {"waiting_customer", "not_repairable"},
        "waiting_customer": {"accepted", "rejected", "estimating", "not_repairable"},
        "accepted": {"estimating"},
        "rejected": {"estimating"},
        "not_repairable": {"estimating"},
    }

    @api.depends(
        "product_location_src_id",
        "company_id",
        "company_id.x_repair_state_location_glue_desk_id",
    )
    def _compute_x_is_in_glue_desk(self):
        for repair in self:
            glue_location = repair.company_id.x_repair_state_location_glue_desk_id
            repair.x_is_in_glue_desk = bool(
                glue_location and repair.product_location_src_id == glue_location
            )

    @api.depends(
        "product_location_src_id",
        "company_id",
        "company_id.x_repair_state_location_waiting_spare_id",
    )
    def _compute_x_is_waiting_spare_location(self):
        for repair in self:
            waiting_location = repair.company_id.x_repair_state_location_waiting_spare_id
            repair.x_is_waiting_spare_location = bool(
                waiting_location and repair.product_location_src_id == waiting_location
            )

    # ---------------------------------------------------------
    # Helpers de flujo
    # ---------------------------------------------------------

    def _get_budget_sale_order(self):
        self.ensure_one()
        return self.sale_order_id

    def _should_confirm_wait_customer_without_sale_order(self):
        self.ensure_one()
        return True

    def _requires_budget_sale_order_for_accept(self):
        self.ensure_one()
        return True

    def _should_confirm_budget_sale_order_on_accept(self):
        self.ensure_one()
        return True

    def _should_manage_sale_order_on_budget_reject(self):
        self.ensure_one()
        return True

    def _should_reset_sale_order_on_budget_reestimate(self):
        self.ensure_one()
        return True

    def _get_budget_wait_customer_without_sale_order_message(self):
        self.ensure_one()
        return _(
            "Estas intentando cambiar el estado a espera cliente sin una cotizacion creada."
        )

    def _get_budget_reject_confirm_message(self):
        self.ensure_one()
        return _(
            "Vas a rechazar este presupuesto. Se cancelara la cotizacion vinculada si esta disponible. ¿Deseas continuar?"
        )

    def _get_budget_reestimate_quote_reset_confirm_message(self):
        self.ensure_one()
        return _(
            "Si vas a volver a presupuestar, la cotizacion debe establecerse a borrador. ¿Deseas continuar?"
        )

    def _has_budget_sale_order(self):
        self.ensure_one()
        return bool(self._get_budget_sale_order())

    def _is_budget_sale_order_accept_ready(self):
        self.ensure_one()
        sale_order = self._get_budget_sale_order()
        return bool(
            sale_order and sale_order.state in self._BUDGET_SALE_ORDER_ACCEPT_READY_STATES
        )

    def _is_budget_sale_order_already_accepted(self):
        self.ensure_one()
        sale_order = self._get_budget_sale_order()
        return bool(
            sale_order and sale_order.state in self._BUDGET_SALE_ORDER_ACCEPTED_STATES
        )

    def _is_budget_sale_order_reject_ready(self):
        self.ensure_one()
        sale_order = self._get_budget_sale_order()
        return bool(
            sale_order and sale_order.state in self._BUDGET_SALE_ORDER_REJECT_READY_STATES
        )

    def _check_budget_sale_order_available_for_accept(self):
        self.ensure_one()
        sale_order = self._get_budget_sale_order()
        if not sale_order:
            if self._requires_budget_sale_order_for_accept():
                raise UserError(
                    _("No se puede aceptar el presupuesto sin una cotizacion.")
                )
            return self.env["sale.order"]
        if not self._should_confirm_budget_sale_order_on_accept():
            return sale_order
        if self._is_budget_sale_order_accept_ready():
            return sale_order
        if self._is_budget_sale_order_already_accepted():
            return sale_order
        raise UserError(
            _(
                "No se puede aceptar el presupuesto porque la cotizacion vinculada no esta disponible."
            )
        )

    def _check_budget_sale_order_available_for_reject(self):
        self.ensure_one()
        if not self._should_manage_sale_order_on_budget_reject():
            return self.env["sale.order"]
        sale_order = self._get_budget_sale_order()
        if not sale_order:
            return self.env["sale.order"]
        if self._is_budget_sale_order_reject_ready() or sale_order.state == "cancel":
            return sale_order
        raise UserError(
            _(
                "No se puede rechazar el presupuesto porque la cotizacion vinculada no se puede cancelar."
            )
        )

    def _get_budget_stage_label(self, stage):
        self.ensure_one()
        return dict(self._fields["x_budget_stage"].selection).get(stage, stage)

    def _is_budget_transition_allowed(self, new_stage):
        self.ensure_one()

        current_stage = self.x_budget_stage or "none"
        allowed = self._BUDGET_TRANSITIONS.get(current_stage, set())
        if new_stage not in allowed:
            return False

        return not (
            current_stage in ("rejected", "not_repairable")
            and new_stage == "estimating"
            and self.state == "cancel"
        )

    def _prepare_budget_stage_vals(self, new_stage):
        self.ensure_one()

        if not self._is_budget_transition_allowed(new_stage):
            raise UserError(
                _(
                    "Transicion de presupuesto no permitida: %(current)s -> %(new)s."
                )
                % {
                    "current": self._get_budget_stage_label(self.x_budget_stage),
                    "new": self._get_budget_stage_label(new_stage),
                }
            )

        vals = {"x_budget_stage": new_stage}
        if new_stage == "estimating" and not self.x_budget_started_at:
            vals["x_budget_started_at"] = fields.Datetime.now()
        if new_stage in ("accepted", "rejected", "not_repairable"):
            vals["x_budget_resolved_at"] = fields.Datetime.now()
        return vals

    def _set_budget_stage(self, new_stage):
        repairs_by_vals = {}
        for repair in self:
            vals = repair._prepare_budget_stage_vals(new_stage)
            key = tuple(sorted(vals.items()))
            repairs_by_vals.setdefault(key, self.env["repair.order"])
            repairs_by_vals[key] |= repair

        for vals_key, repairs in repairs_by_vals.items():
            repairs.write(dict(vals_key))
        return True

    def _confirm_repair_if_needed(self):
        self.ensure_one()
        if self.state == "draft":
            self.action_validate()
        return True

    def _confirm_budget_sale_order_if_needed(self):
        self.ensure_one()
        sale_order = self._check_budget_sale_order_available_for_accept()
        if not sale_order or not self._should_confirm_budget_sale_order_on_accept():
            return sale_order
        if sale_order.state in self._BUDGET_SALE_ORDER_ACCEPT_READY_STATES:
            sale_order.action_confirm()
        return sale_order

    def _cancel_budget_sale_order_if_needed(self):
        self.ensure_one()
        if not self._should_manage_sale_order_on_budget_reject():
            return self.env["sale.order"]
        sale_order = self._check_budget_sale_order_available_for_reject()
        if sale_order and sale_order.state in self._BUDGET_SALE_ORDER_REJECT_READY_STATES:
            sale_order.action_cancel()
        return sale_order

    def _needs_budget_reestimate_sale_order_reset(self):
        self.ensure_one()
        if not self._should_reset_sale_order_on_budget_reestimate():
            return False
        sale_order = self._get_budget_sale_order()
        return bool(sale_order and sale_order.state == "sale")

    def _reopen_budget_sale_order_for_reestimate(self):
        self.ensure_one()
        sale_order = self._get_budget_sale_order()
        if not sale_order or sale_order.state != "sale":
            return sale_order

        sale_order.with_context(disable_cancel_warning=True).action_cancel()
        sale_order.action_draft()

        if sale_order.state != "draft":
            raise UserError(
                _(
                    "No se ha podido devolver la cotizacion a borrador para volver a presupuestar."
                )
            )
        return sale_order

    # ---------------------------------------------------------
    # Helpers de ubicacion SAT
    # ---------------------------------------------------------

    def _get_target_location_from_budget_stage(self, stage):
        self.ensure_one()
        company = self.company_id
        mapping = {
            "estimating": company.x_repair_budget_location_estimating_id,
            "waiting_customer": company.x_repair_budget_location_waiting_customer_id,
            "accepted": company.x_repair_budget_location_accepted_id,
            "rejected": company.x_repair_budget_location_rejected_id,
        }
        return mapping.get(stage)

    def _get_target_location_from_repair_state(self, state):
        self.ensure_one()
        company = self.company_id
        mapping = {
            "under_repair": company.x_repair_state_location_under_repair_id,
            "done": company.x_repair_state_location_done_id,
            "delivered": company.x_repair_state_location_delivered_id,
            "cancel": company.x_repair_budget_location_rejected_id,
        }
        return mapping.get(state)

    def _set_product_location_if_needed(self, location):
        self.ensure_one()
        if location and self.product_location_src_id != location:
            self.write({"product_location_src_id": location.id})

    def _sync_location_for_budget_stage(self):
        repairs_by_location = {}
        for repair in self:
            location = repair._get_target_location_from_budget_stage(repair.x_budget_stage)
            if not location or repair.product_location_src_id == location:
                continue
            repairs_by_location.setdefault(location.id, self.env["repair.order"])
            repairs_by_location[location.id] |= repair

        for location_id, repairs in repairs_by_location.items():
            repairs.write({"product_location_src_id": location_id})

    def _sync_location_for_repair_state(self):
        repairs_by_location = {}
        for repair in self:
            location = repair._get_target_location_from_repair_state(repair.state)
            if not location or repair.product_location_src_id == location:
                continue
            repairs_by_location.setdefault(location.id, self.env["repair.order"])
            repairs_by_location[location.id] |= repair

        for location_id, repairs in repairs_by_location.items():
            repairs.write({"product_location_src_id": location_id})

    def _requires_glue_choice_on_finish(self):
        self.ensure_one()
        if not self.x_device_type:
            raise UserError(
                _(
                    "Debes indicar el Tipo de dispositivo antes de finalizar la reparacion."
                )
            )
        return self.x_device_type in ("mobile", "tablet")

    def _open_glue_finish_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Ubicacion final de la reparacion"),
            "res_model": "wex.finish.repair.glue.choice.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_repair_id": self.id},
        }

    def _open_waiting_spare_confirm_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Confirmar pendiente de repuesto"),
            "res_model": "wex.waiting.spare.confirm.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_repair_id": self.id},
        }

    def _open_budget_workflow_confirm_wizard(self, action_key, message):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Confirmar accion"),
            "res_model": "wex.budget.workflow.confirm.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_repair_id": self.id,
                "default_action_key": action_key,
                "default_message": message,
            },
        }

    def _get_waiting_spare_location(self):
        self.ensure_one()
        waiting_location = self.company_id.x_repair_state_location_waiting_spare_id
        if not waiting_location:
            raise UserError(
                _(
                    "Configura primero la ubicacion 'Pendiente de repuesto' en Ajustes > Wexplay SAT."
                )
            )
        return waiting_location

    def _set_waiting_spare_location(self):
        for repair in self:
            vals = {"product_location_src_id": repair._get_waiting_spare_location().id}
            if not repair.x_waiting_spare_started_at:
                vals["x_waiting_spare_started_at"] = fields.Datetime.now()
            repair.write(vals)
        return True

    # ---------------------------------------------------------
    # Validaciones de botones
    # ---------------------------------------------------------

    def _can_start_budget(self):
        self.ensure_one()
        return (
            self.state not in ("done", "cancel", "delivered")
            and self.x_budget_stage in ("none", "rejected")
        )

    def _can_wait_customer(self):
        self.ensure_one()
        return (
            self.state not in ("done", "cancel", "delivered")
            and self.x_budget_stage == "estimating"
        )

    def _can_accept_budget(self):
        self.ensure_one()
        return (
            self.state not in ("done", "cancel", "delivered")
            and self.x_budget_stage == "waiting_customer"
        )

    def _can_reject_budget(self):
        self.ensure_one()
        return (
            self.state not in ("done", "cancel", "delivered")
            and self.x_budget_stage == "waiting_customer"
        )

    def _can_reestimate_budget(self):
        self.ensure_one()
        return (
            self.state not in ("done", "cancel", "delivered")
            and (
                self.x_budget_stage == "waiting_customer"
                or self.x_budget_stage == "accepted"
                or (self.x_budget_stage == "rejected" and self.state != "cancel")
                or self.x_budget_stage == "not_repairable"
            )
        )

    def _can_mark_not_repairable(self):
        self.ensure_one()
        return (
            self.state not in ("done", "cancel", "delivered")
            and self.x_budget_stage in ("estimating", "waiting_customer")
        )

    def _can_finish_not_repairable_diagnosis(self):
        self.ensure_one()
        return (
            self.state not in ("done", "cancel", "delivered")
            and self.x_budget_stage == "not_repairable"
        )

    def _get_not_repairable_finish_location(self):
        self.ensure_one()
        done_location = self.company_id.x_repair_state_location_done_id
        if not done_location:
            raise UserError(
                _(
                    "Configura primero la ubicacion 'Finalizada' en Ajustes > Wexplay SAT."
                )
            )
        return done_location

    def _check_can_set_waiting_spare(self):
        self.ensure_one()
        if self.state in ("cancel", "delivered"):
            raise UserError(
                _(
                    "No puedes marcar una reparacion cancelada o entregada como pendiente de repuesto."
                )
            )

    def _should_open_waiting_spare_confirm(self):
        self.ensure_one()
        return (
            not self.env.context.get("skip_waiting_spare_confirm")
            and not self.move_ids
        )

    # ---------------------------------------------------------
    # Acciones del workflow
    # ---------------------------------------------------------

    def action_start_budget(self):
        for repair in self:
            if not repair._can_start_budget():
                raise UserError(_("No se puede iniciar el presupuesto en el estado actual."))
        result = self._set_budget_stage("estimating")
        self._sync_location_for_budget_stage()
        return result

    def action_budget_wait_customer(self):
        for repair in self:
            if not repair._can_wait_customer():
                raise UserError(
                    _(
                        "Solo se puede pasar a espera de cliente desde 'Revision'."
                    )
                )
            if (
                repair._should_confirm_wait_customer_without_sale_order()
                and not repair._has_budget_sale_order()
                and not self.env.context.get("skip_budget_wait_customer_quote_confirm")
            ):
                return repair._open_budget_workflow_confirm_wizard(
                    "wait_customer_without_quote",
                    repair._get_budget_wait_customer_without_sale_order_message(),
                )
        result = self._set_budget_stage("waiting_customer")
        self._sync_location_for_budget_stage()
        return result

    def action_budget_accept(self):
        for repair in self:
            if not repair._can_accept_budget():
                raise UserError(
                    _(
                        "Solo se puede aceptar un presupuesto que este esperando al cliente."
                    )
                )
            repair._confirm_budget_sale_order_if_needed()
            repair._confirm_repair_if_needed()
        result = self._set_budget_stage("accepted")
        self._sync_location_for_budget_stage()
        return result

    def action_budget_reject(self):
        for repair in self:
            if not repair._can_reject_budget():
                raise UserError(
                    _(
                        "Solo se puede rechazar un presupuesto que este esperando al cliente."
                    )
                )
            repair._check_budget_sale_order_available_for_reject()
            if not self.env.context.get("skip_budget_reject_confirm"):
                return repair._open_budget_workflow_confirm_wizard(
                    "reject_budget",
                    repair._get_budget_reject_confirm_message(),
                )
            repair._cancel_budget_sale_order_if_needed()
        result = self._set_budget_stage("rejected")
        self._sync_location_for_budget_stage()
        return result

    def action_budget_mark_not_repairable(self):
        for repair in self:
            if not repair._can_mark_not_repairable():
                raise UserError(
                    _(
                        "Solo se puede marcar como no reparable desde revision o espera cliente."
                    )
                )
        return self._set_budget_stage("not_repairable")

    def action_finish_not_repairable_diagnosis(self):
        for repair in self:
            if not repair._can_finish_not_repairable_diagnosis():
                raise UserError(
                    _(
                        "Solo se puede finalizar el diagnostico desde el estado 'No reparable'."
                    )
                )
            repair.write(
                {
                    "state": "done",
                    "product_location_src_id": (
                        repair._get_not_repairable_finish_location().id
                    ),
                }
            )
        return True

    def action_budget_reestimate(self):
        for repair in self:
            if not repair._can_reestimate_budget():
                raise UserError(
                    _(
                        "No se puede volver a presupuestar en el estado actual."
                    )
                )
            if (
                repair._needs_budget_reestimate_sale_order_reset()
                and not self.env.context.get(
                    "skip_budget_reestimate_quote_reset_confirm"
                )
            ):
                return repair._open_budget_workflow_confirm_wizard(
                    "reestimate_budget_reset_quote",
                    repair._get_budget_reestimate_quote_reset_confirm_message(),
                )
            repair._reopen_budget_sale_order_for_reestimate()
        result = self._set_budget_stage("estimating")
        self._sync_location_for_budget_stage()
        return result

    def action_mark_ready_for_pickup_from_glue(self):
        for repair in self:
            if repair.state != "done":
                raise UserError(
                    _(
                        "Solo puedes usar esta accion en reparaciones finalizadas."
                    )
                )
            if not repair.x_is_in_glue_desk:
                raise UserError(_("La reparacion no esta actualmente en Mesa Pegado."))

            pickup_location = repair.company_id.x_repair_state_location_done_id
            if not pickup_location:
                raise UserError(
                    _(
                        "Configura primero la ubicacion 'Finalizada' en Ajustes > Wexplay SAT."
                    )
                )

            repair.write({"product_location_src_id": pickup_location.id})
        return True

    def action_set_waiting_spare(self):
        for repair in self:
            repair._check_can_set_waiting_spare()

            if repair.x_is_waiting_spare_location:
                return True

            if repair._should_open_waiting_spare_confirm():
                return repair._open_waiting_spare_confirm_wizard()

        return self._set_waiting_spare_location()

    # ---------------------------------------------------------
    # Proteccion del flujo estandar de reparacion
    # ---------------------------------------------------------

    def action_repair_start(self):
        for repair in self:
            if repair.x_budget_stage in (
                "estimating",
                "waiting_customer",
                "not_repairable",
            ):
                raise UserError(
                    _(
                        "No se puede iniciar la reparacion mientras el diagnostico o presupuesto no permita reparar."
                    )
                )
        return super().action_repair_start()

    def action_repair_end(self):
        self.ensure_one()
        if self.env.context.get("skip_glue_finish_wizard"):
            return super().action_repair_end()
        if self._requires_glue_choice_on_finish():
            return self._open_glue_finish_wizard()
        return super().action_repair_end()

    # ---------------------------------------------------------
    # Sincronizacion robusta sobre cambios de state
    # ---------------------------------------------------------

    def _mark_budget_rejected_on_cancel(self):
        to_reject = self.filtered(
            lambda repair: repair.x_budget_stage not in ("rejected", "not_repairable")
        )
        if to_reject:
            now = fields.Datetime.now()
            to_reject.write(
                {
                    "x_budget_stage": "rejected",
                    "x_budget_resolved_at": now,
                }
            )

    def _handle_state_write_side_effects(self, new_state):
        if self.env.context.get("skip_repair_state_location_sync"):
            return

        if new_state == "cancel":
            self._mark_budget_rejected_on_cancel()
            self._sync_location_for_budget_stage()
            return

        if new_state in ("under_repair", "done", "delivered"):
            self._sync_location_for_repair_state()

    def write(self, vals):
        state_will_change = "state" in vals
        new_state = vals.get("state")
        result = super().write(vals)
        if state_will_change:
            self._handle_state_write_side_effects(new_state)
        return result
