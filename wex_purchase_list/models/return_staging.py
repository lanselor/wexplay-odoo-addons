import math

from odoo import _, api, Command, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_compare, float_is_zero, float_round


class WexPurchaseReturn(models.Model):
    _inherit = "wex.purchase.return"

    sale_order_id = fields.Many2one("sale.order", readonly=True, copy=False, ondelete="restrict", check_company=True)
    lot_id = fields.Many2one("stock.lot", readonly=True, copy=False, ondelete="restrict", check_company=True)
    source_location_id = fields.Many2one("stock.location", readonly=True, copy=False, ondelete="restrict", check_company=True)
    state = fields.Selection([
        ("draft", "Sin traslado"), ("pending_transfer", "Traslado pendiente"),
        ("pending", "Pendiente de envío"), ("return_prepared", "Devolución preparada"),
        ("returned", "Devuelto"), ("cancelled", "Cancelado"),
    ], compute="_compute_state", store=True)

    _sql_constraints = [
        ("internal_picking_unique", "unique(internal_picking_id)", "El traslado ya está vinculado a otra pieza apartada."),
    ]

    @api.depends("internal_picking_id.state", "return_picking_id.state")
    def _compute_state(self):
        for record in self:
            if record.return_picking_id.state == "done":
                record.state = "returned"
            elif record.internal_picking_id.state == "cancel":
                record.state = "cancelled"
            elif not record.internal_picking_id:
                record.state = "draft"
            elif record.internal_picking_id.state != "done":
                record.state = "pending_transfer"
            elif record.return_picking_id and record.return_picking_id.state != "cancel":
                record.state = "return_prepared"
            else:
                record.state = "pending"

    def _get_source_committed_quantity(self):
        self.ensure_one()
        cancelled = self.internal_picking_id.state == "cancel" and self.return_picking_id.state != "done"
        return 0 if cancelled else self.quantity

    def _get_receipt_committed_quantity(self):
        self.ensure_one()
        if not self._get_source_committed_quantity() or (self.return_picking_id and self.return_picking_id.state != "cancel"):
            return 0
        return self.quantity

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            line = self.env["wex_purchase_list.line"].browse(vals.get("purchase_list_line_id"))
            line.check_access("read")
            vals["repair_id"] = line.repair_id.id
            vals["sale_order_id"] = (line.sale_line_id.order_id or line.repair_id.sale_order_id).id
        return super().create(vals_list)

    def write(self, vals):
        identity_fields = {"purchase_list_line_id", "receipt_move_id", "company_id", "quantity", "source_location_id", "lot_id", "sale_order_id", "repair_id"}
        if identity_fields.intersection(vals) and any(self.mapped("internal_picking_id")):
            raise UserError(_("No puedes modificar la identidad o cantidad de una pieza que ya tiene un traslado."))
        for field in ("internal_picking_id", "return_picking_id"):
            if field in vals and any(record[field] and record[field].id != vals[field] for record in self):
                raise UserError(_("No puedes reemplazar una operación de inventario ya vinculada."))
        return super().write(vals)

    @api.constrains("purchase_list_line_id", "receipt_move_id", "quantity", "internal_picking_id", "return_picking_id")
    def _check_total_committed_quantity(self):
        for record in self:
            record.purchase_list_line_id._check_return_capacity(record.receipt_move_id, 0)


class StockMove(models.Model):
    _inherit = "stock.move"

    wex_return_ids = fields.One2many("wex.purchase.return", "receipt_move_id")
    wex_return_committed_qty = fields.Float(
        compute="_compute_wex_return_committed_qty", store=True, copy=False,
        digits="Product Unit of Measure", string="Unidades apartadas para devolver",
    )

    @api.depends("wex_return_ids.quantity", "wex_return_ids.state", "wex_return_ids.return_picking_id.state")
    def _compute_wex_return_committed_qty(self):
        for move in self:
            move.wex_return_committed_qty = sum(record._get_receipt_committed_quantity() for record in move.wex_return_ids)

    def action_prepare_vendor_return(self):
        self.ensure_one()
        if not self.purchase_list_line_id:
            raise UserError(_("La pieza no tiene una línea de compra vinculada."))
        return self.purchase_list_line_id._open_vendor_return_wizard(self)


class WexPurchaseListLine(models.Model):
    _inherit = "wex_purchase_list.line"

    def write(self, vals):
        origin_fields = {"repair_id", "sale_line_id", "repair_part_move_id"}.intersection(vals)
        if origin_fields:
            for line in self:
                changed = any(line[field].id != (vals[field] or False) for field in origin_fields)
                # Comprobar existencia sin exponer trazas fuera del contexto del editor.
                if changed and self.env["wex.purchase.return"].sudo().search_count([("purchase_list_line_id", "=", line.id)]):
                    raise UserError(_("No puedes cambiar el origen de una línea con trazabilidad de devolución. Revisa el documento de origen."))
        return super().write(vals)

    return_ids = fields.One2many("wex.purchase.return", "purchase_list_line_id", string="Piezas apartadas")
    can_prepare_vendor_return = fields.Boolean(compute="_compute_can_prepare_vendor_return")
    wex_return_quantity = fields.Float(
        compute="_compute_wex_return_quantity", store=True, copy=False,
        digits="Product Unit of Measure", string="Unidades destinadas a devolución",
    )

    @api.depends("return_ids.quantity", "return_ids.state")
    def _compute_wex_return_quantity(self):
        for line in self:
            line.wex_return_quantity = sum(record._get_source_committed_quantity() for record in line.return_ids)

    def _can_manage_vendor_returns(self):
        return self.env.su or self.env.user.has_group("wex_purchase_list.group_wex_purchase_list_manager")

    @api.depends("purchase_order_line_id", "state", "company_id")
    @api.depends_context("uid", "allowed_company_ids")
    def _compute_can_prepare_vendor_return(self):
        allowed = self._can_manage_vendor_returns()
        for line in self:
            line.can_prepare_vendor_return = bool(allowed and line.purchase_order_line_id and line.state != "cancelled" and line.company_id in self.env.companies)

    def _check_return_access(self):
        self.ensure_one()
        self.check_access("write")
        if self.company_id not in self.env.companies:
            raise UserError(_("Activa la compañía de la línea para gestionar su devolución."))
        if not self._can_manage_vendor_returns():
            raise UserError(_("Solo los responsables de la lista de compra pueden apartar piezas para devolución."))

    def _get_return_receipts(self):
        self.ensure_one()
        return self.purchase_order_line_id.move_ids.filtered(lambda move:
            move.state == "done" and move.picking_id.state == "done"
            and move.location_id.usage == "supplier" and move.location_dest_id.usage == "internal"
            and not move.origin_returned_move_id and move.product_id == self.product_id
        )

    def _get_return_repair_moves(self):
        self.ensure_one()
        linked = self.env["stock.move"].search([
            ("purchase_list_line_id", "=", self.id), ("repair_id", "!=", False),
            ("company_id", "=", self.company_id.id), ("state", "!=", "cancel"),
        ]) | self.repair_part_move_id.filtered(lambda move: move.state != "cancel")
        return linked.filtered(lambda move: move.product_id == self.product_id)

    def _open_vendor_return_wizard(self, repair_move=None):
        self._check_return_access()
        receipts = self._get_return_receipts()
        if not receipts:
            raise UserError(_("No hay una recepción de proveedor validada para esta línea de compra."))
        remaining = self.quantity - self.wex_return_quantity
        if float_compare(remaining, 0, precision_rounding=self.product_id.uom_id.rounding) <= 0:
            raise UserError(_("Todas las unidades de esta línea ya están destinadas a devolución."))
        moves = self._get_return_repair_moves()
        if repair_move and repair_move not in moves:
            raise UserError(_("La pieza seleccionada no corresponde al origen de esta línea."))
        wizard = self.env["wex.return.prepare"].create({
            "purchase_list_line_id": self.id,
            "receipt_picking_id": receipts.picking_id.id if len(receipts.picking_id) == 1 else False,
            "receipt_move_id": receipts.id if len(receipts) == 1 else False,
            "repair_move_id": repair_move.id if repair_move else (moves.id if len(moves) == 1 else False),
            "quantity": min(max(1, self.product_id.uom_id.rounding), remaining),
        })
        return {"type": "ir.actions.act_window", "name": _("Devolver a proveedor"),
                "res_model": wizard._name, "res_id": wizard.id, "view_mode": "form", "target": "new"}

    def action_prepare_vendor_return(self):
        self.ensure_one()
        return self._open_vendor_return_wizard()

    def _get_native_return_quantity(self, receipt):
        returned = receipt.returned_move_ids.filtered(lambda move:
            move.state != "cancel" and move.location_dest_id.usage == "supplier"
        )
        return sum(move.product_uom._compute_quantity(
            move.quantity if move.state == "done" else move.product_uom_qty, self.product_id.uom_id,
        ) for move in returned)

    def _check_return_capacity(self, receipt, extra_quantity):
        self.ensure_one()
        rounding = self.product_id.uom_id.rounding
        source_committed = sum(record._get_source_committed_quantity() for record in self.return_ids)
        if float_compare(source_committed + extra_quantity, self.quantity, precision_rounding=rounding) > 0:
            raise UserError(_("La cantidad supera las unidades de esta línea aún no destinadas a devolución."))
        received = receipt.product_uom._compute_quantity(receipt.quantity, self.product_id.uom_id)
        receipt_committed = sum(record._get_receipt_committed_quantity() for record in receipt.wex_return_ids)
        committed = receipt_committed + self._get_native_return_quantity(receipt) + extra_quantity
        if float_compare(committed, received, precision_rounding=rounding) > 0:
            raise UserError(_("La recepción ya tiene unidades devueltas o destinadas a devolución. Revisa la cantidad."))

    def _lock_return_request(self, receipt):
        # Los acumulados almacenados actualizan ambas filas y provocan reintento
        # transaccional nativo si dos solicitudes concurrentes usan la misma capacidad.
        self.env.flush_all()
        self.env.cr.execute("SELECT id FROM wex_purchase_list_line WHERE id = %s FOR UPDATE", [self.id])
        self.env.cr.execute("SELECT id FROM stock_move WHERE id = %s FOR UPDATE", [receipt.id])
        self.invalidate_recordset()
        receipt.invalidate_recordset()

    def _get_origin_sale_line(self, repair_move):
        self.ensure_one()
        return repair_move.sale_line_id if repair_move else self.sale_line_id

    def _check_origin_for_return(self, repair_move, quantity):
        moves = self._get_return_repair_moves()
        if (moves and not repair_move) or (repair_move and repair_move not in moves):
            raise UserError(_("Selecciona la pieza del SAT que deseas retirar o reducir."))
        if repair_move:
            repair_move.check_access("write")
            if repair_move.state == "done" or repair_move.repair_id.state in ("done", "delivered") or repair_move.picked:
                raise UserError(_("La pieza está realizada o marcada como utilizada en el SAT. Revísala desde la reparación antes de devolverla."))
            if repair_move.repair_line_type != "add":
                raise UserError(_("Solo se pueden retirar automáticamente piezas de tipo Añadir."))
        sale_line = self._get_origin_sale_line(repair_move)
        if repair_move and self.sale_line_id and self.sale_line_id != sale_line:
            raise UserError(_("La línea tiene varios orígenes de venta. Revísalos desde los documentos antes de apartar la pieza."))
        if sale_line:
            sale_line.check_access("write")
            if sale_line.order_id.locked:
                raise UserError(_("La venta está bloqueada. Revísala desde su documento."))
            if sale_line.invoice_lines.filtered(lambda item: item.move_id.state != "cancel"):
                raise UserError(_("El artículo tiene una factura confirmada o en borrador. Resuelve la facturación desde el documento antes de retirarlo."))
            if sale_line.qty_delivered > 0 or sale_line.move_ids.filtered(lambda move: move.state == "done"):
                raise UserError(_("El artículo tiene movimientos realizados. Revisa la entrega antes de devolverlo."))
            if repair_move and (sale_line.move_ids - repair_move).filtered(lambda move: move.state != "cancel"):
                raise UserError(_("La línea de venta agrupa otras piezas. Revísala desde el SAT antes de modificarla."))
        origin = repair_move or sale_line
        if not origin or (sale_line and not repair_move and sale_line.order_id.state == "cancel"):
            return False
        uom = repair_move.product_uom if repair_move else sale_line.product_uom
        origin_quantity = repair_move.product_uom_qty if repair_move else sale_line.product_uom_qty
        if origin_quantity <= 0:
            return False
        reduction = self.product_id.uom_id._compute_quantity(quantity, uom, round=False)
        rounded = float_round(reduction, precision_rounding=uom.rounding)
        if not float_is_zero(reduction - rounded, precision_digits=6):
            raise UserError(_("La cantidad no es compatible con la unidad del SAT o la venta. Ajusta la cantidad desde el documento."))
        if float_compare(reduction, origin_quantity, precision_rounding=uom.rounding) > 0:
            raise UserError(_("La cantidad supera la pendiente en el SAT o la venta seleccionados."))
        return origin_quantity - reduction

    def _adjust_return_origin(self, repair_move, new_quantity, confirmed):
        if new_quantity is False:
            return
        if not confirmed:
            raise UserError(_("Confirma expresamente que deseas retirar o reducir el producto del SAT o la venta."))
        if repair_move:
            if float_is_zero(new_quantity, precision_rounding=repair_move.product_uom.rounding):
                repair_move.unlink()
            else:
                repair_move.write({"product_uom_qty": new_quantity})
            return
        sale_line = self.sale_line_id
        if sale_line.order_id.state in ("draft", "sent") and float_is_zero(new_quantity, precision_rounding=sale_line.product_uom.rounding):
            sale_line.unlink()
        else:
            sale_line.write({"product_uom_qty": new_quantity})

    def _check_staging_locations(self, receipt, source, lot, package):
        company = self.company_id
        company._check_wex_return_location()
        destination = company.wex_return_location_id
        if not destination:
            raise UserError(_("Configura la ubicación de devoluciones de la compañía."))
        if not source.active or source.usage != "internal" or source.company_id != company or source.scrap_location:
            raise UserError(_("Selecciona una ubicación interna activa de la compañía como origen."))
        if source.parent_path.startswith(destination.parent_path):
            raise UserError(_("La pieza ya está en una ubicación de devoluciones."))
        product = self.product_id
        if product.tracking != "none" and not lot:
            raise UserError(_("Selecciona el lote o número de serie recibido."))
        if lot and (lot.product_id != product or lot.company_id not in (company, self.env["res.company"])):
            raise UserError(_("El lote no corresponde al producto y a la compañía."))
        if lot and lot not in receipt.move_line_ids.lot_id:
            raise UserError(_("El lote seleccionado no forma parte de esta recepción."))
        if package and package.company_id and package.company_id != company:
            raise UserError(_("El paquete no pertenece a la compañía."))
        return destination

    def _get_staging_picking_type(self, receipt, source):
        warehouse = source.warehouse_id or receipt.picking_id.picking_type_id.warehouse_id
        picking_type = warehouse.int_type_id
        if not picking_type or not picking_type.active or picking_type.company_id != self.company_id:
            raise UserError(_("No hay un tipo de traslado interno activo para este almacén. Revisa Ubicaciones de almacenamiento y los tipos de operación en Inventario."))
        return picking_type

    def _create_staging_transfer(self, receipt, quantity, source, destination, lot, package):
        product = self.product_id
        picking = self.env["stock.picking"].create({
            "company_id": self.company_id.id,
            "picking_type_id": self._get_staging_picking_type(receipt, source).id,
            "location_id": source.id, "location_dest_id": destination.id,
            "origin": _("Apartar para devolución: %s", self.display_name),
            "move_ids": [Command.create({
                "name": product.display_name, "product_id": product.id,
                "product_uom_qty": quantity, "product_uom": product.uom_id.id,
                "company_id": self.company_id.id,
                "location_id": source.id, "location_dest_id": destination.id,
            })],
        })
        picking.action_confirm()
        move = picking.move_ids
        move._do_unreserve()
        taken = move._update_reserved_quantity(quantity, source, lot_id=lot, package_id=package, strict=True)
        if float_compare(taken, quantity, precision_rounding=product.uom_id.rounding) != 0:
            raise UserError(_("No hay suficientes unidades libres en esa ubicación, lote y paquete. No se han liberado reservas de otras operaciones."))
        if any(item.location_id != source or item.lot_id != lot or item.owner_id for item in move.move_line_ids):
            raise UserError(_("La reserva obtenida no corresponde a las unidades seleccionadas."))
        move._recompute_state()
        move.picked = True
        picking.button_validate()
        if picking.state != "done":
            raise UserError(_("Odoo requiere una comprobación adicional para ese traslado. Revisa la configuración de inventario; no se ha apartado la pieza."))
        return picking

    def _stage_vendor_return(self, receipt, quantity, source, lot, package, repair_move, confirmed, rma_reference, return_reason=False, return_notes=False):
        self._check_return_access()
        if not return_reason:
            raise UserError(_("Selecciona el motivo de devolución."))
        if receipt not in self._get_return_receipts() or self.state == "cancelled":
            raise UserError(_("La recepción no es válida para esta línea de compra."))
        if not math.isfinite(quantity) or float_compare(quantity, 0, precision_rounding=self.product_id.uom_id.rounding) <= 0:
            raise UserError(_("Indica una cantidad positiva."))
        if not self.product_id.is_storable:
            raise UserError(_("El producto debe tener seguimiento de inventario para apartar existencias."))
        if not float_is_zero(quantity - float_round(quantity, precision_rounding=self.product_id.uom_id.rounding), precision_digits=6):
            raise UserError(_("La cantidad no es compatible con el redondeo de la unidad del producto."))
        if self.product_id.tracking == "serial" and quantity != 1:
            raise UserError(_("Aparta un número de serie por operación."))
        with self.env.cr.savepoint():
            self._lock_return_request(receipt)
            if repair_move:
                self.env.cr.execute("SELECT id FROM stock_move WHERE id = %s FOR UPDATE", [repair_move.id])
                repair_move.invalidate_recordset()
            sale_line = self._get_origin_sale_line(repair_move)
            if sale_line:
                sale_line.check_access("write")
                self.env.cr.execute("SELECT id FROM sale_order_line WHERE id = %s FOR UPDATE", [sale_line.id])
                sale_line.invalidate_recordset()
            destination = self._check_staging_locations(receipt, source, lot, package)
            self._check_return_capacity(receipt, quantity)
            new_quantity = self._check_origin_for_return(repair_move, quantity)
            trace = self.env["wex.purchase.return"].create({
                "company_id": self.company_id.id, "purchase_list_line_id": self.id,
                "receipt_move_id": receipt.id, "quantity": quantity, "rma_reference": rma_reference,
                "source_location_id": source.id, "lot_id": lot.id,
                "return_reason": return_reason, "return_notes": return_notes,
            })
            self.flush_recordset(["wex_return_quantity"])
            receipt.flush_recordset(["wex_return_committed_qty"])
            self._adjust_return_origin(repair_move, new_quantity, confirmed)
            picking = self._create_staging_transfer(receipt, quantity, source, destination, lot, package)
            trace.internal_picking_id = picking
            if not self.customer_notified and float_compare(self.wex_return_quantity, self.quantity, precision_rounding=self.product_id.uom_id.rounding) >= 0:
                self.is_reservation = False
            picking.message_post(body=_("Pieza apartada para devolución al proveedor. Referencia RMA: %s", rma_reference or "—"))
            return trace

    def _check_can_mark_customer_notified(self):
        super()._check_can_mark_customer_notified()
        if any(line.wex_return_quantity > 0 and float_compare(line.wex_return_quantity, line.quantity, precision_rounding=line.product_id.uom_id.rounding) >= 0 for line in self):
            raise UserError(_("Todas las unidades están destinadas a devolución; no hay un repuesto disponible para avisar al cliente."))

    @api.constrains("quantity")
    def _check_return_source_quantity(self):
        for line in self:
            if float_compare(line.wex_return_quantity, line.quantity, precision_rounding=line.product_id.uom_id.rounding) > 0:
                raise ValidationError(_("La cantidad de la línea no puede ser menor que las unidades destinadas a devolución."))
