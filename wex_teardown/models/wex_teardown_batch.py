from odoo import api, fields, models, _
from odoo.exceptions import UserError

from odoo.addons.wexplay_repair.models.device_constants import DEVICE_TYPE_SELECTION


class WexTeardownBatch(models.Model):
    _name = "wex.teardown.batch"
    _description = "Despiece"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(default="/", readonly=True, copy=False, tracking=True)
    state = fields.Selection(
        [
            ("draft", "Borrador"),
            ("template_loaded", "Plantilla cargada"),
            ("review", "Revisión"),
            ("validated", "Validado"),
            ("partial_created", "Creación parcial"),
            ("done", "Hecho"),
            ("cancelled", "Cancelado"),
        ],
        default="draft",
        required=True,
        tracking=True,
    )
    workflow_focus = fields.Selection(
        [
            ("device", "Dispositivo"),
            ("pieces", "Piezas"),
            ("data_completion", "Completar datos"),
        ],
        string="Foco de trabajo",
        default="device",
        copy=False,
    )
    device_type = fields.Selection(DEVICE_TYPE_SELECTION, string="Tipo de dispositivo", required=True, tracking=True)
    model_id = fields.Many2one(
        "wex.repair.device_model",
        string="Modelo",
        required=True,
        domain="[('device_type', '=', device_type)]",
        tracking=True,
    )
    brand_id = fields.Many2one(
        related="model_id.brand_id",
        string="Marca",
        store=True,
        readonly=True,
    )
    technician_id = fields.Many2one(
        "res.users",
        default=lambda self: self.env.user,
        required=True,
        tracking=True,
    )
    template_id = fields.Many2one(
        "wex.teardown.template",
        string="Plantilla",
        domain="[('device_type', '=', device_type)]",
        tracking=True,
    )
    line_ids = fields.One2many("wex.teardown.line", "batch_id", string="Piezas")
    active_line_ids = fields.One2many(
        "wex.teardown.line",
        compute="_compute_review_line_ids",
        string="Piezas pendientes / aptas",
    )
    failed_line_ids = fields.One2many(
        "wex.teardown.line",
        compute="_compute_review_line_ids",
        string="No aptas / control de calidad fallido",
    )
    company_id = fields.Many2one(
        "res.company",
        string="Compañía",
        default=lambda self: self.env.company,
        required=True,
        index=True,
    )
    notes = fields.Text(string="Notas")
    validation_message = fields.Text(string="Mensaje de validación", readonly=True, copy=False)
    missing_part_number_confirmed = fields.Boolean(string="Part number ausente confirmado", copy=False)
    warning_confirmed = fields.Boolean(string="Advertencias confirmadas", copy=False)
    processed_at = fields.Datetime(string="Procesado el", readonly=True, copy=False)
    processed_by = fields.Many2one("res.users", string="Procesado por", readonly=True, copy=False)
    duplicate_check_state = fields.Selection(
        [
            ("idle", "Sin ejecutar"),
            ("running", "Calculando"),
            ("done", "Completado"),
            ("error", "Error"),
        ],
        string="Estado de coincidencias",
        default="idle",
        copy=False,
        readonly=True,
    )
    duplicate_check_progress = fields.Integer(string="Progreso coincidencias", default=0, copy=False, readonly=True)
    duplicate_check_processed = fields.Integer(string="Piezas revisadas", default=0, copy=False, readonly=True)
    duplicate_check_total = fields.Integer(string="Piezas a revisar", default=0, copy=False, readonly=True)
    duplicate_check_message = fields.Char(string="Mensaje coincidencias", copy=False, readonly=True)
    pieces_operational_anchor = fields.Integer(
        string="Ancla vista operativa de piezas",
        compute="_compute_operational_anchors",
    )
    data_completion_anchor = fields.Integer(
        string="Ancla vista completar datos",
        compute="_compute_operational_anchors",
    )

    line_count = fields.Integer(string="Piezas", compute="_compute_summary_counts")
    created_count = fields.Integer(string="Creadas", compute="_compute_summary_counts")
    discarded_count = fields.Integer(string="Descartadas", compute="_compute_summary_counts")
    pending_count = fields.Integer(string="Pendientes", compute="_compute_summary_counts")
    error_count = fields.Integer(string="Errores", compute="_compute_summary_counts")
    warning_count = fields.Integer(string="Advertencias", compute="_compute_summary_counts")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "/") == "/":
                vals["name"] = self.env["ir.sequence"].next_by_code("wex.teardown.batch") or "/"
        records = super().create(vals_list)
        for record in records:
            record.message_post(body=_("Despiece creado."))
        return records

    @api.onchange("device_type")
    def _onchange_device_type_reset_model_template(self):
        for rec in self:
            if rec.model_id and rec.model_id.device_type != rec.device_type:
                rec.model_id = False
            if rec.template_id and rec.template_id.device_type != rec.device_type:
                rec.template_id = False

    @api.depends("line_ids.state", "line_ids.validation_status")
    def _compute_summary_counts(self):
        for rec in self:
            lines = rec.line_ids
            rec.line_count = len(lines)
            rec.created_count = len(lines.filtered(lambda line: line.state == "created"))
            rec.discarded_count = len(lines.filtered(lambda line: line.state == "discarded"))
            rec.error_count = len(lines.filtered(lambda line: line.state == "error"))
            rec.warning_count = len(lines.filtered(lambda line: line.validation_status == "warning"))
            rec.pending_count = len(
                lines.filtered(lambda line: line.state not in ("created", "discarded", "error"))
            )

    @api.depends("line_ids.qc_state", "line_ids.state")
    def _compute_review_line_ids(self):
        for rec in self:
            rec.active_line_ids = rec.line_ids.filtered(lambda line: line._is_active_review_line())
            rec.failed_line_ids = rec.line_ids.filtered(lambda line: line._is_failed_review_line())

    @api.depends("line_count", "active_line_ids")
    def _compute_operational_anchors(self):
        for rec in self:
            rec.pieces_operational_anchor = rec.line_count
            rec.data_completion_anchor = rec.line_count

    def action_load_template(self):
        for rec in self:
            rec._check_can_load_template()
            rec.line_ids.unlink()
            vals_list = [rec._prepare_line_from_template_line(tpl_line) for tpl_line in rec.template_id.line_ids]
            self.env["wex.teardown.line"].create(vals_list)
            rec.state = "template_loaded"
            rec.workflow_focus = "pieces"
            rec.message_post(body=_("Plantilla cargada: %s") % rec.template_id.display_name)
        return True

    def action_mark_review(self):
        self.write({"state": "review", "workflow_focus": "pieces"})
        return True

    def action_focus_data_completion(self):
        for rec in self:
            rec._prepare_for_data_completion()
            vals = {"workflow_focus": "data_completion"}
            if rec.state in ("draft", "template_loaded"):
                vals["state"] = "review"
            rec.write(vals)
        return True

    def action_check_duplicates(self):
        for rec in self:
            rec.line_ids.filtered(lambda line: line._is_active_review_line()).action_check_duplicates()
            if rec.state in ("template_loaded", "draft"):
                rec.state = "review"
            rec.workflow_focus = "pieces"
            rec.message_post(body=_("Comprobacion de duplicados ejecutada."))
        return True

    def action_start_duplicate_check(self, chunk_size=3):
        self.ensure_one()
        active_lines = self._get_duplicate_check_lines()
        active_lines.write(
            {
                "duplicate_checked_at": False,
                "duplicate_status": "none",
                "duplicate_message": False,
            }
        )
        vals = {
            "duplicate_check_state": "running" if active_lines else "done",
            "duplicate_check_progress": 0,
            "duplicate_check_processed": 0,
            "duplicate_check_total": len(active_lines),
            "duplicate_check_message": _("Buscando coincidencias...") if active_lines else _("No hay piezas aptas para revisar."),
            "workflow_focus": "pieces",
        }
        self.write(vals)
        return self._get_duplicate_check_payload(chunk_size=chunk_size)

    def action_process_duplicate_check_chunk(self, chunk_size=3):
        self.ensure_one()
        if self.duplicate_check_state == "error":
            return self._get_duplicate_check_payload(chunk_size=chunk_size)
        try:
            pending_lines = self._get_pending_duplicate_check_lines(limit=chunk_size)
            if pending_lines:
                pending_lines.action_check_duplicates()
                pending_lines.write({"duplicate_checked_at": fields.Datetime.now()})
            remaining = len(self._get_pending_duplicate_check_lines())
            processed = max(self.duplicate_check_total - remaining, 0)
            progress = int((processed / self.duplicate_check_total) * 100) if self.duplicate_check_total else 100
            state = "running" if remaining else "done"
            message = (
                _("Buscando coincidencias... %s/%s") % (processed, self.duplicate_check_total)
                if remaining
                else _("Comprobación de coincidencias completada.")
            )
            self.write(
                {
                    "duplicate_check_state": state,
                    "duplicate_check_processed": processed,
                    "duplicate_check_progress": progress,
                    "duplicate_check_message": message,
                }
            )
            if state == "done":
                if self.state in ("template_loaded", "draft"):
                    self.state = "review"
                self.message_post(body=_("Comprobación de coincidencias ejecutada."))
            return self._get_duplicate_check_payload(chunk_size=chunk_size)
        except Exception as error:
            self.write(
                {
                    "duplicate_check_state": "error",
                    "duplicate_check_message": str(error),
                }
            )
            raise

    def action_mark_all_qc_ok(self):
        for rec in self:
            rec.line_ids.filtered(lambda line: line.state not in ("created", "discarded"))._mark_qc("ok")
            rec.message_post(body=_("Todas las piezas pendientes se marcaron como revisadas."))
        return True

    def action_mark_all_qc_not_applicable(self):
        for rec in self:
            rec.line_ids.filtered(lambda line: line.state not in ("created", "discarded"))._mark_qc(
                "not_applicable"
            )
            rec.message_post(body=_("Todas las piezas pendientes se marcaron como control no aplicable."))
        return True

    def action_get_operational_piece_rows(self):
        self.ensure_one()
        return {
            "batch_id": self.id,
            "state": self.state,
            "rows": [line._get_operational_row_data() for line in self._get_duplicate_check_lines()],
        }

    def action_get_data_completion_rows(self):
        self.ensure_one()
        return {
            "batch_id": self.id,
            "state": self.state,
            "tax_options": self._get_available_sale_tax_options(),
            "rows": [line._get_data_completion_row_data() for line in self._get_data_completion_lines()],
        }

    def action_validate_teardown(self):
        for rec in self:
            rec._prepare_for_data_completion()
            errors, warnings = rec._collect_validation_messages()
            rec.validation_message = rec._format_validation_messages(errors, warnings)
            if errors:
                rec.state = "review"
                rec.workflow_focus = "data_completion"
                rec.message_post(body=_("Validacion con errores.<br/>%s") % rec.validation_message)
                raise UserError(rec.validation_message)
            if warnings and not rec.warning_confirmed:
                rec.state = "review"
                rec.workflow_focus = "data_completion"
                rec.message_post(body=_("Validacion con advertencias.<br/>%s") % rec.validation_message)
                raise UserError(
                    _(
                        "Hay advertencias pendientes. Revise el mensaje de validacion y marque "
                        "'Advertencias confirmadas' si desea continuar."
                    )
                )
            rec.state = "validated"
            rec.workflow_focus = "data_completion"
            rec.message_post(body=_("Despiece validado."))
        return True

    def action_create_or_update_products(self):
        for rec in self:
            if rec.state not in ("validated", "partial_created"):
                raise UserError(_("Solo se pueden procesar despieces validados o parcialmente creados."))
            rec._check_stock_location()
            processable_lines = rec.line_ids.filtered(lambda line: line._can_process_product())
            if not processable_lines:
                raise UserError(_("No hay lineas pendientes para procesar."))
            for line in processable_lines:
                line.action_create_or_update_product()
            rec._update_state_after_processing()
            rec.processed_at = fields.Datetime.now()
            rec.processed_by = self.env.user
            rec.message_post(body=_("Creacion/actualizacion de productos ejecutada."))
        return True

    def action_cancel(self):
        self.write({"state": "cancelled"})
        return True

    def action_reset_to_review(self):
        self.write({"state": "review", "workflow_focus": "pieces"})
        return True

    def _check_can_load_template(self):
        self.ensure_one()
        if self.state not in ("draft", "template_loaded"):
            raise UserError(_("Solo se puede cargar plantilla en borrador o plantilla cargada."))
        if not self.device_type:
            raise UserError(_("Debe indicar el tipo de dispositivo."))
        if not self.model_id:
            raise UserError(_("Debe indicar el modelo."))
        if not self.template_id:
            raise UserError(_("Debe indicar la plantilla."))
        if self.template_id.device_type != self.device_type:
            raise UserError(_("La plantilla debe pertenecer al mismo tipo de dispositivo que el despiece."))
        if not self.template_id.line_ids:
            raise UserError(_("La plantilla no tiene lineas."))

    def _prepare_line_from_template_line(self, template_line):
        self.ensure_one()
        return {
            "batch_id": self.id,
            "component_type_id": template_line.component_type_id.id,
            "quantity": template_line.default_quantity,
            "missing_part_number_confirmed": bool(
                self.template_id.default_missing_part_number_confirmed
            ),
        }

    def _prepare_for_data_completion(self):
        self.ensure_one()
        self._check_can_focus_data_completion()
        self._normalize_data_completion_decisions()
        self.warning_confirmed = False

    def _check_can_focus_data_completion(self):
        self.ensure_one()
        errors = []
        active_lines = self._get_duplicate_check_lines()
        if not active_lines:
            errors.append(_("No hay piezas aptas o pendientes para preparar."))
        for line in active_lines:
            errors.extend(line._collect_data_completion_entry_errors())
        if errors:
            raise UserError(
                _("No se puede pasar a completar datos hasta cerrar la fase de piezas:\n- %s")
                % "\n- ".join(errors)
            )

    def _normalize_data_completion_decisions(self):
        self.ensure_one()
        lines_to_create = self.line_ids.filtered(
            lambda line: line.qc_state == "ok" and line.state != "discarded" and line.decision == "pending"
        )
        if lines_to_create:
            lines_to_create.write({"decision": "create_new"})

    def _collect_validation_messages(self):
        self.ensure_one()
        errors = []
        warnings = []
        if not self.device_type:
            errors.append(_("El despiece no tiene tipo de dispositivo."))
        if not self.model_id:
            errors.append(_("El despiece no tiene modelo."))
        if not self.template_id:
            errors.append(_("El despiece no tiene plantilla."))
        if not self.line_ids:
            errors.append(_("El despiece no tiene piezas."))
        if not self.company_id.wex_teardown_default_location_id:
            errors.append(_("La compania no tiene ubicacion destino de despieces configurada."))
        for line in self.line_ids:
            line_errors, line_warnings = line._validate_line()
            errors.extend(line_errors)
            warnings.extend(line_warnings)
        return errors, warnings

    def _get_duplicate_check_lines(self):
        self.ensure_one()
        return self.line_ids.filtered(lambda line: line._is_active_review_line())

    def _get_data_completion_lines(self):
        self.ensure_one()
        return self.line_ids.filtered(lambda line: line.qc_state == "ok" and line.state != "discarded")

    def _get_available_sale_tax_options(self):
        self.ensure_one()
        taxes = self.env["account.tax"].search(
            [
                ("type_tax_use", "=", "sale"),
                "|",
                ("company_id", "=", self.company_id.id),
                ("company_id", "=", False),
            ],
            order="sequence, id",
        )
        return [{"id": tax.id, "name": tax.display_name} for tax in taxes]

    def _get_pending_duplicate_check_lines(self, limit=None):
        self.ensure_one()
        domain = [
            ("batch_id", "=", self.id),
            ("qc_state", "in", ("pending", "ok")),
            ("state", "!=", "discarded"),
            ("duplicate_checked_at", "=", False),
        ]
        return self.env["wex.teardown.line"].search(domain, order="id", limit=limit)

    def _get_duplicate_check_payload(self, chunk_size=3):
        self.ensure_one()
        return {
            "state": self.duplicate_check_state,
            "progress": self.duplicate_check_progress,
            "processed": self.duplicate_check_processed,
            "total": self.duplicate_check_total,
            "message": self.duplicate_check_message or "",
            "chunk_size": chunk_size,
        }

    def _format_validation_messages(self, errors, warnings):
        blocks = []
        if errors:
            blocks.append(_("Errores:\n- %s") % "\n- ".join(errors))
        if warnings:
            blocks.append(_("Advertencias:\n- %s") % "\n- ".join(warnings))
        return "\n\n".join(blocks) or _("Validacion correcta.")

    def _check_stock_location(self):
        self.ensure_one()
        if not self.company_id.wex_teardown_default_location_id:
            raise UserError(_("Configure la ubicacion destino de despieces en la compania."))

    def _update_state_after_processing(self):
        self.ensure_one()
        active_lines = self.line_ids.filtered(lambda line: line.state != "discarded")
        if active_lines and all(line.state == "created" for line in active_lines):
            self.state = "done"
        else:
            self.state = "partial_created"
