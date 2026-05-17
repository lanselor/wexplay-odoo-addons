import re
import unicodedata

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.osv import expression

from odoo.addons.wexplay_repair.models.device_constants import DEVICE_TYPE_SELECTION

try:
    from rapidfuzz import fuzz, process
except ImportError:  # pragma: no cover - controlado por external_dependencies
    fuzz = None
    process = None


class WexTeardownLine(models.Model):
    _name = "wex.teardown.line"
    _description = "Linea de despiece"
    _order = "batch_id, id"
    _rec_name = "name_final"

    batch_id = fields.Many2one(
        "wex.teardown.batch",
        string="Despiece",
        required=True,
        ondelete="cascade",
        index=True,
    )
    company_id = fields.Many2one(related="batch_id.company_id", string="Compañía", store=True, readonly=True)
    device_type = fields.Selection(
        related="batch_id.device_type",
        string="Tipo de dispositivo",
        store=True,
        readonly=True,
    )
    model_id = fields.Many2one(related="batch_id.model_id", string="Modelo", store=True, readonly=True)
    brand_id = fields.Many2one(related="batch_id.brand_id", string="Marca", store=True, readonly=True)
    component_type_id = fields.Many2one(
        "wex.teardown.component.type",
        string="Componente",
        required=True,
        domain="[('device_type', '=', device_type)]",
        ondelete="restrict",
    )
    part_number = fields.Char(string="Part number", index=True)
    quantity = fields.Float(string="Cantidad", default=1.0, required=True)
    missing_part_number_confirmed = fields.Boolean(string="Part number ausente confirmado", copy=False)
    product_category_id = fields.Many2one(
        related="component_type_id.product_category_id",
        string="Categoría",
        store=True,
        readonly=True,
    )
    product_tmpl_id = fields.Many2one("product.template", string="Producto creado", readonly=True, copy=False)
    existing_product_id = fields.Many2one("product.template", string="Producto existente")
    existing_product_update_name = fields.Boolean(string="Actualizar nombre producto existente", copy=False)

    duplicate_status = fields.Selection(
        [
            ("none", "Sin coincidencias"),
            ("exact", "Coincidencia exacta"),
            ("partial", "Coincidencia parcial"),
            ("model", "Coincidencia por modelo"),
        ],
        string="Coincidencia",
        default="none",
        copy=False,
    )
    duplicate_message = fields.Text(string="Detalle de coincidencias", copy=False)
    duplicate_checked_at = fields.Datetime(string="Coincidencias revisadas el", copy=False, readonly=True)
    decision = fields.Selection(
        [
            ("pending", "Pendiente"),
            ("use_existing", "Usar existente"),
            ("create_new", "Crear nuevo"),
            ("discard", "Descartar"),
        ],
        string="Decisión",
        default="pending",
        required=True,
    )
    state = fields.Selection(
        [
            ("draft", "Borrador"),
            ("warning", "Advertencia"),
            ("ready", "Lista"),
            ("created", "Creada"),
            ("discarded", "Descartada"),
            ("error", "Error"),
        ],
        string="Estado",
        default="draft",
        required=True,
        copy=False,
    )
    discard_reason = fields.Selection(
        [
            ("broken", "Rota"),
            ("missing", "No recuperada"),
            ("not_useful", "No util"),
            ("duplicate", "Duplicada"),
            ("other", "Otro"),
        ],
        string="Motivo de descarte",
    )
    discard_notes = fields.Text(string="Notas de descarte")

    name_suggested = fields.Char(string="Nombre sugerido", compute="_compute_name_suggested", store=True)
    name_final = fields.Char(string="Nombre final")
    name_manual_locked = fields.Boolean(string="Nombre bloqueado manualmente")
    pvp_tax_included = fields.Float(
        string="PVP IVA incluido",
        compute="_compute_pvp_tax_included",
        inverse="_inverse_pvp_tax_included",
    )
    list_price = fields.Float(string="Precio sin IVA")
    standard_price = fields.Float(string="Coste")
    tax_ids = fields.Many2many("account.tax", string="Impuestos")

    validation_status = fields.Selection(
        [("ok", "Correcto"), ("warning", "Advertencia"), ("error", "Error")],
        string="Estado de validación",
        default="warning",
        copy=False,
    )
    validation_message = fields.Text(string="Mensaje de validación", copy=False)
    label_printed = fields.Boolean(string="Etiqueta impresa", readonly=True, copy=False)
    label_printed_at = fields.Datetime(string="Fecha de impresión", readonly=True, copy=False)

    qc_state = fields.Selection(
        [
            ("pending", "Pendiente"),
            ("ok", "Apta"),
            ("fail", "No apta"),
            ("not_applicable", "No recuperada / No aplica"),
        ],
        string="Control de calidad",
        default="pending",
        required=True,
    )
    qc_notes = fields.Text(string="Notas de control de calidad")
    reviewed_by = fields.Many2one("res.users", string="Revisado por", readonly=True, copy=False)
    reviewed_at = fields.Datetime(string="Revisado el", readonly=True, copy=False)

    stock_move_id = fields.Many2one("stock.move", string="Movimiento de stock", readonly=True, copy=False)
    stock_ref = fields.Char(string="Referencia de stock", readonly=True, copy=False)

    _MATCH_STOPWORDS = {
        "de",
        "del",
        "la",
        "el",
        "los",
        "las",
        "para",
        "con",
        "sin",
        "movil",
        "smartphone",
        "tablet",
        "repuesto",
    }

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("tax_ids"):
                company = self.env["res.company"].browse(vals.get("company_id")) or self.env.company
                vals["tax_ids"] = [(6, 0, self.with_company(company)._get_default_sale_taxes_for_company().ids)]
        return super().create(vals_list)

    def write(self, vals):
        if self.env.context.get("wex_skip_qc_sync") or "qc_state" not in vals:
            return super().write(vals)
        for rec in self:
            rec_vals = dict(vals)
            rec_vals.update(rec._prepare_qc_flow_vals(vals["qc_state"]))
            super(WexTeardownLine, rec.with_context(wex_skip_qc_sync=True)).write(rec_vals)
        return True

    @api.depends(
        "component_type_id",
        "part_number",
        "device_type",
        "brand_id",
        "model_id",
        "component_type_id.name_pattern",
    )
    def _compute_name_suggested(self):
        for rec in self:
            if not rec.component_type_id:
                rec.name_suggested = False
                continue
            rec.name_suggested = rec.component_type_id.render_product_name(rec)
            if not rec.name_manual_locked:
                rec.name_final = rec.name_suggested

    @api.depends("list_price", "tax_ids")
    def _compute_pvp_tax_included(self):
        for rec in self:
            rec.pvp_tax_included = rec._get_price_included()

    def _inverse_pvp_tax_included(self):
        for rec in self:
            rec.list_price = rec._get_price_excluded(rec.pvp_tax_included)

    @api.onchange("part_number", "component_type_id")
    def _onchange_name_inputs(self):
        for rec in self:
            if rec.component_type_id:
                rec.name_suggested = rec.component_type_id.render_product_name(rec)
            if not rec.name_manual_locked:
                rec.name_final = rec.name_suggested

    @api.onchange("component_type_id")
    def _onchange_component_type_id_set_default_taxes(self):
        for rec in self:
            if not rec.tax_ids:
                rec.tax_ids = rec._get_default_sale_taxes()

    def action_check_duplicates(self):
        for rec in self:
            candidates = rec._get_duplicate_candidates()
            candidates = rec._refine_candidates_with_rapidfuzz(candidates)
            rec._set_duplicate_result(candidates)
        return True

    def action_mark_qc_ok(self):
        self._mark_qc("ok")
        return True

    def action_mark_qc_fail(self):
        self._mark_qc("fail")
        return True

    def action_mark_qc_not_applicable(self):
        self._mark_qc("not_applicable")
        return True

    def action_mark_qc_pending(self):
        self._mark_qc("pending")
        return True

    def action_discard(self):
        self.write({"decision": "discard", "state": "discarded"})
        return True

    def action_open_edit_form(self):
        self.ensure_one()
        form_view = self.env.ref("wex_teardown.view_wex_teardown_line_form", raise_if_not_found=False)
        return {
            "type": "ir.actions.act_window",
            "name": _("Revisar pieza"),
            "res_model": "wex.teardown.line",
            "res_id": self.id,
            "view_mode": "form",
            "views": [(form_view.id, "form")] if form_view else [(False, "form")],
            "target": "new",
            "context": {
                "form_view_initial_mode": "edit",
            },
        }

    def action_open_reject_wizard(self):
        self.ensure_one()
        form_view = self.env.ref("wex_teardown.view_wex_teardown_reject_wizard_form", raise_if_not_found=False)
        return {
            "type": "ir.actions.act_window",
            "name": _("Rechazar pieza"),
            "res_model": "wex.teardown.reject.wizard",
            "view_mode": "form",
            "views": [(form_view.id, "form")] if form_view else [(False, "form")],
            "target": "new",
            "context": {
                "default_line_id": self.id,
                "default_qc_state": "fail",
                "default_discard_reason": "broken",
            },
        }

    def action_save_operational_review(self, values):
        self.ensure_one()
        allowed_fields = {"part_number", "quantity", "name_final", "missing_part_number_confirmed"}
        vals = {field_name: values[field_name] for field_name in values if field_name in allowed_fields}
        if "quantity" in vals:
            vals["quantity"] = float(vals["quantity"] or 0.0)
        if "missing_part_number_confirmed" in vals:
            vals["missing_part_number_confirmed"] = bool(vals["missing_part_number_confirmed"])
        if "name_final" in vals:
            vals["name_manual_locked"] = vals["name_final"] != (self.name_suggested or "")
        if vals.get("part_number"):
            vals["missing_part_number_confirmed"] = False
        self.write(vals)
        return self._get_operational_row_data()

    def action_save_data_completion_review(self, values):
        self.ensure_one()
        allowed_fields = {"list_price", "standard_price", "tax_ids", "pvp_tax_included", "price_source"}
        vals = {field_name: values[field_name] for field_name in values if field_name in allowed_fields}
        price_source = vals.pop("price_source", False)
        if "list_price" in vals:
            vals["list_price"] = float(vals["list_price"] or 0.0)
        if "standard_price" in vals:
            vals["standard_price"] = float(vals["standard_price"] or 0.0)
        if "tax_ids" in vals:
            vals["tax_ids"] = [(6, 0, [int(tax_id) for tax_id in vals["tax_ids"] or []])]
        if vals:
            self.write(vals)
        if "pvp_tax_included" in values and price_source == "pvp":
            self.pvp_tax_included = float(values["pvp_tax_included"] or 0.0)
            if not vals.get("list_price") or abs(self.list_price - float(values.get("list_price") or 0.0)) > 0.0001:
                self.write({"list_price": self.list_price})
        if vals:
            self.invalidate_recordset(["list_price", "pvp_tax_included", "standard_price", "tax_ids"])
        return self._get_data_completion_row_data()

    def action_choose_existing_product(self, product_id, update_name=False):
        self.ensure_one()
        product = self.env["product.template"].browse(product_id).exists()
        if not product:
            raise UserError(_("No se ha encontrado el producto seleccionado."))
        generated_name = self.name_final or self.name_suggested or product.name
        vals = {
            "existing_product_id": product.id,
            "existing_product_update_name": bool(update_name),
            "decision": "use_existing",
            "name_final": generated_name if update_name else product.name,
            "name_manual_locked": bool(update_name and generated_name != (self.name_suggested or "")),
        }
        vals.update(self._prepare_existing_product_prefill_vals(product))
        self.write(vals)
        return self._get_operational_row_data()

    def action_open_existing_product(self, product_id):
        product = self.env["product.template"].browse(product_id).exists()
        if not product:
            raise UserError(_("No se ha encontrado el producto solicitado."))
        form_view = self.env.ref("product.product_template_only_form_view", raise_if_not_found=False)
        return {
            "type": "ir.actions.act_window",
            "name": _("Producto coincidente"),
            "res_model": "product.template",
            "res_id": product.id,
            "view_mode": "form",
            "views": [(form_view.id, "form")] if form_view else [(False, "form")],
            "target": "current",
        }

    def action_regenerate_name(self):
        for rec in self:
            rec.name_manual_locked = False
            rec.name_final = rec.name_suggested
        return True

    def action_unlock_manual_name(self):
        self.write({"name_manual_locked": True})
        return True

    def action_create_or_update_product(self):
        for rec in self:
            try:
                rec._process_product()
            except Exception as error:
                rec.write(
                    {
                        "state": "error",
                        "validation_status": "error",
                        "validation_message": str(error),
                    }
                )
                rec.batch_id.message_post(body=_("Error en linea %s: %s") % (rec.display_name, error))
        return True

    def _mark_qc(self, qc_state):
        for rec in self:
            vals = {
                "qc_state": qc_state,
                "reviewed_by": self.env.user.id,
                "reviewed_at": fields.Datetime.now(),
            }
            vals.update(rec._prepare_qc_flow_vals(qc_state))
            rec.write(vals)

    def _prepare_qc_flow_vals(self, qc_state):
        self.ensure_one()
        if qc_state == "fail":
            return {"decision": "discard", "state": "discarded", "discard_reason": "broken"}
        if qc_state == "not_applicable":
            return {"decision": "discard", "state": "discarded", "discard_reason": "missing"}
        if qc_state in ("pending", "ok") and self.state == "discarded":
            return {"decision": "pending", "state": "draft", "discard_reason": False}
        return {}

    def _get_operational_row_data(self):
        self.ensure_one()
        candidates = self._serialize_operational_candidates()
        primary_candidate = candidates[0] if candidates else False
        secondary_candidates = candidates[1:] if len(candidates) > 1 else []
        decision_labels = dict(self._fields["decision"].selection)
        return {
            "id": self.id,
            "component_name": self.component_type_id.display_name,
            "part_number": self.part_number or "",
            "quantity": self.quantity,
            "name_final": self.name_final or "",
            "name_suggested": self.name_final or self.name_suggested or "",
            "missing_part_number_confirmed": self.missing_part_number_confirmed,
            "state": self.state,
            "state_label": dict(self._fields["state"].selection).get(self.state, self.state),
            "qc_state": self.qc_state,
            "duplicate_status": self.duplicate_status,
            "duplicate_status_label": dict(self._fields["duplicate_status"].selection).get(self.duplicate_status, ""),
            "name_manual_locked": self.name_manual_locked,
            "decision": self.decision,
            "decision_label": decision_labels.get(self.decision, ""),
            "existing_product_id": self.existing_product_id.id,
            "existing_product_name": self.existing_product_id.display_name or "",
            "existing_product_update_name": self.existing_product_update_name,
            "primary_candidate": primary_candidate,
            "secondary_candidates": secondary_candidates,
        }

    def _get_data_completion_row_data(self):
        self.ensure_one()
        return {
            "id": self.id,
            "component_name": self.component_type_id.display_name,
            "part_number": self.part_number or "",
            "quantity": self.quantity,
            "name_suggested": self.name_final or self.name_suggested or "",
            "decision": self.decision,
            "decision_label": dict(self._fields["decision"].selection).get(self.decision, ""),
            "state": self.state,
            "state_label": dict(self._fields["state"].selection).get(self.state, self.state),
            "existing_product_id": self.existing_product_id.id,
            "existing_product_name": self.existing_product_id.display_name or "",
            "existing_product_update_name": self.existing_product_update_name,
            "list_price": self.list_price,
            "pvp_tax_included": self.pvp_tax_included,
            "standard_price": self.standard_price,
            "tax_ids": self.tax_ids.ids,
            "tax_labels": self.tax_ids.mapped("display_name"),
            "tax_details": [
                {
                    "id": tax.id,
                    "name": tax.display_name,
                    "amount": tax.amount,
                    "amount_type": tax.amount_type,
                }
                for tax in self.tax_ids
            ],
        }

    def _collect_data_completion_entry_errors(self):
        self.ensure_one()
        errors = []
        prefix = self.display_name or self.component_type_id.display_name or _("Linea")
        if self.state == "discarded" or self.qc_state in ("fail", "not_applicable"):
            return errors
        if self.qc_state != "ok":
            errors.append(_("%s: debe marcarse como apta o descartarse antes de continuar.") % prefix)
        if not self.component_type_id:
            errors.append(_("%s: sin componente.") % prefix)
        if not self.name_final:
            errors.append(_("%s: sin nombre final.") % prefix)
        if self.quantity <= 0:
            errors.append(_("%s: cantidad debe ser mayor que cero.") % prefix)
        if not self.part_number and not self.missing_part_number_confirmed:
            errors.append(_("%s: confirme que seguira sin part number o indique uno.") % prefix)
        if self.duplicate_status == "exact" and self.decision != "use_existing":
            errors.append(
                _("%s: existe una coincidencia exacta y debe reutilizar el producto existente antes de continuar.")
                % prefix
            )
        if self.decision == "use_existing" and not self.existing_product_id:
            errors.append(_("%s: debe seleccionar producto existente.") % prefix)
        return errors

    def _prepare_existing_product_prefill_vals(self, product):
        self.ensure_one()
        vals = {
            "list_price": product.list_price,
            "standard_price": product.standard_price,
        }
        if "taxes_id" in product._fields:
            vals["tax_ids"] = [(6, 0, product.taxes_id.ids)]
        return vals

    def _serialize_operational_candidates(self):
        self.ensure_one()
        candidates = self._refine_candidates_with_rapidfuzz(self._get_duplicate_candidates())
        if not candidates:
            return []
        serialized = []
        for candidate in candidates:
            serialized.append(
                {
                    "id": candidate.id,
                    "name": candidate.display_name,
                    "status": self._get_candidate_match_status(candidate),
                    "status_label": self._get_candidate_match_label(candidate),
                    "score": int(self._compute_rapidfuzz_score(candidate) or 0),
                    "part_number": candidate.wex_teardown_part_number or candidate.default_code or "",
                    "model_name": candidate.wex_teardown_model_id.display_name or "",
                    "is_selected": self.existing_product_id == candidate,
                }
            )
        serialized.sort(
            key=lambda item: (
                {"exact": 0, "partial": 1, "model": 2, "none": 3}.get(item["status"], 9),
                -item["score"],
                item["name"],
            )
        )
        return serialized

    def _get_candidate_match_status(self, candidate):
        self.ensure_one()
        if (
            self.component_type_id
            and self.model_id
            and self.part_number
            and candidate.wex_teardown_component_id == self.component_type_id
            and candidate.wex_teardown_model_id == self.model_id
            and candidate.wex_teardown_part_number == self.part_number
        ) or (self.name_final and candidate.name == self.name_final):
            return "exact"
        if self._is_partial_candidate(candidate):
            return "partial"
        if self._is_model_candidate(candidate):
            return "model"
        return "none"

    def _get_candidate_match_label(self, candidate):
        labels = dict(self._fields["duplicate_status"].selection)
        return labels.get(self._get_candidate_match_status(candidate), _("Sin coincidencias"))

    def _is_active_review_line(self):
        self.ensure_one()
        return self.qc_state in ("pending", "ok") and self.state != "discarded"

    def _is_failed_review_line(self):
        self.ensure_one()
        return self.qc_state in ("fail", "not_applicable") or self.state == "discarded"

    def _can_process_product(self):
        self.ensure_one()
        return self.state in ("ready", "warning", "error", "draft") and self.decision in (
            "create_new",
            "use_existing",
        )

    def _process_product(self):
        self.ensure_one()
        errors, warnings = self._validate_line()
        if errors:
            raise UserError("\n".join(errors))
        if self.stock_move_id and self.stock_move_id.state == "done":
            raise UserError(_("Esta linea ya tiene un movimiento de stock validado."))
        if self.decision == "use_existing":
            product = self._update_existing_product()
        elif self.decision == "create_new":
            product = self.product_tmpl_id or self._create_product()
        else:
            raise UserError(_("La linea no tiene una decision procesable."))
        if self.product_tmpl_id != product:
            self.product_tmpl_id = product
        stock_move = self._create_stock_entry(product)
        self.write(
            {
                "product_tmpl_id": product.id,
                "stock_move_id": stock_move.id,
                "stock_ref": stock_move.reference or stock_move.name,
                "state": "created",
                "validation_status": "warning" if warnings else "ok",
                "validation_message": "\n".join(warnings),
            }
        )

    def _create_product(self):
        self.ensure_one()
        vals = self._prepare_product_create_vals()
        return self.env["product.template"].with_company(self.company_id).create(vals)

    def _update_existing_product(self):
        self.ensure_one()
        if not self.existing_product_id:
            raise UserError(_("Debe seleccionar el producto existente."))
        product = self.existing_product_id.with_company(self.company_id)
        vals = self._prepare_product_update_vals(product)
        if vals:
            product.write(vals)
        return product

    def _prepare_product_create_vals(self):
        self.ensure_one()
        vals = {
            "name": self.name_final,
            "categ_id": self.product_category_id.id,
            "list_price": self.list_price,
            "standard_price": self.standard_price,
            "active": True,
            "wex_condition": "refurbished",
            "wex_teardown_component_id": self.component_type_id.id,
            "wex_teardown_part_number": self.part_number,
            "wex_teardown_model_id": self.model_id.id,
        }
        self._add_product_type_vals(vals)
        if "taxes_id" in self.env["product.template"]._fields:
            vals["taxes_id"] = [(6, 0, (self.tax_ids or self._get_default_sale_taxes()).ids)]
        self._add_teardown_tags(vals)
        return vals

    def _prepare_product_update_vals(self, product):
        self.ensure_one()
        vals = {
            "list_price": self.list_price,
            "wex_condition": "refurbished",
            "wex_teardown_component_id": self.component_type_id.id,
            "wex_teardown_part_number": self.part_number or product.wex_teardown_part_number,
            "wex_teardown_model_id": self.model_id.id or product.wex_teardown_model_id.id,
        }
        if self.existing_product_update_name and self.name_final:
            vals["name"] = self.name_final
        if not product.categ_id and self.product_category_id:
            vals["categ_id"] = self.product_category_id.id
        if self.standard_price:
            vals["standard_price"] = self.standard_price
        if "taxes_id" in product._fields and self.tax_ids:
            vals["taxes_id"] = [(6, 0, self.tax_ids.ids)]
        self._add_teardown_tags(vals, product=product)
        return vals

    def _add_product_type_vals(self, vals):
        Product = self.env["product.template"]
        if "is_storable" in Product._fields:
            vals["is_storable"] = True
        if "type" in Product._fields:
            vals["type"] = "consu"

    def _add_teardown_tags(self, vals, product=None):
        Product = self.env["product.template"]
        tag_field = "product_tag_ids"
        if tag_field not in Product._fields:
            return
        tags = self._get_teardown_tags()
        if not tags:
            return
        tag_ids = tags.ids
        if product:
            tag_ids = list(set(product.product_tag_ids.ids + tag_ids))
        vals[tag_field] = [(6, 0, tag_ids)]

    def _get_teardown_tags(self):
        refs = [
            "wex_teardown.product_tag_refurbished",
            "wex_teardown.product_tag_teardown",
        ]
        tags = self.env["product.tag"]
        for ref in refs:
            tag = self.env.ref(ref, raise_if_not_found=False)
            if tag:
                tags |= tag
        return tags

    def _create_stock_entry(self, product):
        self.ensure_one()
        if self.stock_move_id:
            move = self.stock_move_id
            if move.state == "done":
                raise UserError(_("Esta linea ya tiene un movimiento de stock validado."))
            if move.state == "draft":
                move._action_confirm()
            self._set_move_done_quantity(move)
            move._action_done()
            return move
        variant = product.product_variant_id
        if not variant:
            raise UserError(_("El producto no tiene variante para stock."))
        source = self.env.ref("wex_teardown.stock_location_teardown_source", raise_if_not_found=False)
        dest = self.company_id.wex_teardown_default_location_id
        if not source:
            raise UserError(_("No existe la ubicacion virtual de origen de despieces."))
        if not dest:
            raise UserError(_("No hay ubicacion destino de despieces configurada."))
        move = self.env["stock.move"].create(
            {
                "name": self.batch_id.name,
                "company_id": self.company_id.id,
                "product_id": variant.id,
                "product_uom": variant.uom_id.id,
                "product_uom_qty": self.quantity,
                "location_id": source.id,
                "location_dest_id": dest.id,
                "origin": self.batch_id.name,
            }
        )
        self.write({"stock_move_id": move.id, "stock_ref": move.reference or move.name})
        move._action_confirm()
        self._set_move_done_quantity(move)
        move._action_done()
        return move

    def _set_move_done_quantity(self, move):
        self.ensure_one()
        if not move.move_line_ids:
            line_vals = {
                "move_id": move.id,
                "company_id": self.company_id.id,
                "product_id": move.product_id.id,
                "product_uom_id": move.product_uom.id,
                "location_id": move.location_id.id,
                "location_dest_id": move.location_dest_id.id,
            }
            qty_field = self._get_move_line_qty_field()
            line_vals[qty_field] = self.quantity
            self.env["stock.move.line"].create(line_vals)
            return
        qty_field = self._get_move_line_qty_field()
        move.move_line_ids.write({qty_field: self.quantity})

    def _get_move_line_qty_field(self):
        fields_map = self.env["stock.move.line"]._fields
        if "quantity" in fields_map:
            return "quantity"
        return "qty_done"

    def _get_duplicate_candidates(self):
        self.ensure_one()
        Product = self.env["product.template"]
        domain = [("wex_condition", "=", "refurbished")]
        structured_domain = self._get_structured_duplicate_domain()
        if structured_domain:
            candidates = Product.search(expression.AND([domain, structured_domain]), limit=10)
            if candidates:
                return candidates
        fallback_domain = self._get_fallback_duplicate_domain()
        candidate_pool = Product.search(expression.AND([domain, fallback_domain]), limit=50)
        if not candidate_pool:
            return Product
        scored_candidates = self._score_duplicate_candidates(candidate_pool)
        return scored_candidates[:10]

    def _set_duplicate_result(self, candidates):
        self.ensure_one()
        if not candidates:
            self.write({"duplicate_status": "none", "duplicate_message": False})
            return
        status = self._classify_duplicate_candidates(candidates)
        message = "\n".join(self._format_duplicate_candidate(candidate) for candidate in candidates)
        self.write({"duplicate_status": status, "duplicate_message": message})

    def _get_structured_duplicate_domain(self):
        self.ensure_one()
        domain = []
        if self.component_type_id and self.model_id and self.part_number:
            domain = [
                ("wex_teardown_component_id", "=", self.component_type_id.id),
                ("wex_teardown_model_id", "=", self.model_id.id),
                ("wex_teardown_part_number", "=", self.part_number),
            ]
        elif self.component_type_id and self.model_id:
            domain = [
                ("wex_teardown_component_id", "=", self.component_type_id.id),
                ("wex_teardown_model_id", "=", self.model_id.id),
            ]
        elif self.model_id:
            domain = [("wex_teardown_model_id", "=", self.model_id.id)]
        return domain

    def _get_fallback_duplicate_domain(self):
        self.ensure_one()
        category_domain = [("categ_id", "=", self.product_category_id.id)] if self.product_category_id else []
        if self.part_number:
            fallback_domains = [
                [
                    "|",
                    "|",
                    ("wex_teardown_part_number", "=", self.part_number),
                    ("default_code", "=", self.part_number),
                    ("barcode", "=", self.part_number),
                ]
            ]
            if category_domain:
                fallback_domains.append(category_domain)
            return expression.OR(fallback_domains)
        if self.name_final:
            fallback_domains = [category_domain] if category_domain else []
            if self.component_type_id:
                fallback_domains.append([("name", "ilike", self.component_type_id.name)])
            if self.model_id:
                fallback_domains.append([("name", "ilike", self.model_id.name)])
                relaxed_model_name = self._relaxed_model_reference(self.model_id.name)
                if relaxed_model_name and relaxed_model_name != self.model_id.name:
                    fallback_domains.append([("name", "ilike", relaxed_model_name)])
            fallback_domains.append([("name", "ilike", self.name_final)])
            return expression.OR(fallback_domains)
        return category_domain

    def _classify_duplicate_candidates(self, candidates):
        self.ensure_one()
        for candidate in candidates:
            if (
                self.component_type_id
                and self.model_id
                and self.part_number
                and candidate.wex_teardown_component_id == self.component_type_id
                and candidate.wex_teardown_model_id == self.model_id
                and candidate.wex_teardown_part_number == self.part_number
            ) or (self.name_final and candidate.name == self.name_final):
                return "exact"
        for candidate in candidates:
            if self._is_partial_candidate(candidate):
                return "partial"
        for candidate in candidates:
            if self._is_model_candidate(candidate):
                return "model"
        return "none"

    def _format_duplicate_candidate(self, candidate):
        self.ensure_one()
        parts = [candidate.display_name]
        score = self._compute_rapidfuzz_score(candidate)
        if score:
            parts.append(_("[RF %s]") % int(score))
        if candidate.wex_teardown_part_number:
            parts.append("[%s]" % candidate.wex_teardown_part_number)
        elif candidate.default_code:
            parts.append("[%s]" % candidate.default_code)
        if candidate.wex_teardown_model_id:
            parts.append("(%s)" % candidate.wex_teardown_model_id.display_name)
        return " ".join(parts)

    def _score_duplicate_candidates(self, candidates):
        self.ensure_one()
        scored = []
        for candidate in candidates:
            score = self._compute_duplicate_score(candidate)
            if score > 0:
                scored.append((score, candidate.id))
        scored.sort(key=lambda item: (-item[0], item[1]))
        candidate_ids = [candidate_id for _, candidate_id in scored]
        return candidates.browse(candidate_ids)

    def _compute_duplicate_score(self, candidate):
        self.ensure_one()
        score = 0
        if self.product_category_id and candidate.categ_id == self.product_category_id:
            score += 20
        if self.part_number and (
            candidate.wex_teardown_part_number == self.part_number
            or candidate.default_code == self.part_number
            or candidate.barcode == self.part_number
        ):
            score += 120
        if self.name_final and candidate.name == self.name_final:
            score += 100
        if self.component_type_id and candidate.wex_teardown_component_id == self.component_type_id:
            score += 40
        if self.model_id and candidate.wex_teardown_model_id == self.model_id:
            score += 60
        if self._candidate_matches_model_text(candidate):
            score += 35
        if self._candidate_matches_component_text(candidate):
            score += 25
        return score

    def _refine_candidates_with_rapidfuzz(self, candidates):
        self.ensure_one()
        if not candidates:
            return candidates
        status = self._classify_duplicate_candidates(candidates)
        if status in ("none", "exact") or not self._has_rapidfuzz():
            return candidates
        scored_candidates = []
        for candidate in candidates:
            rf_score = self._compute_rapidfuzz_score(candidate)
            if not rf_score:
                continue
            if status == "partial" and rf_score < 76:
                continue
            if status == "model" and rf_score < 74:
                continue
            if status == "model" and not self._has_model_secondary_signal(candidate):
                continue
            scored_candidates.append((rf_score, candidate.id))
        if not scored_candidates:
            return self.env["product.template"]
        scored_candidates.sort(key=lambda item: (-item[0], item[1]))
        candidate_ids = [candidate_id for _, candidate_id in scored_candidates]
        return candidates.browse(candidate_ids)

    def _compute_rapidfuzz_score(self, candidate):
        self.ensure_one()
        if not self._has_rapidfuzz():
            return 0
        query_name = self.name_final or self.name_suggested or self.component_type_id.name or ""
        if not query_name or not candidate.name:
            return 0
        primary_query, compatibility_query = self._split_name_segments(query_name)
        primary_target, compatibility_target = self._split_name_segments(candidate.name)
        compatibility_fallback = (
            candidate.wex_teardown_model_id.name if candidate.wex_teardown_model_id else candidate.name
        )
        primary_score = self._compute_text_similarity(primary_query, primary_target)
        if not primary_score:
            primary_score = self._compute_text_similarity(
                self.component_type_id.name,
                candidate.wex_teardown_component_id.name or primary_target or candidate.name,
            )
        compatibility_score = self._compute_text_similarity(
            compatibility_query,
            compatibility_target or compatibility_fallback,
        )
        component_score = self._compute_text_similarity(
            self.component_type_id.name,
            candidate.wex_teardown_component_id.name or primary_target or candidate.name,
        )
        model_query = self._relaxed_model_reference(self.model_id.name) if self.model_id else ""
        model_target = ""
        if candidate.wex_teardown_model_id:
            model_target = self._relaxed_model_reference(candidate.wex_teardown_model_id.name)
        if not model_target:
            model_target = self._relaxed_model_reference(compatibility_target or candidate.name)
        model_score = self._compute_text_similarity(model_query, model_target)
        category_bonus = 8 if self.product_category_id and candidate.categ_id == self.product_category_id else 0
        structured_bonus = 0
        if self.model_id and candidate.wex_teardown_model_id == self.model_id:
            structured_bonus += 10
        if self.component_type_id and candidate.wex_teardown_component_id == self.component_type_id:
            structured_bonus += 8
        blended = (
            (primary_score * 0.6)
            + (component_score * 0.2)
            + (model_score * 0.1)
            + (compatibility_score * 0.1)
            + category_bonus
            + structured_bonus
        )
        return min(100, blended)

    def _is_partial_candidate(self, candidate):
        self.ensure_one()
        same_component = bool(
            self.component_type_id and candidate.wex_teardown_component_id == self.component_type_id
        )
        same_model = bool(self.model_id and candidate.wex_teardown_model_id == self.model_id)
        primary_similarity = self._get_primary_name_similarity(candidate)
        if same_component and same_model:
            return True
        if same_model and self._candidate_matches_component_text(candidate) and primary_similarity >= 72:
            return True
        if primary_similarity < 78:
            return False
        return self._compute_rapidfuzz_score(candidate) >= 84 and (
            same_component or same_model or self._has_category_match(candidate)
        )

    def _is_model_candidate(self, candidate):
        self.ensure_one()
        if not self.model_id:
            return False
        same_model = candidate.wex_teardown_model_id == self.model_id
        model_text_match = self._candidate_matches_model_text(candidate)
        if not (same_model or model_text_match):
            return False
        if not self._has_model_secondary_signal(candidate):
            return False
        return self._compute_rapidfuzz_score(candidate) >= 74

    def _has_model_secondary_signal(self, candidate):
        self.ensure_one()
        return self._has_category_match(candidate) or self._candidate_matches_component_text(candidate)

    def _has_category_match(self, candidate):
        self.ensure_one()
        return bool(self.product_category_id and candidate.categ_id == self.product_category_id)

    def _get_primary_name_similarity(self, candidate):
        self.ensure_one()
        query_name = self.name_final or self.name_suggested or self.component_type_id.name or ""
        if not query_name or not candidate.name:
            return 0
        primary_query, _compatibility_query = self._split_name_segments(query_name)
        primary_target, _compatibility_target = self._split_name_segments(candidate.name)
        return self._compute_text_similarity(primary_query, primary_target)

    def _compute_text_similarity(self, left, right):
        if not self._has_rapidfuzz() or not left or not right:
            return 0
        scores = [
            fuzz.WRatio(left, right, processor=self._normalize_match_text),
            fuzz.token_set_ratio(left, right, processor=self._normalize_match_text),
        ]
        return max(scores)

    def _has_rapidfuzz(self):
        return bool(fuzz and process)

    def _candidate_matches_model_text(self, candidate):
        self.ensure_one()
        if not self.model_id or not candidate.name:
            return False
        model_tokens = self._tokenize_match_text(self.model_id.name)
        candidate_tokens = self._tokenize_match_text(candidate.name)
        if not model_tokens or not candidate_tokens:
            return False
        overlap = len(model_tokens & candidate_tokens)
        required_overlap = max(2, min(3, len(model_tokens)))
        if overlap >= required_overlap:
            return True
        relaxed_model = self._relaxed_model_reference(self.model_id.name)
        relaxed_candidate = self._relaxed_model_reference(candidate.name)
        return bool(relaxed_model and relaxed_candidate and relaxed_model in relaxed_candidate)

    def _candidate_matches_component_text(self, candidate):
        self.ensure_one()
        if not self.component_type_id or not candidate.name:
            return False
        component_tokens = self._tokenize_match_text(self.component_type_id.name)
        primary_target, _compatibility_target = self._split_name_segments(candidate.name)
        candidate_tokens = self._tokenize_match_text(primary_target or candidate.name)
        if not component_tokens or not candidate_tokens:
            return False
        overlap = len(component_tokens & candidate_tokens)
        required_overlap = max(1, min(2, len(component_tokens)))
        return overlap >= required_overlap

    def _split_name_segments(self, value):
        normalized_value = value or ""
        parts = re.split(r"\s+para\s+", normalized_value, maxsplit=1, flags=re.IGNORECASE)
        primary = parts[0].strip() if parts else ""
        compatibility = parts[1].strip() if len(parts) > 1 else ""
        return primary, compatibility

    def _tokenize_match_text(self, value):
        normalized = self._normalize_match_text(value)
        tokens = {
            self._normalize_match_token(token)
            for token in normalized.split()
            if len(token) > 1 and token not in self._MATCH_STOPWORDS
        }
        return tokens

    def _normalize_match_text(self, value):
        text = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode("ascii")
        text = text.lower()
        text = text.replace("-", " ")
        text = re.sub(r"[^a-z0-9\s]", " ", text)
        return re.sub(r"\s+", " ", text).strip()

    def _relaxed_model_reference(self, value):
        normalized = self._normalize_match_text(value)
        filtered_tokens = [token for token in normalized.split() if token not in {"ds"}]
        return " ".join(filtered_tokens)

    def _normalize_match_token(self, token):
        token = token.strip()
        if len(token) > 4 and token.endswith("s"):
            return token[:-1]
        return token

    def _validate_line(self):
        self.ensure_one()
        errors = []
        warnings = []
        prefix = self.display_name or _("Linea")
        if self.state == "discarded" or self.decision == "discard":
            return errors, warnings
        if not self.component_type_id:
            errors.append(_("%s: sin componente.") % prefix)
        elif self.component_type_id.device_type != self.device_type:
            errors.append(_("%s: el componente no pertenece al tipo de dispositivo del despiece.") % prefix)
        if not self.product_category_id:
            errors.append(_("%s: el componente no tiene categoria configurada.") % prefix)
        if not self.name_final:
            errors.append(_("%s: sin nombre final.") % prefix)
        if not self.list_price or self.list_price <= 0:
            errors.append(_("%s: precio sin IVA obligatorio mayor que cero.") % prefix)
        if self.quantity <= 0:
            errors.append(_("%s: cantidad debe ser mayor que cero.") % prefix)
        if self.qc_state == "ok" and self.decision == "pending":
            errors.append(_("%s: debe tener una decision de producto antes de validar.") % prefix)
        if self.decision == "use_existing" and not self.existing_product_id:
            errors.append(_("%s: debe seleccionar producto existente.") % prefix)
        if self.qc_state in ("fail", "not_applicable"):
            return errors, warnings
        if not self.part_number:
            errors.append(_("%s: sin part number confirmado.") % prefix)
        status = "error" if errors else ("warning" if warnings else "ok")
        self.write({"validation_status": status, "validation_message": "\n".join(errors + warnings)})
        if not errors and self.state not in ("created", "discarded"):
            self.state = "warning" if warnings else "ready"
        return errors, warnings

    def _get_name_values(self):
        self.ensure_one()
        selection = dict(DEVICE_TYPE_SELECTION)
        return {
            "component": self.component_type_id.name or "",
            "part_number": self.part_number or "",
            "device_type": selection.get(self.device_type, self.device_type or ""),
            "brand": self.brand_id.name or "",
            "model": self.model_id.name or "",
        }

    def _render_default_name(self):
        self.ensure_one()
        values = self._get_name_values()
        return " ".join(
            part
            for part in [
                values["component"],
                values["part_number"],
                "para" if values["device_type"] or values["brand"] or values["model"] else "",
                values["device_type"],
                values["brand"],
                values["model"],
            ]
            if part
        )

    def _get_default_sale_taxes(self):
        self.ensure_one()
        return self.with_company(self.company_id)._get_default_sale_taxes_for_company()

    def _get_default_sale_taxes_for_company(self):
        Product = self.env["product.template"]
        if "taxes_id" not in Product._fields:
            return self.env["account.tax"]
        defaults = Product.with_company(self.company_id).default_get(["taxes_id"])
        tax_ids = []
        for command in defaults.get("taxes_id") or []:
            if isinstance(command, (list, tuple)) and command[0] == 6:
                tax_ids.extend(command[2])
            elif isinstance(command, int):
                tax_ids.append(command)
        return self.env["account.tax"].browse(tax_ids)

    def _get_price_included(self):
        self.ensure_one()
        price = self.list_price or 0.0
        if not price or not self.tax_ids:
            return price
        taxes = self.tax_ids.compute_all(price, currency=self.company_id.currency_id)
        return taxes["total_included"]

    def _get_price_excluded(self, price_tax_included):
        self.ensure_one()
        price = price_tax_included or 0.0
        if not price or not self.tax_ids:
            return price
        percent_taxes = self.tax_ids.filtered(lambda tax: tax.amount_type == "percent")
        if percent_taxes and len(percent_taxes) == len(self.tax_ids):
            percent = sum(percent_taxes.mapped("amount"))
            return price / (1 + (percent / 100.0)) if percent else price
        taxes = self.tax_ids.compute_all(price, currency=self.company_id.currency_id, handle_price_include=True)
        return taxes["total_excluded"]
