# -*- coding: utf-8 -*-

from odoo import _, fields, models, api
from odoo.exceptions import UserError


class RepairOrder(models.Model):
    _inherit = "repair.order"

    x_budget_stage = fields.Selection(
        [
            ("none", "Sin presupuesto"),
            ("estimating", "Revisión"),
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
        string="Está en Mesa Pegado",
        compute="_compute_x_is_in_glue_desk",
        store=False,
    )

    x_is_waiting_spare_location = fields.Boolean(
        string="Está en Pendiente de repuesto",
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

    def _is_budget_transition_allowed(self, new_stage):
        self.ensure_one()

        current_stage = self.x_budget_stage or "none"
        allowed = self._BUDGET_TRANSITIONS.get(current_stage, set())

        if new_stage not in allowed:
            return False

        if (
            current_stage == "rejected"
            and new_stage == "estimating"
            and self.state == "cancel"
        ):
            return False

        return True

    def _prepare_budget_stage_vals(self, new_stage):
        self.ensure_one()

        if not self._is_budget_transition_allowed(new_stage):
            raise UserError(
                _(
                    "Transición de presupuesto no permitida: %(current)s → %(new)s."
                )
                % {
                    "current": dict(self._fields["x_budget_stage"].selection).get(
                        self.x_budget_stage, self.x_budget_stage
                    ),
                    "new": dict(self._fields["x_budget_stage"].selection).get(
                        new_stage, new_stage
                    ),
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
            vals = repair._prepare_budget_stage_vals(new_stage)
            repair.write(vals)
        return True

    # ---------------------------------------------------------
    # Helpers de ubicación SAT
    # ---------------------------------------------------------

    def _get_budget_stage_target_location(self, stage):
        self.ensure_one()
        company = self.company_id

        mapping = {
            "estimating": company.x_repair_budget_location_estimating_id,
            "waiting_customer": company.x_repair_budget_location_waiting_customer_id,
            "accepted": company.x_repair_budget_location_accepted_id,
            "rejected": company.x_repair_budget_location_rejected_id,
        }
        return mapping.get(stage)

    def _get_repair_state_target_location(self, state):
        self.ensure_one()
        company = self.company_id

        mapping = {
            "under_repair": company.x_repair_state_location_under_repair_id,
            "done": company.x_repair_state_location_done_id,
            "delivered": company.x_repair_state_location_delivered_id,
            "cancel": company.x_repair_budget_location_rejected_id,
        }
        return mapping.get(state)

    def _sync_location_from_budget_stage(self):
        for repair in self:
            target_location = repair._get_budget_stage_target_location(
                repair.x_budget_stage
            )
            if target_location and repair.product_location_src_id != target_location:
                repair.write({"product_location_src_id": target_location.id})

    def _sync_location_from_repair_state(self):
        for repair in self:
            target_location = repair._get_repair_state_target_location(repair.state)
            if target_location and repair.product_location_src_id != target_location:
                repair.write({"product_location_src_id": target_location.id})

    def _requires_glue_choice_on_finish(self):
        self.ensure_one()

        if not self.x_device_type:
            raise UserError(
                _("Debes indicar el Tipo de dispositivo antes de finalizar la reparación.")
            )

        return self.x_device_type in ("mobile", "tablet")

    def _open_glue_finish_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Ubicación final de la reparación"),
            "res_model": "wex.finish.repair.glue.choice.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_repair_id": self.id,
            },
        }

    def _open_waiting_spare_confirm_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Confirmar pendiente de repuesto"),
            "res_model": "wex.waiting.spare.confirm.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_repair_id": self.id,
            },
        }

    def _set_waiting_spare_location(self):
        for repair in self:
            waiting_location = repair.company_id.x_repair_state_location_waiting_spare_id
            if not waiting_location:
                raise UserError(
                    _("Configura primero la ubicación 'Pendiente de repuesto' en Ajustes > Wexplay SAT.")
                )

            vals = {"product_location_src_id": waiting_location.id}
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

    # ---------------------------------------------------------
    # Acciones del workflow
    # ---------------------------------------------------------

    def action_start_budget(self):
        for repair in self:
            if not repair._can_start_budget():
                raise UserError(
                    _("No se puede iniciar el presupuesto en el estado actual.")
                )
        res = self._set_budget_stage("estimating")
        self._sync_location_from_budget_stage()
        return res

    def action_budget_wait_customer(self):
        for repair in self:
            if not repair._can_wait_customer():
                raise UserError(
                    _("Solo se puede pasar a espera de cliente desde 'Revisión'.")
                )
        res = self._set_budget_stage("waiting_customer")
        self._sync_location_from_budget_stage()
        return res

    def action_budget_accept(self):
        for repair in self:
            if not repair._can_accept_budget():
                raise UserError(
                    _("Solo se puede aceptar un presupuesto que esté esperando al cliente.")
                )
        res = self._set_budget_stage("accepted")
        self._sync_location_from_budget_stage()
        return res

    def action_budget_reject(self):
        for repair in self:
            if not repair._can_reject_budget():
                raise UserError(
                    _("Solo se puede rechazar un presupuesto que esté esperando al cliente.")
                )
        res = self._set_budget_stage("rejected")
        self._sync_location_from_budget_stage()
        return res

    def action_budget_reestimate(self):
        for repair in self:
            if not repair._can_reestimate_budget():
                raise UserError(
                    _("No se puede volver a presupuestar en el estado actual.")
                )
        res = self._set_budget_stage("estimating")
        self._sync_location_from_budget_stage()
        return res

    def action_mark_ready_for_pickup_from_glue(self):
        for repair in self:
            if repair.state != "done":
                raise UserError(
                    _("Solo puedes usar esta acción en reparaciones finalizadas.")
                )
            if not repair.x_is_in_glue_desk:
                raise UserError(_("La reparación no está actualmente en Mesa Pegado."))

            pickup_location = repair.company_id.x_repair_state_location_done_id
            if not pickup_location:
                raise UserError(
                    _("Configura primero la ubicación 'Finalizada' en Ajustes > Wexplay SAT.")
                )

            repair.write({"product_location_src_id": pickup_location.id})
        return True

    def action_set_waiting_spare(self):
        for repair in self:
            if repair.state in ("cancel", "delivered"):
                raise UserError(
                    _("No puedes marcar una reparación cancelada o entregada como pendiente de repuesto.")
                )

            if repair.x_is_waiting_spare_location:
                return True

            if (
                not self.env.context.get("skip_waiting_spare_confirm")
                and not repair.move_ids
            ):
                return repair._open_waiting_spare_confirm_wizard()

        return self._set_waiting_spare_location()

    # ---------------------------------------------------------
    # Protección del flujo estándar de reparación
    # ---------------------------------------------------------

    def action_repair_start(self):
        for repair in self:
            if repair.x_budget_stage in ("estimating", "waiting_customer"):
                raise UserError(
                    _("No se puede iniciar la reparación mientras el presupuesto esté abierto.")
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
    # Sincronización robusta sobre cambios de state
    # ---------------------------------------------------------

    def write(self, vals):
        state_will_change = "state" in vals
        new_state = vals.get("state")

        res = super().write(vals)

        if state_will_change:
            if new_state == "cancel":
                to_reject = self.filtered(lambda r: r.x_budget_stage != "rejected")
                if to_reject:
                    now = fields.Datetime.now()
                    to_reject.write(
                        {
                            "x_budget_stage": "rejected",
                            "x_budget_resolved_at": now,
                        }
                    )
                self._sync_location_from_budget_stage()

            elif new_state in ("under_repair", "done", "delivered"):
                self._sync_location_from_repair_state()

        return res