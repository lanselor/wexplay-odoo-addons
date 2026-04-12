# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class RepairOrder(models.Model):
    _inherit = "repair.order"

    x_budget_stage = fields.Selection(
        [
            ("none", "Sin presupuesto"),
            ("estimating", "Revision"),
            ("waiting_customer", "Esperando cliente"),
            ("accepted", "Aceptado"),
            ("rejected", "Rechazado"),
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
        "estimating": {"waiting_customer"},
        "waiting_customer": {"accepted", "rejected", "estimating"},
        "accepted": {"estimating"},
        "rejected": {"estimating"},
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
            current_stage == "rejected"
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
        if new_stage in ("accepted", "rejected"):
            vals["x_budget_resolved_at"] = fields.Datetime.now()
        return vals

    def _set_budget_stage(self, new_stage):
        for repair in self:
            repair.write(repair._prepare_budget_stage_vals(new_stage))
        return True

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
        for repair in self:
            repair._set_product_location_if_needed(
                repair._get_target_location_from_budget_stage(repair.x_budget_stage)
            )

    def _sync_location_for_repair_state(self):
        for repair in self:
            repair._set_product_location_if_needed(
                repair._get_target_location_from_repair_state(repair.state)
            )

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
            self.state not in ("done", "delivered")
            and (
                self.x_budget_stage == "waiting_customer"
                or self.x_budget_stage == "accepted"
                or (self.x_budget_stage == "rejected" and self.state != "cancel")
            )
        )

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
        result = self._set_budget_stage("rejected")
        self._sync_location_for_budget_stage()
        return result

    def action_budget_reestimate(self):
        for repair in self:
            if not repair._can_reestimate_budget():
                raise UserError(
                    _(
                        "No se puede volver a presupuestar en el estado actual."
                    )
                )
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
            if repair.x_budget_stage in ("estimating", "waiting_customer"):
                raise UserError(
                    _(
                        "No se puede iniciar la reparacion mientras el presupuesto este abierto."
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
        to_reject = self.filtered(lambda repair: repair.x_budget_stage != "rejected")
        if to_reject:
            now = fields.Datetime.now()
            to_reject.write(
                {
                    "x_budget_stage": "rejected",
                    "x_budget_resolved_at": now,
                }
            )

    def _handle_state_write_side_effects(self, new_state):
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
