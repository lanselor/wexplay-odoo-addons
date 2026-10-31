import math

from odoo import _, api, Command, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_compare, float_is_zero, float_round


class WexPurchaseReturn(models.Model):
    _inherit = "wex.purchase.return"

    resolution_ids = fields.One2many("wex.return.resolution", "return_id", string="Resoluciones excepcionales")
    recovery_move_ids = fields.One2many("stock.move", "wex_recovered_return_id")
    recovered_quantity = fields.Float(compute="_compute_resolution_quantities", store=True, digits="Product Unit of Measure", string="Recuperadas para uso")
    scrapped_quantity = fields.Float(compute="_compute_resolution_quantities", store=True, digits="Product Unit of Measure", string="Desechadas")
    resolution_revision = fields.Integer(default=0, copy=False)
    state = fields.Selection(selection_add=[("resolved", "Resuelta sin envío"), ("closed", "Completada")])

    @api.depends("recovery_move_ids.state", "recovery_move_ids.quantity", "recovery_move_ids.product_uom", "recovery_move_ids.location_id", "recovery_move_ids.location_dest_id", "resolution_ids.scrap_ids.state", "resolution_ids.scrap_ids.scrap_qty", "resolution_ids.scrap_ids.product_uom_id")
    def _compute_resolution_quantities(self):
        for record in self:
            recovered = 0
            for move in record.recovery_move_ids.filtered(lambda item: item.state == "done"):
                quantity = move.product_uom._compute_quantity(move.quantity, record.product_uom_id)
                recovered += -quantity if move.location_dest_id == record.staging_location_id else quantity
            record.recovered_quantity = max(0, recovered)
            record.scrapped_quantity = sum(
                scrap.product_uom_id._compute_quantity(scrap.scrap_qty, record.product_uom_id)
                for scrap in record.resolution_ids.scrap_ids.filtered(lambda item: item.state == "done")
            )

    @api.depends("internal_picking_id.state", "return_picking_id.state", "returned_quantity", "prepared_quantity", "dispatch_move_ids.state", "recovered_quantity", "scrapped_quantity", "remaining_quantity")
    def _compute_state(self):
        super()._compute_state()
        for record in self:
            resolved = record.recovered_quantity + record.scrapped_quantity
            if float_is_zero(resolved, precision_rounding=record.product_uom_id.rounding):
                continue
            if float_is_zero(record.remaining_quantity, precision_rounding=record.product_uom_id.rounding):
                record.state = "closed" if record.returned_quantity else "resolved"
            else:
                record.state = "partial"

    def _get_source_committed_quantity(self):
        return max(0, super()._get_source_committed_quantity() - self.recovered_quantity)

    def _get_receipt_committed_quantity(self):
        return max(0, super()._get_receipt_committed_quantity() - self.recovered_quantity)

    def _check_resolution_quantity(self, quantity, include_prepared=True):
        self.ensure_one()
        rounding = self.product_uom_id.rounding
        if not math.isfinite(quantity) or float_compare(quantity, 0, precision_rounding=rounding) <= 0 or abs(quantity - float_round(quantity, precision_rounding=rounding)) > 0.000001:
            raise UserError(_("Indica una cantidad positiva compatible con la unidad del producto."))
        if self.product_id.tracking == "serial" and quantity != 1:
            raise UserError(_("Gestiona un número de serie por operación."))
        if self.internal_picking_id.state != "done":
            raise UserError(_("La pieza debe tener realizado el traslado a devoluciones."))
        available = self.remaining_quantity - (self.prepared_quantity if include_prepared else 0)
        if float_compare(quantity, available, precision_rounding=rounding) > 0:
            raise UserError(_("La cantidad supera las unidades pendientes y libres de envío. Revisa los documentos preparados o registra primero el regreso de las piezas ya enviadas."))

    def action_open_resolution(self):
        self.ensure_one()
        self._check_dispatch_access()
        self._check_resolution_quantity(self.remaining_quantity, include_prepared=False)
        wizard = self.env["wex.return.resolve"].create({"return_id": self.id, "quantity": max(0, self.remaining_quantity - self.prepared_quantity)})
        return {"type": "ir.actions.act_window", "name": _("Resolver sin enviar"), "res_model": wizard._name,
                "res_id": wizard.id, "view_mode": "form", "target": "new"}

    def _check_recovery_move_identity(self, move):
        self.ensure_one()
        resolution = move.wex_return_resolution_id.sudo()
        if not resolution or resolution.return_id != self or resolution.disposition != "recover" or move.product_id != self.product_id or move.company_id != self.company_id:
            raise UserError(_("El traslado no corresponde a la resolución de la pieza apartada."))
        original = resolution.picking_id.move_ids
        ancestor = move.origin_returned_move_id
        seen = set()
        while ancestor and ancestor.id not in seen and ancestor not in original:
            seen.add(ancestor.id)
            ancestor = ancestor.origin_returned_move_id
        if move not in original and ancestor not in original:
            raise UserError(_("El traslado no procede de la recuperación original."))
        if any(line.lot_id != self.lot_id or line.owner_id for line in move.move_line_ids.filtered("picked")):
            raise UserError(_("El lote o propietario no corresponde a la pieza apartada."))
        return resolution

    def _get_recovery_move_quantities(self, move):
        resolution = self._check_recovery_move_identity(move)
        lines = move.move_line_ids.filtered("picked")
        if any(line.location_id != move.location_id or line.location_dest_id != move.location_dest_id for line in lines):
            raise UserError(_("Las ubicaciones de las líneas no corresponden a la resolución."))
        self._check_dispatch_stock(lines)
        quantity = sum(line.product_uom_id._compute_quantity(line.quantity, self.product_uom_id) for line in lines)
        if move.location_id == self.staging_location_id and move.location_dest_id == resolution.destination_location_id:
            return resolution, quantity, 0
        if move.location_dest_id == self.staging_location_id and move.location_id == resolution.destination_location_id:
            return resolution, 0, quantity
        raise UserError(_("El traslado debe conservar las ubicaciones de la recuperación o su devolución nativa."))

    def _check_recovery_validation(self, moves):
        self._lock_dispatch_records()
        for trace in self:
            outgoing = incoming = 0
            changes = {}
            for move in moves.filtered(lambda item: item.wex_recovered_return_id.id == trace.id):
                resolution, recovered, restored = trace._get_recovery_move_quantities(move)
                outgoing += recovered
                incoming += restored
                changes[resolution] = changes.get(resolution, 0) + recovered - restored
            if outgoing:
                trace._check_resolution_quantity(outgoing)
            for resolution, change in changes.items():
                done = trace.recovery_move_ids.filtered(lambda move: move.state == "done" and move.wex_return_resolution_id == resolution)
                net = sum(move.product_uom._compute_quantity(move.quantity, trace.product_uom_id) * (-1 if move.location_dest_id == trace.staging_location_id else 1) for move in done)
                if float_compare(net + change, 0, precision_rounding=trace.product_uom_id.rounding) < 0 or float_compare(net + change, resolution.quantity, precision_rounding=trace.product_uom_id.rounding) > 0:
                    raise UserError(_("La cantidad supera las unidades de esta resolución."))
            if float_compare(incoming, trace.recovered_quantity, precision_rounding=trace.product_uom_id.rounding) > 0:
                raise UserError(_("No se pueden reintegrar a devoluciones más unidades de las recuperadas."))
            if incoming > outgoing:
                trace.purchase_list_line_id._check_return_capacity(trace.receipt_move_id, incoming - outgoing)
            trace.resolution_revision += 1


class WexReturnResolution(models.Model):
    _name = "wex.return.resolution"
    _description = "Exceptional Vendor Return Resolution"
    _order = "id desc"
    _check_company_auto = True
    _rec_name = "return_id"

    return_id = fields.Many2one("wex.purchase.return", string="Devolución", required=True, ondelete="restrict", check_company=True, index=True)
    company_id = fields.Many2one(related="return_id.company_id", store=True)
    product_id = fields.Many2one(related="return_id.product_id")
    quantity = fields.Float(string="Cantidad", required=True, digits="Product Unit of Measure")
    disposition = fields.Selection([("recover", "Recuperar para uso"), ("hold", "Conservar para revisión"), ("scrap", "Desechar")], required=True, string="Decisión")
    explanation = fields.Text(required=True, string="Explicación")
    destination_location_id = fields.Many2one("stock.location", check_company=True, string="Destino")
    package_id = fields.Many2one("stock.quant.package", check_company=True)
    picking_id = fields.Many2one("stock.picking", string="Traslado de recuperación", readonly=True, check_company=True, ondelete="restrict")
    scrap_ids = fields.One2many("stock.scrap", "wex_return_resolution_id", string="Desecho")
    state = fields.Selection([("draft", "Pendiente"), ("done", "Realizada"), ("cancelled", "Cancelada / sin documento")], compute="_compute_state", store=True, string="Estado")

    @api.depends("disposition", "picking_id.state", "scrap_ids.state")
    def _compute_state(self):
        for record in self:
            if record.disposition == "hold" or record.picking_id.state == "done" or "done" in record.scrap_ids.mapped("state"):
                record.state = "done"
            elif record.picking_id.state == "cancel" or (record.disposition == "scrap" and not record.scrap_ids):
                record.state = "cancelled"
            else:
                record.state = "draft"

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self.env["wex.purchase.return"].browse(vals.get("return_id"))._check_dispatch_access()
        return super().create(vals_list)

    @api.constrains("quantity", "explanation", "return_id", "destination_location_id", "disposition")
    def _check_resolution_values(self):
        for record in self:
            if not (record.explanation or "").strip() or not math.isfinite(record.quantity) or record.quantity <= 0:
                raise ValidationError(_("Indica una cantidad positiva y explica la decisión."))
            if record.disposition != "recover":
                continue
            destination = record.destination_location_id
            stage = record.return_id.staging_location_id
            if not stage or not destination or not destination.active or destination.usage != "internal" or destination.scrap_location or destination.company_id != record.company_id or destination.parent_path.startswith(stage.parent_path):
                raise ValidationError(_("Selecciona un destino interno activo de la compañía, fuera de la zona de devoluciones."))

    def write(self, vals):
        if set(vals) - {"picking_id"}:
            raise UserError(_("Las resoluciones forman parte del historial y no se pueden modificar."))
        if "picking_id" in vals and any(record.picking_id for record in self):
            raise UserError(_("No se puede reemplazar el traslado de una resolución."))
        return super().write(vals)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_history(self):
        raise UserError(_("No se puede eliminar el historial de resolución de una devolución."))

    def _open_document(self):
        self.ensure_one()
        document = self.picking_id or self.scrap_ids or self
        document.check_access("read")
        return {"type": "ir.actions.act_window", "name": _("Resolución de devolución"), "res_model": document._name,
                "res_id": document.id, "view_mode": "form", "target": "current"}

    def _create_recovery_transfer(self):
        self.ensure_one()
        trace = self.return_id
        source = trace.staging_location_id
        product = trace.product_id
        picking = self.env["stock.picking"].create({
            "company_id": trace.company_id.id,
            "picking_type_id": trace.purchase_list_line_id._get_staging_picking_type(trace.receipt_move_id, source).id,
            "location_id": source.id, "location_dest_id": self.destination_location_id.id,
            "origin": _("Recuperar devolución: %s", trace.display_name),
            "move_ids": [Command.create({
                "name": product.display_name, "product_id": product.id,
                "product_uom_qty": self.quantity, "product_uom": product.uom_id.id,
                "company_id": trace.company_id.id, "location_id": source.id,
                "location_dest_id": self.destination_location_id.id,
                "wex_recovered_return_id": trace.id, "wex_return_resolution_id": self.id,
            })],
        })
        self.picking_id = picking
        picking.action_confirm()
        move = picking.move_ids
        move._do_unreserve()
        taken = move._update_reserved_quantity(self.quantity, source, lot_id=trace.lot_id, package_id=self.package_id, strict=True)
        if float_compare(taken, self.quantity, precision_rounding=product.uom_id.rounding) != 0:
            raise UserError(_("No hay suficientes unidades libres de la pieza, lote y paquete. No se liberan reservas de otras operaciones."))
        if any(line.lot_id != trace.lot_id or line.owner_id for line in move.move_line_ids):
            raise UserError(_("Las existencias reservadas no corresponden a la pieza apartada."))
        move._recompute_state()
        move.picked = True
        picking.button_validate()
        if picking.state != "done":
            raise UserError(_("El traslado requiere una revisión adicional de Inventario. No se ha recuperado la pieza."))
        picking.message_post(body=self.explanation)
        return picking

    def _create_scrap_document(self):
        self.ensure_one()
        trace = self.return_id
        scrap = self.env["stock.scrap"].create({
            "company_id": trace.company_id.id, "product_id": trace.product_id.id,
            "product_uom_id": trace.product_uom_id.id, "scrap_qty": self.quantity,
            "location_id": trace.staging_location_id.id, "lot_id": trace.lot_id.id,
            "package_id": self.package_id.id, "origin": trace.internal_picking_id.name,
            "wex_return_resolution_id": self.id,
        })
        scrap.message_post(body=self.explanation)
        return scrap


class StockMove(models.Model):
    _inherit = "stock.move"

    wex_recovered_return_id = fields.Many2one("wex.purchase.return", copy=True, check_company=True, ondelete="restrict", index=True)
    wex_return_resolution_id = fields.Many2one("wex.return.resolution", copy=True, check_company=True, ondelete="restrict")
    wex_replacement_return_id = fields.Many2one("wex.purchase.return", copy=False, check_company=True, ondelete="restrict")

    def _prepare_merge_moves_distinct_fields(self):
        return super()._prepare_merge_moves_distinct_fields() + ["wex_recovered_return_id", "wex_return_resolution_id", "wex_replacement_return_id"]

    @api.depends("wex_return_ids.quantity", "wex_return_ids.state", "wex_return_ids.return_picking_id.state", "wex_return_ids.returned_quantity", "wex_return_ids.prepared_quantity", "wex_return_ids.recovered_quantity")
    def _compute_wex_return_committed_qty(self):
        return super()._compute_wex_return_committed_qty()


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def _action_done(self):
        self.check_access("write")
        moves = self.move_ids.filtered(lambda move: move.wex_recovered_return_id and move.state not in ("done", "cancel") and move.picked)
        traces = moves.wex_recovered_return_id.sudo()
        if traces:
            traces._check_recovery_validation(moves)
        return super()._action_done()


class StockReturnPickingLine(models.TransientModel):
    _inherit = "stock.return.picking.line"

    def _prepare_move_default_values(self, new_picking):
        values = super()._prepare_move_default_values(new_picking)
        if self.move_id.wex_recovered_return_id:
            values.update({"wex_recovered_return_id": self.move_id.wex_recovered_return_id.id,
                           "wex_return_resolution_id": self.move_id.wex_return_resolution_id.id})
        return values


class StockScrap(models.Model):
    _inherit = "stock.scrap"

    wex_return_resolution_id = fields.Many2one("wex.return.resolution", check_company=True, copy=False, ondelete="restrict", readonly=True)
    _sql_constraints = [("wex_resolution_unique", "unique(wex_return_resolution_id)", "La resolución ya tiene un documento de desecho.")]

    def write(self, vals):
        if "wex_return_resolution_id" in vals and any(record.wex_return_resolution_id for record in self):
            raise UserError(_("No se puede cambiar el vínculo de un desecho con su devolución."))
        return super().write(vals)

    def _check_wex_resolution(self):
        self.ensure_one()
        if self.state == "done":
            raise UserError(_("El desecho ya está realizado."))
        # Lectura de la traza y actualización exclusiva de su contador de concurrencia.
        resolution = self.wex_return_resolution_id.sudo()
        trace = resolution.return_id
        trace._lock_dispatch_records()
        quantity = self.product_uom_id._compute_quantity(self.scrap_qty, trace.product_uom_id)
        if resolution.disposition != "scrap" or self.product_id != trace.product_id or self.company_id != trace.company_id or self.location_id != trace.staging_location_id or self.lot_id != trace.lot_id or self.owner_id or self.should_replenish or self.package_id != resolution.package_id:
            raise UserError(_("El desecho debe conservar producto, compañía, origen, lote y paquete de la resolución, sin reaprovisionamiento automático."))
        if not self.scrap_location_id.scrap_location or not self.scrap_location_id.active:
            raise UserError(_("Selecciona una ubicación de desecho activa."))
        trace._check_resolution_quantity(quantity)
        available = self.env["stock.quant"]._get_available_quantity(self.product_id, self.location_id, lot_id=self.lot_id, package_id=self.package_id, strict=True)
        if float_compare(available, quantity, precision_rounding=trace.product_uom_id.rounding) < 0:
            raise UserError(_("No hay unidades libres suficientes para desechar. Revisa las reservas existentes."))
        if float_compare(quantity, resolution.quantity, precision_rounding=trace.product_uom_id.rounding) != 0:
            raise UserError(_("La cantidad de desecho debe coincidir con la resolución. Prepara otra resolución para una cantidad distinta."))
        return trace

    def action_validate(self):
        self.check_access("write")
        for scrap in self.filtered("wex_return_resolution_id"):
            scrap._check_wex_resolution()
        return super().action_validate()

    def do_scrap(self):
        self.check_access("write")
        with self.env.cr.savepoint():
            for scrap in self:
                if scrap.wex_return_resolution_id:
                    trace = scrap._check_wex_resolution()
                    trace.resolution_revision += 1
                # Validar y realizar cada documento antes de comprobar el siguiente.
                # Así dos borradores de la misma traza no consumen la misma capacidad.
                super(StockScrap, scrap).do_scrap()
            return True


class WexPurchaseListLine(models.Model):
    _inherit = "wex_purchase_list.line"

    @api.depends("return_ids.quantity", "return_ids.state", "return_ids.recovered_quantity")
    def _compute_wex_return_quantity(self):
        return super()._compute_wex_return_quantity()
