from collections import defaultdict

from odoo import _, api, Command, fields, models
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare, float_is_zero


class WexPurchaseReturn(models.Model):
    _inherit = "wex.purchase.return"

    dispatch_move_ids = fields.One2many("stock.move", "wex_vendor_return_id")
    return_picking_ids = fields.Many2many("stock.picking", compute="_compute_return_pickings", string="Documentos de devolución")
    staging_location_id = fields.Many2one(related="internal_picking_id.location_dest_id", string="Ubicación de devoluciones", store=True)
    returned_quantity = fields.Float(compute="_compute_dispatch_quantities", store=True, digits="Product Unit of Measure", string="Unidades devueltas")
    prepared_quantity = fields.Float(compute="_compute_dispatch_quantities", store=True, digits="Product Unit of Measure", string="Unidades en devolución preparada")
    remaining_quantity = fields.Float(compute="_compute_dispatch_quantities", store=True, digits="Product Unit of Measure", string="Unidades pendientes de envío")
    state = fields.Selection(selection_add=[("partial", "Gestión parcial")])

    @api.depends("dispatch_move_ids.picking_id", "return_picking_id")
    def _compute_return_pickings(self):
        for record in self:
            record.return_picking_ids = record.dispatch_move_ids.picking_id | record.return_picking_id

    @api.depends("quantity", "dispatch_move_ids.state", "dispatch_move_ids.quantity", "dispatch_move_ids.product_uom_qty", "dispatch_move_ids.product_uom", "dispatch_move_ids.location_id.usage", "dispatch_move_ids.location_dest_id.usage", "recovered_quantity", "scrapped_quantity")
    def _compute_dispatch_quantities(self):
        for record in self:
            returned, prepared = record._get_dispatch_totals()
            record.returned_quantity = max(0, returned)
            record.prepared_quantity = prepared
            record.remaining_quantity = max(0, record.quantity - returned - record.recovered_quantity - record.scrapped_quantity)

    def _get_dispatch_totals(self):
        self.ensure_one()
        returned = prepared = 0
        for move in self.dispatch_move_ids.filtered(lambda item: item.state != "cancel"):
            if move.location_dest_id.usage == "supplier":
                if move.state == "done":
                    returned += move.product_uom._compute_quantity(move.quantity, self.product_uom_id)
                else:
                    prepared += move.product_uom._compute_quantity(move.product_uom_qty, self.product_uom_id)
            elif move.location_id.usage == "supplier" and move.state == "done":
                returned -= move.product_uom._compute_quantity(move.quantity, self.product_uom_id)
        return returned, prepared

    @api.depends("internal_picking_id.state", "return_picking_id.state", "returned_quantity", "prepared_quantity", "dispatch_move_ids.state")
    def _compute_state(self):
        super()._compute_state()
        for record in self.filtered("dispatch_move_ids"):
            rounding = record.product_uom_id.rounding
            if float_compare(record.returned_quantity, record.quantity, precision_rounding=rounding) >= 0:
                record.state = "returned"
            elif not float_is_zero(record.returned_quantity, precision_rounding=rounding):
                record.state = "partial"
            elif record.internal_picking_id.state == "done":
                record.state = "return_prepared" if record.prepared_quantity else "pending"

    def _get_receipt_committed_quantity(self):
        self.ensure_one()
        if not self.dispatch_move_ids:
            return super()._get_receipt_committed_quantity()
        returned, prepared = self._get_dispatch_totals()
        return max(0, self.quantity - returned - prepared)

    def _check_dispatch_access(self):
        self.check_access("write")
        if not self.env.su and not self.env.user.has_group("wex_purchase_list.group_wex_purchase_list_manager"):
            raise UserError(_("Solo los responsables pueden preparar devoluciones o asignar RMA."))
        if any(record.company_id not in self.env.companies for record in self):
            raise UserError(_("Activa las compañías de las piezas seleccionadas."))
        if not self:
            raise UserError(_("Selecciona las piezas que deseas gestionar."))

    def _lock_dispatch_records(self):
        self.env.flush_all()
        for table, ids in (
            ("wex_purchase_list_line", self.purchase_list_line_id.ids),
            ("stock_move", self.receipt_move_id.ids),
            ("wex_purchase_return", self.ids),
        ):
            self.env.cr.execute(f"SELECT id FROM {table} WHERE id IN %s ORDER BY id FOR UPDATE", [tuple(sorted(ids))])
        self.invalidate_recordset()
        self.receipt_move_id.invalidate_recordset()

    def _check_ready_to_dispatch(self):
        for record in self:
            returned, prepared = record._get_dispatch_totals()
            if record.internal_picking_id.state != "done":
                raise UserError(_("Solo se pueden preparar piezas cuyo traslado a devoluciones esté realizado."))
            if float_compare(record.remaining_quantity, 0, precision_rounding=record.product_uom_id.rounding) <= 0:
                raise UserError(_("Una de las piezas seleccionadas ya está devuelta por completo."))
            if not float_is_zero(prepared, precision_rounding=record.product_uom_id.rounding):
                raise UserError(_("Una pieza ya tiene una devolución preparada. Abre sus documentos para continuar o cancelar esa operación."))
            if not record.staging_location_id.active or record.staging_location_id.usage != "internal":
                raise UserError(_("La ubicación donde está apartada la pieza no es una ubicación interna activa."))
            if record.receipt_move_id.move_dest_ids.filtered(lambda move: move.state not in ("done", "cancel")):
                raise UserError(_("La recepción mantiene operaciones dependientes pendientes. Revísalas desde Inventario antes de crear la devolución."))

    def _open_return_pickings(self, pickings):
        pickings.check_access("read")
        action = {"type": "ir.actions.act_window", "name": _("Devoluciones al proveedor"),
                  "res_model": "stock.picking", "view_mode": "list,form", "domain": [("id", "in", pickings.ids)],
                  "context": {"group_by": []}}
        if len(pickings) == 1:
            action.update({"view_mode": "form", "res_id": pickings.id})
        return action

    def action_view_return_pickings(self):
        self.check_access("read")
        return self._open_return_pickings(self.return_picking_ids)

    def action_open_dispatch(self):
        self._check_dispatch_access()
        self._check_ready_to_dispatch()
        wizard = self.env["wex.return.dispatch"].create({"return_ids": [Command.set(self.ids)]})
        return {"type": "ir.actions.act_window", "name": _("Preparar devolución al proveedor"),
                "res_model": wizard._name, "res_id": wizard.id, "view_mode": "form", "target": "new"}

    def action_open_rma_assignment(self):
        self._check_dispatch_access()
        if len(self.company_id) != 1 or len(self.vendor_id.commercial_partner_id) != 1:
            raise UserError(_("Selecciona piezas de una misma compañía y proveedor para asignar un RMA común."))
        wizard = self.env["wex.return.rma"].create({"return_ids": [Command.set(self.ids)]})
        return {"type": "ir.actions.act_window", "name": _("Asignar referencia RMA"),
                "res_model": wizard._name, "res_id": wizard.id, "view_mode": "form", "target": "new"}

    def _reserve_dispatch_moves(self, picking):
        moves = picking.move_ids
        moves._do_unreserve()
        for move in moves:
            record = move.wex_vendor_return_id
            if not record:
                raise UserError(_("Odoo ha generado un movimiento sin vínculo con la pieza apartada. Revisa la operación."))
            # La recepción conserva la referencia documental; el traslado realizado
            # aporta las líneas que abastecen físicamente la zona de devoluciones.
            move.write({"move_orig_ids": [Command.link(item.id) for item in record.internal_picking_id.move_ids.filtered(lambda item: item.product_id == record.product_id)]})
            quantity = move.product_uom._compute_quantity(move.product_uom_qty, record.product_uom_id)
            taken = move._update_reserved_quantity(quantity, record.staging_location_id, lot_id=record.lot_id, strict=True)
            if float_compare(taken, quantity, precision_rounding=record.product_uom_id.rounding) != 0:
                raise UserError(_("No hay suficientes unidades libres del lote o pieza en la zona de devoluciones. Revisa su ubicación o paquete desde Inventario."))
            if any(line.lot_id != record.lot_id or line.owner_id for line in move.move_line_ids):
                raise UserError(_("La reserva no corresponde al lote o propiedad de la pieza apartada."))
            move._recompute_state()

    def _create_native_dispatch(self):
        self._check_dispatch_access()
        with self.env.cr.savepoint():
            self._lock_dispatch_records()
            self._check_ready_to_dispatch()
            groups = defaultdict(lambda: self.browse())
            for record in self:
                groups[record.receipt_picking_id.id, record.staging_location_id.id] |= record
            pickings = self.env["stock.picking"]
            for records in groups.values():
                first = records[0]
                wizard = self.env["stock.return.picking"].create({
                    "picking_id": first.receipt_picking_id.id,
                    "wex_staging_location_id": first.staging_location_id.id,
                    "wex_return_trace_ids": [Command.set(records.ids)],
                })
                wizard.product_return_moves = [Command.clear()] + [Command.create({
                    "move_id": record.receipt_move_id.id, "product_id": record.product_id.id,
                    "quantity": record.remaining_quantity, "wex_return_trace_id": record.id,
                }) for record in records]
                picking = wizard._create_return()
                if picking.location_dest_id.usage != "supplier":
                    raise UserError(_("El tipo de devolución nativo no tiene destino proveedor. Revisa su configuración."))
                pickings |= picking
            # El asistente nativo puede desreservar documentos creados antes en
            # este mismo lote. Reservar al final únicamente los documentos nuevos.
            for picking in pickings:
                records = picking.move_ids.wex_vendor_return_id
                records._reserve_dispatch_moves(picking)
                for record in records.filtered(lambda item: not item.return_picking_id):
                    record.return_picking_id = picking
                picking.message_post(body=_("Devolución preparada desde las piezas apartadas. Comprueba su registro con el proveedor antes del envío."))
            self.flush_recordset()
            self.receipt_move_id.flush_recordset(["wex_return_committed_qty"])
            return pickings

    def _check_dispatch_move_identity(self, move):
        self.ensure_one()
        if move.company_id != self.company_id or move.product_id != self.product_id or move.purchase_line_id != self.purchase_order_line_id:
            raise UserError(_("El movimiento no corresponde a la compañía, producto o compra de la pieza apartada."))
        ancestors = move.origin_returned_move_id
        seen = set()
        while ancestors and ancestors.id not in seen and ancestors != self.receipt_move_id:
            seen.add(ancestors.id)
            ancestors = ancestors.origin_returned_move_id
        if ancestors != self.receipt_move_id:
            raise UserError(_("La operación no conserva el vínculo con la recepción original."))
        if move.picking_id.partner_id.commercial_partner_id != self.vendor_id.commercial_partner_id:
            raise UserError(_("El proveedor del documento no corresponde a la pieza apartada."))
        if any(line.lot_id != self.lot_id or line.owner_id for line in move.move_line_ids.filtered("picked")):
            raise UserError(_("No se puede validar una devolución con otro lote, serie o propietario."))

    def _check_dispatch_stock(self, lines):
        self.ensure_one()
        for line in lines:
            quants = self.env["stock.quant"]._gather(
                line.product_id, line.location_id, lot_id=line.lot_id,
                package_id=line.package_id, owner_id=line.owner_id, strict=True,
            ).filtered(lambda quant: quant.lot_id == line.lot_id)
            physical = sum(quants.mapped("quantity"))
            reserved = sum(quants.mapped("reserved_quantity"))
            quantity = line.product_uom_id._compute_quantity(line.quantity, self.product_uom_id)
            rounding = self.product_uom_id.rounding
            if float_compare(physical, reserved, precision_rounding=rounding) < 0 or float_compare(physical, quantity, precision_rounding=rounding) < 0:
                raise UserError(_("No hay stock físico suficiente en la zona de devoluciones. Revisa las existencias y reservas antes de validar."))

    def _get_dispatch_move_quantities(self, move):
        self._check_dispatch_move_identity(move)
        lines = move.move_line_ids.filtered("picked")
        quantity = sum(line.product_uom_id._compute_quantity(line.quantity, self.product_uom_id) for line in lines)
        location = self.staging_location_id
        if move.location_dest_id.usage == "supplier":
            if not move.location_id.parent_path.startswith(location.parent_path) or any(not line.location_id.parent_path.startswith(location.parent_path) or line.location_dest_id.usage != "supplier" for line in lines):
                raise UserError(_("Las unidades deben salir de la zona donde se apartaron para devolución."))
            self._check_dispatch_stock(lines)
            return quantity, 0
        if move.location_id.usage == "supplier" and move.location_dest_id.usage == "internal":
            if any(line.location_id.usage != "supplier" or line.location_dest_id.usage != "internal" for line in lines):
                raise UserError(_("La devolución recibida debe volver a una ubicación interna."))
            return 0, quantity
        raise UserError(_("La operación vinculada no es una devolución al proveedor ni su recepción inversa."))

    def _check_dispatch_validation(self, pickings):
        self._lock_dispatch_records()
        for record in self:
            if record.internal_picking_id.state != "done":
                raise UserError(_("La pieza no tiene un traslado realizado a devoluciones."))
            moves = pickings.move_ids.filtered(lambda move: move.wex_vendor_return_id == record and move.state not in ("done", "cancel") and move.picked)
            outgoing = incoming = 0
            for move in moves:
                shipped, received = record._get_dispatch_move_quantities(move)
                outgoing += shipped
                incoming += received
            returned, prepared = record._get_dispatch_totals()
            rounding = record.product_uom_id.rounding
            limit = record.quantity - record.recovered_quantity - record.scrapped_quantity
            if float_compare(returned + outgoing - incoming, limit, precision_rounding=rounding) > 0 or float_compare(incoming, returned, precision_rounding=rounding) > 0:
                raise UserError(_("La cantidad supera las unidades pendientes de devolver o de recibir de vuelta."))


class StockReturnPicking(models.TransientModel):
    _inherit = "stock.return.picking"

    wex_staging_location_id = fields.Many2one("stock.location", check_company=True)
    wex_return_trace_ids = fields.Many2many("wex.purchase.return")

    def _prepare_picking_default_values(self):
        values = super()._prepare_picking_default_values()
        if self.wex_staging_location_id:
            records = self.wex_return_trace_ids
            records._check_dispatch_access()
            if not records or any(
                record.receipt_picking_id != self.picking_id
                or record.staging_location_id != self.wex_staging_location_id
                or record.company_id != self.company_id
                for record in records
            ):
                raise UserError(_("La selección no corresponde a la recepción o ubicación de devoluciones."))
            values["location_id"] = self.wex_staging_location_id.id
        return values

    def _create_exchange(self, return_picking):
        exchange = super()._create_exchange(return_picking)
        exchange.move_ids.write({"wex_vendor_return_id": False})
        return exchange


class StockReturnPickingLine(models.TransientModel):
    _inherit = "stock.return.picking.line"

    wex_return_trace_id = fields.Many2one("wex.purchase.return")

    def _prepare_move_default_values(self, new_picking):
        values = super()._prepare_move_default_values(new_picking)
        record = self.wex_return_trace_id or self.move_id.wex_vendor_return_id
        if record:
            values["wex_vendor_return_id"] = record.id
        return values


class StockMove(models.Model):
    _inherit = "stock.move"

    wex_vendor_return_id = fields.Many2one("wex.purchase.return", string="Pieza apartada", index=True, copy=True, ondelete="restrict", check_company=True)

    def _prepare_merge_moves_distinct_fields(self):
        return super()._prepare_merge_moves_distinct_fields() + ["wex_vendor_return_id"]

    @api.depends("wex_return_ids.quantity", "wex_return_ids.state", "wex_return_ids.return_picking_id.state", "wex_return_ids.returned_quantity", "wex_return_ids.prepared_quantity")
    def _compute_wex_return_committed_qty(self):
        return super()._compute_wex_return_committed_qty()


class WexPurchaseListLine(models.Model):
    _inherit = "wex_purchase_list.line"

    def _get_native_return_quantity(self, receipt):
        # Contabilizar también las devoluciones de devolución y sus descendientes.
        seen = set()
        pending = receipt.returned_move_ids
        quantity = 0
        while pending:
            current = pending.filtered(lambda move: move.id not in seen)
            if not current:
                break
            seen.update(current.ids)
            for move in current.filtered(lambda item: item.state != "cancel"):
                if move.location_dest_id.usage == "supplier":
                    value = move.quantity if move.state == "done" else move.product_uom_qty
                    quantity += move.product_uom._compute_quantity(value, self.product_id.uom_id)
                elif move.location_id.usage == "supplier" and move.state == "done":
                    quantity -= move.product_uom._compute_quantity(move.quantity, self.product_id.uom_id)
            pending = current.returned_move_ids
        return max(0, quantity)


class StockPicking(models.Model):
    _inherit = "stock.picking"

    wex_vendor_return_ids = fields.Many2many("wex.purchase.return", compute="_compute_wex_vendor_returns")

    @api.depends("move_ids.wex_vendor_return_id")
    def _compute_wex_vendor_returns(self):
        for picking in self:
            picking.wex_vendor_return_ids = picking.move_ids.wex_vendor_return_id

    def _action_done(self):
        self.check_access("write")
        # Solo lectura elevada para proteger la integridad incluso si valida un
        # operario de Inventario sin acceso a la aplicación de lista de compra.
        records = self.move_ids.wex_vendor_return_id.sudo()
        if records:
            records._check_dispatch_validation(self)
        return super()._action_done()
