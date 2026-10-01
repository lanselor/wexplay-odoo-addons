import re

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

from .product_template import _TEARDOWN_TOKEN


class WexTeardownBatchLifecycle(models.Model):
    _inherit = "wex.teardown.batch"

    state = fields.Selection(selection_add=[("products_prepared", "Productos preparados")],
                             ondelete={"products_prepared": "set default"}, copy=False)
    workflow_focus = fields.Selection(selection_add=[("products", "Productos pendientes")])
    name = fields.Char(copy=False)
    device_identifier_type = fields.Selection(
        [("imei", "IMEI"), ("serial", "Número de serie")], string="Tipo de identificación", copy=False,
    )
    device_identifier = fields.Char(string="IMEI / número de serie", copy=False, tracking=True)
    device_identity_key = fields.Char(compute="_compute_device_identity_key", store=True, copy=False)
    physical_identity_confirmed = fields.Boolean(
        string="Dispositivo/bandeja identificado físicamente con la referencia del despiece", copy=False,
    )
    prepared_count = fields.Integer(string="Productos pendientes", compute="_compute_prepared_count")
    prepared_line_ids = fields.One2many("wex.teardown.line", compute="_compute_prepared_count")

    _sql_constraints = [
        ("device_identity_unique", "unique(company_id, device_identity_key)",
         "Este dispositivo ya tiene un despiece. Localice el lote existente por su IMEI o número de serie."),
    ]

    @api.depends("device_identifier_type", "device_identifier", "brand_id", "state")
    def _compute_device_identity_key(self):
        for batch in self:
            value = (batch.device_identifier or "").strip().upper()
            if batch.device_identifier_type == "imei":
                value = re.sub(r"\s+", "", value)
            scope = str(batch.brand_id.id) if batch.device_identifier_type == "serial" else ""
            batch.device_identity_key = (
                "%s:%s:%s" % (batch.device_identifier_type, scope, value)
                if value and batch.device_identifier_type and batch.state != "cancelled" else False
            )

    @api.constrains("device_identifier", "device_identifier_type", "model_id")
    def _check_identifier_format(self):
        for batch in self:
            if batch.device_identifier and not batch.device_identifier_type:
                raise ValidationError(_("Seleccione el tipo de identificación del dispositivo."))
            if batch.device_identifier_type == "imei" and batch.device_identifier:
                if not re.fullmatch(r"[0-9]{15}", re.sub(r"\s+", "", batch.device_identifier)):
                    raise ValidationError(_("El IMEI debe contener 15 dígitos."))

    @api.constrains("device_identifier", "device_identifier_type", "company_id", "model_id", "state")
    def _check_identity_duplicate(self):
        for batch in self:
            if batch.device_identity_key and self.search_count([
                ("company_id", "=", batch.company_id.id), ("device_identity_key", "=", batch.device_identity_key),
                ("id", "!=", batch.id),
            ]):
                raise ValidationError(_("El dispositivo ya tiene un despiece. Busque su IMEI o número de serie."))

    @api.depends("line_ids.state", "line_ids.product_tmpl_id")
    def _compute_prepared_count(self):
        for batch in self:
            batch.prepared_line_ids = batch.line_ids.filtered(lambda line: line.state == "product_prepared")
            batch.prepared_count = len(batch.prepared_line_ids)

    def _check_device_identity(self):
        self.ensure_one()
        if not (self.device_identifier and self.device_identifier_type) and not self.physical_identity_confirmed:
            raise UserError(_("Indique IMEI/serie o confirme que el dispositivo y su bandeja están identificados con la referencia del despiece."))

    @api.model_create_multi
    def create(self, vals_list):
        if self.env.context.get("_teardown_token") is not _TEARDOWN_TOKEN:
            if any(vals.get("state", "draft") != "draft" for vals in vals_list):
                raise UserError(_("Cree los despieces en borrador."))
        return super().create(vals_list)

    def _lock_for_processing(self):
        self.ensure_one()
        self.check_access("write")
        self.flush_recordset()
        self.env.cr.execute("UPDATE wex_teardown_batch SET write_date = write_date WHERE id = %s", [self.id])
        self.invalidate_recordset()

    def _write_lifecycle(self, vals):
        return self.with_context(_teardown_token=_TEARDOWN_TOKEN).write(vals)

    def write(self, vals):
        if self.env.context.get("_teardown_token") is not _TEARDOWN_TOKEN:
            if "state" in vals and vals["state"] not in ("draft", "template_loaded", "review"):
                raise UserError(_("Utilice las acciones del despiece para cambiar su estado."))
            protected = {"company_id", "model_id", "device_type", "device_identifier", "device_identifier_type", "physical_identity_confirmed"}
            for batch in self:
                if "state" in vals or protected & vals.keys():
                    batch._lock_for_processing()
                    if batch.line_ids.filtered(lambda line: line.product_tmpl_id or line.stock_move_id):
                        raise UserError(_("No cambie identidad, compañía o estado de un despiece con productos preparados."))
                if batch.state == "cancelled" and "state" in vals:
                    raise UserError(_("Un despiece cancelado no se reabre. Revise su trazabilidad."))
        return super().write(vals)

    def unlink(self):
        if any(line.product_tmpl_id or line.stock_move_id for line in self.mapped("line_ids")):
            raise UserError(_("No se puede eliminar un despiece con productos preparados o stock."))
        return super().unlink()

    def copy(self, default=None):
        values = dict(default or {})
        values.update(name="/", state="draft", workflow_focus="device", line_ids=[],
                      device_identifier=False, device_identifier_type=False, physical_identity_confirmed=False)
        return super().copy(values)

    def action_load_template(self):
        for batch in self:
            batch._check_device_identity()
        return super().action_load_template()

    def action_validate_teardown(self):
        for batch in self:
            batch._lock_for_processing()
            batch._check_device_identity()
            if batch.state not in ("review", "template_loaded"):
                raise UserError(_("Solo se puede validar un despiece en revisión."))
        return super(WexTeardownBatchLifecycle, self.with_context(_teardown_token=_TEARDOWN_TOKEN)).action_validate_teardown()

    def action_prepare_products(self):
        for batch in self:
            batch._lock_for_processing()
            if batch.state not in ("validated", "products_prepared", "partial_created"):
                raise UserError(_("Valide primero el despiece."))
            lines = batch.line_ids.filtered(lambda line: not line.product_tmpl_id and line.state != "discarded")
            lines._run_batch_operation("_prepare_product")
            batch._update_state_after_processing()
        return True

    def action_create_or_update_products(self):
        return self.action_prepare_products()

    def action_finalize_ready_lines(self):
        for batch in self:
            batch._lock_for_processing()
            if batch.state not in ("products_prepared", "partial_created"):
                raise UserError(_("Prepare primero los productos."))
            batch.prepared_line_ids._run_batch_operation("_finalize_piece")
            batch._update_state_after_processing()
        return True

    def action_cancel(self):
        for batch in self:
            batch._lock_for_processing()
            if batch.line_ids.filtered(lambda line: line.stock_move_id or line.state == "created"):
                raise UserError(_("Este despiece tiene stock procesado. No se puede cancelar."))
            products = batch.line_ids.mapped("product_tmpl_id").sorted("id")
            for product in products:
                line = batch.line_ids.filtered(lambda item: item.product_tmpl_id == product)[:1]
                line._lock_product(product)
                if product.wex_teardown_preparation_state != "pending" or product.wex_teardown_origin_line_id.batch_id != batch:
                    continue
                replacement = self.env["wex.teardown.line"].search([
                    ("product_tmpl_id", "=", product.id), ("batch_id", "!=", batch.id),
                    ("batch_id.state", "!=", "cancelled"), ("state", "=", "product_prepared"),
                ], order="id", limit=1)
                if replacement:
                    product._write_teardown_values({"wex_teardown_origin_line_id": replacement.id})
                else:
                    product._write_teardown_values({"wex_teardown_preparation_state": "cancelled"})
            batch._write_lifecycle({"state": "cancelled"})
            # Liberar la clave antes de que otro lote del mismo dispositivo se inserte.
            batch.flush_recordset(["state", "device_identity_key"])
        return True

    def _update_state_after_processing(self):
        self.ensure_one()
        lines = self.line_ids.filtered(lambda line: line.state != "discarded")
        if self.state == "cancelled":
            return
        if lines and all(line.state == "created" for line in lines):
            state = "done"
        elif any(line.state == "created" for line in lines):
            state = "partial_created"
        elif any(line.product_tmpl_id for line in lines):
            state = "products_prepared"
        else:
            state = "validated"
        self._write_lifecycle({"state": state, "workflow_focus": "products"})

    def _check_stock_location(self):
        super()._check_stock_location()
        location = self.company_id.wex_teardown_default_location_id
        if location.usage != "internal" or (location.company_id and location.company_id != self.company_id):
            raise UserError(_("Seleccione una ubicación interna de la compañía del despiece."))
