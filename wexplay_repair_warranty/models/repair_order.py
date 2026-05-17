# -*- coding: utf-8 -*-

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError, UserError


class RepairOrder(models.Model):
    _inherit = "repair.order"

    x_is_warranty_case = fields.Boolean(
        string="Caso de garantía",
        default=False,
        copy=False,
        index=True,
        tracking=True,
        readonly=True,
    )
    x_warranty_origin_repair_id = fields.Many2one(
        "repair.order",
        string="SAT origen de garantía",
        copy=False,
        index=True,
        ondelete="restrict",
    )
    x_warranty_origin_repair_name = fields.Char(
        string="Nombre SAT origen",
        related="x_warranty_origin_repair_id.name",
        readonly=True,
    )
    x_warranty_child_ids = fields.One2many(
        "repair.order",
        "x_warranty_origin_repair_id",
        string="Garantías hijas",
    )
    x_warranty_child_count = fields.Integer(
        string="Número de garantías hijas",
        compute="_compute_x_warranty_child_count",
        store=True,
    )

    x_force_no_warranty = fields.Boolean(
        string="Forzar sin garantía",
        default=False,
        copy=False,
        tracking=True,
    )
    x_force_warranty_claim = fields.Boolean(
        string="Tramitar como garantía de todos modos",
        default=False,
        copy=False,
        tracking=True,
    )
    x_warranty_parts_months = fields.Integer(
        string="Meses garantía piezas",
        default=0,
        copy=False,
    )
    x_warranty_labor_months = fields.Integer(
        string="Meses garantía mano de obra",
        default=0,
        copy=False,
    )
    x_warranty_source_invoice_id = fields.Many2one(
        "account.move",
        string="Factura base",
        copy=False,
        readonly=True,
    )
    x_warranty_source_invoice_date = fields.Date(
        string="Fecha factura base",
        copy=False,
        readonly=True,
    )

    x_warranty_parts_deadline = fields.Date(
        string="Límite garantía piezas",
        compute="_compute_warranty_state",
    )
    x_warranty_labor_deadline = fields.Date(
        string="Límite garantía mano de obra",
        compute="_compute_warranty_state",
    )
    x_is_parts_under_warranty = fields.Boolean(
        string="Piezas en garantía",
        compute="_compute_warranty_state",
    )
    x_is_labor_under_warranty = fields.Boolean(
        string="Mano de obra en garantía",
        compute="_compute_warranty_state",
    )
    x_is_any_warranty_valid = fields.Boolean(
        string="Tiene alguna garantía vigente",
        compute="_compute_warranty_state",
    )
    x_warranty_status = fields.Selection(
        [
            ("none", "Sin garantía"),
            ("valid", "En garantía"),
            ("expired", "Fuera de garantía"),
            ("forced_no_warranty", "Sin garantía"),
        ],
        string="Estado de garantía",
        compute="_compute_warranty_state",
    )
    x_show_warranty_status = fields.Boolean(
        string="Mostrar estado de garantía",
        compute="_compute_warranty_state",
    )
    x_can_override_expired_warranty = fields.Boolean(
        string="Puede forzar garantía caducada",
        compute="_compute_x_can_override_expired_warranty",
    )
    x_warranty_budget_stage = fields.Selection(
        [
            ("none", "Sin revisión"),
            ("estimating", "Revisión"),
            ("waiting_customer", "Espera Cliente"),
            ("accepted", "Garantía aprobada"),
            ("rejected", "Garantía rechazada"),
            ("not_repairable", "No reparable"),
        ],
        string="Estado de revisión de garantía",
        compute="_compute_x_warranty_budget_stage",
    )

    @api.depends("x_warranty_child_ids")
    def _compute_x_warranty_child_count(self):
        for repair in self:
            repair.x_warranty_child_count = len(repair.x_warranty_child_ids)

    @api.depends("x_budget_stage")
    def _compute_x_warranty_budget_stage(self):
        for repair in self:
            repair.x_warranty_budget_stage = repair.x_budget_stage

    def _compute_x_can_override_expired_warranty(self):
        for repair in self:
            repair.x_can_override_expired_warranty = repair._can_override_expired_warranty()

    @api.depends(
        "x_force_no_warranty",
        "x_is_warranty_case",
        "x_warranty_parts_months",
        "x_warranty_labor_months",
        "x_warranty_source_invoice_id",
        "x_warranty_source_invoice_date",
        "state",
    )
    def _compute_warranty_state(self):
        for repair in self:
            parts_deadline = repair._get_warranty_deadline(
                repair.x_warranty_source_invoice_date,
                repair.x_warranty_parts_months,
            )
            labor_deadline = repair._get_warranty_deadline(
                repair.x_warranty_source_invoice_date,
                repair.x_warranty_labor_months,
            )
            is_parts_valid = repair._is_deadline_valid(parts_deadline)
            is_labor_valid = repair._is_deadline_valid(labor_deadline)

            repair.x_warranty_parts_deadline = parts_deadline
            repair.x_warranty_labor_deadline = labor_deadline
            repair.x_is_parts_under_warranty = is_parts_valid
            repair.x_is_labor_under_warranty = is_labor_valid
            repair.x_is_any_warranty_valid = is_parts_valid or is_labor_valid
            repair.x_warranty_status = repair._get_warranty_status_value(
                is_parts_valid,
                is_labor_valid,
            )
            repair.x_show_warranty_status = repair._get_show_warranty_status_value()

    def _get_show_warranty_status_value(self):
        self.ensure_one()
        if self.x_is_warranty_case:
            return True
        return bool(
            self.state in ("done", "delivered")
            and self.x_warranty_source_invoice_id
        )

    @api.constrains("x_force_no_warranty", "x_force_warranty_claim")
    def _check_warranty_force_flags(self):
        for repair in self:
            if repair.x_force_no_warranty and repair.x_force_warranty_claim:
                raise ValidationError(
                    _("No puede forzar garantía y forzar sin garantía al mismo tiempo.")
                )

    def _get_warranty_status_value(self, is_parts_valid, is_labor_valid):
        self.ensure_one()

        if self.x_force_no_warranty:
            return "forced_no_warranty"
        if not self.x_warranty_parts_months and not self.x_warranty_labor_months:
            return "none"
        if is_parts_valid or is_labor_valid:
            return "valid"
        return "expired"

    def _is_deadline_valid(self, deadline):
        self.ensure_one()
        return bool(deadline and deadline >= fields.Date.context_today(self))

    def _get_warranty_deadline(self, source_date, months):
        self.ensure_one()
        if not source_date or months <= 0:
            return False
        return source_date + relativedelta(months=months)

    def _get_warranty_service_lines(self):
        self.ensure_one()
        return self.repair_service_ids.filtered(
            lambda line: (
                line.product_id
                and line.product_id.product_tmpl_id
                and line.product_id.product_tmpl_id.type == "service"
            )
        )

    def _get_warranty_months_from_service_line(self, service_line):
        self.ensure_one()
        product = service_line.product_id.product_tmpl_id
        return (
            product.x_warranty_parts_months or 0,
            product.x_warranty_labor_months or 0,
        )

    def _get_warranty_service_total_coverage(self, service_line):
        self.ensure_one()
        parts_months, labor_months = self._get_warranty_months_from_service_line(service_line)
        return parts_months + labor_months

    def _get_best_warranty_service(self):
        self.ensure_one()

        best_line = self.repair_service_ids[:0]
        best_total = -1

        for service_line in self._get_warranty_service_lines():
            coverage_total = self._get_warranty_service_total_coverage(service_line)
            if coverage_total > best_total:
                best_line = service_line
                best_total = coverage_total

        return best_line

    def _get_posted_customer_invoices(self):
        self.ensure_one()
        if not self.sale_order_id:
            return self.env["account.move"]

        return self.env["account.move"].search(
            [
                ("move_type", "=", "out_invoice"),
                ("state", "=", "posted"),
                ("invoice_line_ids.sale_line_ids.order_id", "=", self.sale_order_id.id),
            ],
            order="invoice_date asc, id asc",
        )

    def _get_warranty_source_invoice(self):
        self.ensure_one()
        return self._get_posted_customer_invoices()[:1]

    def _prepare_warranty_snapshot_vals(self, invoice=False):
        self.ensure_one()

        invoice = invoice or self._get_warranty_source_invoice()
        service_line = self._get_best_warranty_service()
        parts_months, labor_months = (
            self._get_warranty_months_from_service_line(service_line)
            if service_line
            else (0, 0)
        )

        if self._is_manually_forced_no_warranty():
            parts_months = 0
            labor_months = 0

        return {
            "x_warranty_parts_months": parts_months,
            "x_warranty_labor_months": labor_months,
            "x_warranty_source_invoice_id": invoice.id if invoice else False,
            "x_warranty_source_invoice_date": invoice.invoice_date if invoice else False,
        }

    def _apply_warranty_snapshot(self, force=False):
        for repair in self.filtered(lambda rec: not rec.x_is_warranty_case):
            if (
                not force
                and repair.x_warranty_source_invoice_id
                and not repair._is_manually_forced_no_warranty()
            ):
                continue

            vals = repair._prepare_warranty_snapshot_vals()
            repair.with_context(skip_warranty_snapshot_refresh=True).write(vals)

    def _refresh_warranty_snapshot(self, force=False):
        self._apply_warranty_snapshot(force=force)

    def _is_manually_forced_no_warranty(self):
        self.ensure_one()
        return bool(self.x_force_no_warranty)

    def _is_warranty_claim_forced(self):
        self.ensure_one()
        return bool(self.x_force_warranty_claim)

    def _has_warranty_snapshot(self):
        self.ensure_one()
        return bool(
            self.x_warranty_source_invoice_id
            and (self.x_warranty_parts_months or self.x_warranty_labor_months)
        )

    def _can_override_expired_warranty(self):
        self.ensure_one()
        return self.env.user.has_group(
            "wexplay_repair_warranty.group_wex_repair_warranty_override_expired"
        )

    def _can_claim_warranty(self):
        self.ensure_one()
        if self.x_is_warranty_case:
            return False
        if self._is_manually_forced_no_warranty():
            return False
        return self._has_warranty_snapshot()

    def _should_confirm_wait_customer_without_sale_order(self):
        self.ensure_one()
        if self.x_is_warranty_case:
            return False
        return super()._should_confirm_wait_customer_without_sale_order()

    def _requires_budget_sale_order_for_accept(self):
        self.ensure_one()
        if self.x_is_warranty_case:
            return False
        return super()._requires_budget_sale_order_for_accept()

    def _should_confirm_budget_sale_order_on_accept(self):
        self.ensure_one()
        if self.x_is_warranty_case:
            return False
        return super()._should_confirm_budget_sale_order_on_accept()

    def _should_manage_sale_order_on_budget_reject(self):
        self.ensure_one()
        if self.x_is_warranty_case:
            return False
        return super()._should_manage_sale_order_on_budget_reject()

    def _should_reset_sale_order_on_budget_reestimate(self):
        self.ensure_one()
        if self.x_is_warranty_case:
            return False
        return super()._should_reset_sale_order_on_budget_reestimate()

    def _get_budget_reject_confirm_message(self):
        self.ensure_one()
        if self.x_is_warranty_case:
            return _("Vas a rechazar esta garantia. ¿Deseas continuar?")
        return super()._get_budget_reject_confirm_message()

    def _get_budget_stage_location_setting_field(self, stage):
        self.ensure_one()
        mapping = {
            "estimating": "x_repair_budget_location_estimating_id",
            "waiting_customer": "x_repair_budget_location_waiting_customer_id",
            "accepted": "x_repair_budget_location_accepted_id",
            "rejected": "x_repair_budget_location_rejected_id",
        }
        return mapping.get(stage)

    def _get_budget_stage_location_label(self, stage):
        self.ensure_one()
        labels = dict(self._fields["x_budget_stage"].selection)
        return labels.get(stage, stage)

    def _check_budget_stage_target_location_configured(self):
        for repair in self:
            stage = repair.x_budget_stage
            setting_field = repair._get_budget_stage_location_setting_field(stage)
            if not setting_field:
                continue

            target_location = repair.company_id[setting_field]
            if target_location:
                continue

            raise UserError(
                _(
                    "Falta configurar la ubicación SAT para '%(stage)s' en Ajustes > Wexplay SAT."
                )
                % {"stage": repair._get_budget_stage_location_label(stage)}
            )

    def _check_waiting_spare_location_configured(self):
        for repair in self:
            waiting_location = repair.company_id.x_repair_state_location_waiting_spare_id
            if waiting_location:
                continue
            raise UserError(
                _(
                    "Configura primero la ubicación 'Pendiente de repuesto' en Ajustes > Wexplay SAT."
                )
            )

    def _set_budget_stage(self, new_stage):
        res = super()._set_budget_stage(new_stage)
        self._check_budget_stage_target_location_configured()
        return res

    def _set_waiting_spare_location(self):
        self._check_waiting_spare_location_configured()
        return super()._set_waiting_spare_location()

    def _check_can_claim_warranty(self):
        self.ensure_one()

        if self.x_is_warranty_case:
            raise UserError(_("Una garantía no puede generar otra garantía."))
        if self._is_manually_forced_no_warranty():
            raise UserError(_("Este SAT se ha marcado manualmente como sin garantía."))
        if not self.x_warranty_source_invoice_id:
            raise UserError(_("No se ha encontrado ninguna factura de cliente publicada para este SAT."))
        if not self.x_warranty_parts_months and not self.x_warranty_labor_months:
            raise UserError(_("Este SAT no tiene cobertura de garantía para tramitar."))

    def _get_warranty_priority_value(self):
        self.ensure_one()
        return "warranty" if "x_sat_priority" in self._fields else False

    def _prepare_warranty_child_vals(self):
        self.ensure_one()

        vals = {
            "name": self.env["ir.sequence"].next_by_code("repair.order.warranty.rma")
            or _("Nuevo"),
            "partner_id": self.partner_id.id,
            "product_id": self.product_id.id,
            "company_id": self.company_id.id,
            "product_qty": self.product_qty,
            "product_uom": self.product_uom.id,
            "picking_type_id": self.picking_type_id.id,
            "location_id": self.location_id.id,
            "product_location_src_id": self.product_location_src_id.id,
            "x_device_type": self.x_device_type,
            "x_brand": self.x_brand,
            "x_model": self.x_model,
            "x_model_id": self.x_model_id.id,
            "x_imei": self.x_imei,
            "x_reported_issue": self.x_reported_issue,
            "x_unlock_type": self.x_unlock_type,
            "x_unlock_code": self.x_unlock_code,
            "x_unlock_pattern": self.x_unlock_pattern,
            "x_unlock_notes": self.x_unlock_notes,
            "under_warranty": True,
            "x_is_warranty_case": True,
            "x_warranty_origin_repair_id": self.id,
            "x_warranty_parts_months": self.x_warranty_parts_months,
            "x_warranty_labor_months": self.x_warranty_labor_months,
            "x_warranty_source_invoice_id": self.x_warranty_source_invoice_id.id,
            "x_warranty_source_invoice_date": self.x_warranty_source_invoice_date,
        }

        priority_value = self._get_warranty_priority_value()
        if priority_value:
            vals["x_sat_priority"] = priority_value

        return vals

    def _create_warranty_child_repair(self):
        self.ensure_one()
        self._check_can_claim_warranty()
        return self.create(self._prepare_warranty_child_vals())

    def action_view_warranty_children(self):
        self.ensure_one()
        action = {
            "type": "ir.actions.act_window",
            "name": _("Garantías SAT"),
            "res_model": "repair.order",
            "view_mode": "list,form",
            "domain": [("id", "in", self.x_warranty_child_ids.ids)],
            "context": {
                "search_default_warranty_cases": 1,
                "default_x_warranty_origin_repair_id": self.id,
            },
        }
        if len(self.x_warranty_child_ids) == 1:
            action.update(
                {
                    "view_mode": "form",
                    "res_id": self.x_warranty_child_ids.id,
                }
            )
        return action

    def action_view_warranty_origin(self):
        self.ensure_one()
        if not self.x_warranty_origin_repair_id:
            raise UserError(_("Esta garantía no tiene un SAT origen vinculado."))

        return {
            "type": "ir.actions.act_window",
            "name": _("SAT origen"),
            "res_model": "repair.order",
            "view_mode": "form",
            "res_id": self.x_warranty_origin_repair_id.id,
        }

    def action_open_warranty_claim_wizard(self):
        self.ensure_one()
        self._check_can_claim_warranty()

        return {
            "type": "ir.actions.act_window",
            "name": _("Tramitar garantía"),
            "res_model": "wex.repair.warranty.claim.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_repair_id": self.id,
            },
        }

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("x_is_warranty_case"):
                continue

            current_name = vals.get("name")
            if current_name and current_name != _("Nuevo"):
                continue

            vals["name"] = self.env["ir.sequence"].next_by_code("repair.order.warranty.rma") or _(
                "Nuevo"
            )

        repairs = super().create(vals_list)
        repairs.filtered(lambda rec: not rec.x_is_warranty_case)._refresh_warranty_snapshot()
        return repairs

    def write(self, vals):
        if vals.get("x_force_warranty_claim"):
            unauthorized_repairs = self.filtered(
                lambda repair: not repair._can_override_expired_warranty()
            )
            if unauthorized_repairs:
                raise UserError(
                    _(
                        "No tiene permisos para forzar la tramitación de una garantía caducada."
                    )
                )

        if "x_is_warranty_case" in vals:
            vals.pop("x_is_warranty_case")

        res = super().write(vals)

        if self.env.context.get("skip_warranty_snapshot_refresh"):
            return res

        if {"sale_order_id", "repair_service_ids"}.intersection(vals):
            self._refresh_warranty_snapshot()

        if "x_force_no_warranty" in vals:
            self._refresh_warranty_snapshot(force=True)

        return res
