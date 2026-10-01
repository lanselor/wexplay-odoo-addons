import logging

from psycopg2 import OperationalError

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.osv import expression

from .product_template import _TEARDOWN_TOKEN

_logger = logging.getLogger(__name__)


class WexTeardownLineLifecycle(models.Model):
    _inherit = "wex.teardown.line"

    state = fields.Selection(selection_add=[("product_prepared", "Producto preparado")],
                             ondelete={"product_prepared": "set default"})
    product_image = fields.Image(related="product_tmpl_id.image_128", string="Imagen principal")
    product_code = fields.Char(related="product_tmpl_id.default_code", string="Referencia")
    product_active = fields.Boolean(related="product_tmpl_id.active")
    product_tmpl_id = fields.Many2one(string="Producto preparado", ondelete="restrict")
    product_snapshot = fields.Json(copy=False, readonly=True)
    finalized_at = fields.Datetime(string="Finalizada el", readonly=True, copy=False)
    finalized_by = fields.Many2one("res.users", string="Finalizada por", readonly=True, copy=False)

    _LIFECYCLE_FIELDS = {
        "product_tmpl_id", "stock_move_id", "stock_ref", "product_snapshot",
        "finalized_at", "finalized_by",
        "company_id", "device_type", "model_id", "brand_id", "product_category_id",
    }
    _IDENTITY_FIELDS = {
        "batch_id", "component_type_id", "part_number", "quantity", "name_final",
        "decision", "existing_product_id", "qc_state", "missing_part_number_confirmed",
    }
    _ECONOMIC_FIELDS = {"list_price", "standard_price", "tax_ids", "existing_product_update_name", "pvp_tax_included"}

    @api.model_create_multi
    def create(self, vals_list):
        if self.env.context.get("_teardown_token") is not _TEARDOWN_TOKEN:
            for vals in vals_list:
                if self._LIFECYCLE_FIELDS & vals.keys() or vals.get("state", "draft") != "draft":
                    raise UserError(_("Cree la pieza en borrador y utilice las acciones del despiece."))
                batch = self.env["wex.teardown.batch"].browse(vals.get("batch_id"))
                batch.check_access("write")
                if batch.state not in ("draft", "template_loaded", "review"):
                    raise UserError(_("Solo se pueden añadir piezas durante la revisión."))
        return super().create(vals_list)

    def write(self, vals):
        if self.env.context.get("_teardown_token") is not _TEARDOWN_TOKEN:
            if self._LIFECYCLE_FIELDS & vals.keys() or vals.get("state") in ("created", "product_prepared"):
                raise UserError(_("Use Preparar producto o Finalizar pieza."))
            for line in self:
                if (self._IDENTITY_FIELDS | self._ECONOMIC_FIELDS) & vals.keys():
                    if line.batch_id.state == "cancelled" or line.state == "created":
                        raise UserError(_("No se puede modificar una pieza finalizada o cancelada."))
                    if line.product_tmpl_id:
                        if self._IDENTITY_FIELDS & vals.keys() or line.decision == "create_new":
                            raise UserError(_("La ficha ya está preparada. Edite los datos del producto o rectifique la preparación."))
                if "state" in vals and line.product_tmpl_id and vals["state"] != line.state:
                    raise UserError(_("No se puede cambiar el estado de una pieza preparada manualmente."))
        result = super().write(vals)
        if (self._IDENTITY_FIELDS | self._ECONOMIC_FIELDS) & vals.keys():
            self.mapped("batch_id").write({"warning_confirmed": False})
        return result

    def unlink(self):
        if any(line.product_tmpl_id or line.stock_move_id for line in self):
            raise UserError(_("No se pueden eliminar piezas con producto preparado o movimiento de stock."))
        return super().unlink()

    def _write_lifecycle(self, vals):
        return self.with_context(_teardown_token=_TEARDOWN_TOKEN).write(vals)

    def _lock_for_processing(self):
        self.ensure_one()
        self.check_access("write")
        self.batch_id._lock_for_processing()
        self.flush_recordset()
        self.env.cr.execute("SELECT id FROM wex_teardown_line WHERE id = %s FOR UPDATE", [self.id])
        self.invalidate_recordset()

    def _check_product_scope(self, product):
        product.check_access("write")
        if not product or (product.company_id and product.company_id != self.company_id):
            raise UserError(_("El producto no pertenece a la compañía del despiece."))
        if product.wex_condition != "refurbished":
            raise UserError(_("Seleccione un producto reacondicionado."))
        if not product.active and product.wex_teardown_preparation_state != "pending" and not self._can_recover_preparation(product):
            raise UserError(_("El producto está archivado fuera de una preparación activa. Revise el catálogo."))

    def _can_recover_preparation(self, product):
        return (product.wex_teardown_preparation_state == "cancelled"
                and self.env.user.has_group("wex_teardown.group_wex_teardown_manager"))

    def _check_no_product_stock(self, product):
        variants = product.with_context(active_test=False).product_variant_ids
        if self.env["stock.move"].search_count([("product_id", "in", variants.ids), ("state", "=", "done")]):
            raise UserError(_("El producto ya tiene movimientos finalizados. Revise el catálogo antes de rectificar su preparación."))

    def _lock_product(self, product):
        product.check_access("write")
        product.flush_recordset()
        # UPDATE provoca reintento de transacción en REPEATABLE READ si otro proceso lo cambió.
        self.env.cr.execute("UPDATE product_template SET write_date = write_date WHERE id = %s", [product.id])
        product.invalidate_recordset()

    def _get_catalog_domain(self):
        return [
            ("wex_condition", "=", "refurbished"),
            ("company_id", "in", [False, self.company_id.id]),
        ]

    def _get_exact_products(self):
        domains = [[("name", "=", self.name_final)]]
        if self.part_number:
            domains.append([
                ("wex_teardown_component_id", "=", self.component_type_id.id),
                ("wex_teardown_model_id", "=", self.model_id.id),
                ("wex_teardown_part_number", "=", self.part_number),
            ])
        return self.env["product.template"].with_context(active_test=False).search(
            expression.AND([self._get_catalog_domain(), expression.OR(domains)]), limit=10,
        )

    def _lock_catalog_creation(self):
        # Serializa solo las preparaciones de catálogo; la secuencia conserva su valor.
        # El UPDATE es necesario: un advisory lock solo no renueva el snapshot de Odoo.
        sequence = self.env.ref("wex_teardown.seq_wex_teardown_batch")
        self.env.cr.execute("UPDATE ir_sequence SET write_date = write_date WHERE id = %s", [sequence.id])

    def action_prepare_product(self):
        for line in self:
            with self.env.cr.savepoint():
                line._prepare_product()
        return True

    def action_create_or_update_product(self):
        return self.action_prepare_product()

    def _prepare_product(self):
        self._lock_for_processing()
        if self.batch_id.state not in ("validated", "products_prepared", "partial_created"):
            raise UserError(_("Valide el despiece antes de preparar productos."))
        if self.product_tmpl_id:
            return self.product_tmpl_id
        self.batch_id._check_device_identity()
        errors, warnings = self._validate_line()
        if errors or self.qc_state != "ok" or self.decision not in ("create_new", "use_existing"):
            raise UserError("\n".join(errors) or _("La pieza debe estar apta y tener una decisión de producto."))
        if warnings and not self.batch_id.warning_confirmed:
            raise UserError(_("Confirme las advertencias antes de preparar."))
        if self.decision == "use_existing":
            product = self.existing_product_id.with_context(active_test=False).with_company(self.company_id)
            self._lock_product(product)
            self._check_product_scope(product)
            if self._can_recover_preparation(product):
                self._check_no_product_stock(product)
                product._write_teardown_values({
                    "wex_teardown_origin_line_id": self.id, "wex_teardown_preparation_state": "pending",
                })
        else:
            self._lock_catalog_creation()
            exact = self._get_exact_products()
            if exact:
                raise UserError(_("Ya existe una coincidencia exacta: %s. Abra la pestaña Piezas y reutilícela.") % exact[0].display_name)
            vals = self._prepare_product_create_vals()
            vals.update(active=False, is_published=False, company_id=self.company_id.id,
                        wex_teardown_origin_line_id=self.id, wex_teardown_preparation_state="pending")
            product = self.env["product.template"].with_company(self.company_id).with_context(
                active_test=False, _teardown_token=_TEARDOWN_TOKEN,
            ).create(vals)
            product = product.with_context(_teardown_token=None)
        self._write_lifecycle({
            "product_tmpl_id": product.id, "state": "product_prepared",
            "product_snapshot": self._get_product_snapshot(product),
            "validation_status": "ok", "validation_message": False,
        })
        self.batch_id._update_state_after_processing()
        return product

    def _get_product_snapshot(self, product):
        product = product.with_company(self.company_id)
        return {
            "name": product.name, "list_price": product.list_price,
            "standard_price": product.standard_price, "tax_ids": sorted(product.taxes_id.ids),
            "category": product.categ_id.id, "component": product.wex_teardown_component_id.id,
            "part_number": product.wex_teardown_part_number or "", "model": product.wex_teardown_model_id.id,
        }

    def action_refresh_product_proposal(self):
        self.ensure_one()
        self._lock_for_processing()
        if self.state != "product_prepared" or self.decision != "use_existing" or self.batch_id.state == "cancelled":
            raise UserError(_("Solo se puede revisar una reutilización pendiente."))
        product = self.product_tmpl_id.with_company(self.company_id)
        self._lock_product(product)
        self._check_product_scope(product)
        vals = self._prepare_existing_product_prefill_vals(product)
        vals.update(name_final=product.name, existing_product_update_name=False,
                    product_snapshot=self._get_product_snapshot(product))
        self._write_lifecycle(vals)
        return self.action_open_edit_form()

    def _check_can_finalize(self):
        self.ensure_one()
        if self.batch_id.state not in ("products_prepared", "partial_created", "validated"):
            raise UserError(_("El despiece no está pendiente de finalización."))
        if self.state != "product_prepared" or self.qc_state != "ok" or not self.product_tmpl_id:
            raise UserError(_("Prepare primero una pieza apta."))
        self.batch_id._check_device_identity()
        self.batch_id._check_stock_location()
        if self.stock_move_id:
            raise UserError(_("La pieza ya tiene un movimiento. Revíselo antes de continuar."))
        product = self.product_tmpl_id.with_context(active_test=False).with_company(self.company_id)
        self._check_product_scope(product)
        variants = product.product_variant_ids
        if len(variants) != 1 or variants.tracking != "none" or not product.is_storable:
            raise UserError(_("Esta fase requiere un producto almacenable con una variante y sin seguimiento por lote/serie."))
        if not product.image_1920:
            raise UserError(_("Suba la imagen principal del producto antes de finalizar."))
        if self.quantity <= 0 or product.list_price <= 0 or not product.categ_id:
            raise UserError(_("Revise cantidad, categoría y precio del producto."))
        if self.decision == "use_existing":
            if self.product_snapshot != self._get_product_snapshot(product):
                raise UserError(_("El producto ha cambiado. Use Revisar propuesta para cargar sus valores actuales antes de aplicar cambios."))
            if self.list_price <= 0 or self.standard_price < 0:
                raise UserError(_("Revise el precio y coste propuestos."))
        if not product.active and product.wex_teardown_preparation_state != "pending":
            raise UserError(_("Recupere primero la preparación del producto desde una pieza validada."))
        if any(tax.company_id != self.company_id for tax in self.tax_ids):
            raise UserError(_("Los impuestos deben pertenecer a la compañía del despiece."))
        return product

    def action_finalize_piece(self):
        for line in self:
            with self.env.cr.savepoint():
                line._finalize_piece()
        return True

    def _finalize_piece(self):
        self._lock_for_processing()
        if self.state == "created" and self.stock_move_id.state == "done":
            return
        self._lock_product(self.product_tmpl_id)
        product = self._check_can_finalize()
        if self.decision == "use_existing":
            product.write(self._prepare_product_update_vals(product))
        if product.wex_teardown_preparation_state == "pending":
            product._write_teardown_values({"active": True, "wex_teardown_preparation_state": "ready"})
        # El token solo circula dentro de esta operación validada, nunca en acciones del cliente.
        move = self.with_context(_teardown_token=_TEARDOWN_TOKEN)._create_stock_entry(product.with_context(active_test=False))
        if move.state != "done":
            raise UserError(_("El movimiento no ha quedado finalizado; no se activará el producto."))
        self._write_lifecycle({
            "state": "created", "stock_move_id": move.id, "stock_ref": move.reference or move.name,
            "finalized_at": fields.Datetime.now(), "finalized_by": self.env.uid,
            "validation_status": "ok", "validation_message": False,
        })
        self.batch_id._write_lifecycle({"processed_at": fields.Datetime.now(), "processed_by": self.env.uid})
        self.batch_id._update_state_after_processing()
        self.batch_id.message_post(body=_("Pieza finalizada: %s") % self.display_name)

    def _run_batch_operation(self, operation):
        for line in self.sorted("id"):
            try:
                with self.env.cr.savepoint():
                    getattr(line, operation)()
            except OperationalError:
                raise  # Odoo debe reintentar las carreras de serialización completas.
            except Exception as error:
                _logger.exception("Teardown operation failed for line %s", line.id)
                line._write_lifecycle({"validation_status": "error", "validation_message": str(error)})
                line.batch_id.message_post(body=_("Pieza pendiente %s: %s") % (line.display_name, error))

    def action_open_prepared_product(self):
        self.ensure_one()
        self.check_access("read")
        if not self.product_tmpl_id:
            raise UserError(_("Prepare primero el producto."))
        return self.action_open_existing_product(self.product_tmpl_id.id)

    def action_reset_preparation(self):
        self.ensure_one()
        self._lock_for_processing()
        if not self.env.user.has_group("wex_teardown.group_wex_teardown_manager"):
            raise UserError(_("Solo un responsable puede rectificar una preparación."))
        if self.state != "product_prepared" or self.stock_move_id or self.batch_id.state == "cancelled":
            raise UserError(_("Solo se puede rectificar una preparación sin stock."))
        product = self.product_tmpl_id
        self._lock_product(product)
        if product.wex_teardown_origin_line_id == self:
            self._check_no_product_stock(product)
            others = self.search([("product_tmpl_id", "=", product.id), ("id", "!=", self.id)])
            if others or product.active or product.wex_teardown_preparation_state != "pending":
                raise UserError(_("La ficha ya está compartida o activada. No se puede desvincular."))
            product._write_teardown_values({"wex_teardown_preparation_state": "cancelled"})
        self._write_lifecycle({"product_tmpl_id": False, "product_snapshot": False, "state": "draft"})
        self.batch_id._write_lifecycle({"state": "review", "workflow_focus": "pieces"})
        return True
