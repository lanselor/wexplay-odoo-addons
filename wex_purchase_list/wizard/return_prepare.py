import math

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.misc import formatLang
from odoo.tools.float_utils import float_compare, float_round


class WexReturnPrepare(models.TransientModel):
    _name = "wex.return.prepare"
    _description = "Prepare Vendor Return"
    _check_company_auto = True

    purchase_list_line_id = fields.Many2one("wex_purchase_list.line", required=True, readonly=True, check_company=True)
    company_id = fields.Many2one(related="purchase_list_line_id.company_id")
    product_id = fields.Many2one(related="purchase_list_line_id.product_id")
    vendor_id = fields.Many2one(related="purchase_list_line_id.vendor_id")
    purchase_order_id = fields.Many2one(related="purchase_list_line_id.purchase_order_id")
    product_uom_id = fields.Many2one(related="product_id.uom_id")
    receipt_move_ids = fields.Many2many("stock.move", compute="_compute_choices")
    receipt_picking_ids = fields.Many2many("stock.picking", compute="_compute_choices")
    repair_move_ids = fields.Many2many("stock.move", compute="_compute_choices")
    has_multiple_receipt_moves = fields.Boolean(compute="_compute_choices")
    has_multiple_repair_moves = fields.Boolean(compute="_compute_choices")
    receipt_picking_id = fields.Many2one("stock.picking", string="Recepción", check_company=True)
    receipt_move_id = fields.Many2one(
        "stock.move", string="Movimiento del producto", check_company=True,
        compute="_compute_receipt_move", store=True, readonly=False,
    )
    received_quantity = fields.Float(compute="_compute_received_quantity", string="Unidades recibidas", digits="Product Unit of Measure")
    receipt_date = fields.Datetime(related="receipt_move_id.picking_id.date_done", string="Fecha de recepción")
    repair_move_id = fields.Many2one("stock.move", string="Pieza del SAT", check_company=True)
    source_location_id = fields.Many2one(
        "stock.location", string="Ubicación física de origen", check_company=True,
        compute="_compute_source_location", store=True, readonly=False,
    )
    destination_location_id = fields.Many2one(related="company_id.wex_return_location_id")
    lot_id = fields.Many2one("stock.lot", string="Lote / número de serie", check_company=True)
    package_id = fields.Many2one("stock.quant.package", string="Paquete de origen", check_company=True)
    tracking = fields.Selection(related="product_id.tracking")
    quantity = fields.Float(string="Cantidad a apartar", digits="Product Unit of Measure")
    rma_reference = fields.Char(string="Referencia RMA")
    return_id = fields.Many2one("wex.purchase.return", readonly=True, copy=False, check_company=True)
    confirm_origin_change = fields.Boolean(string="Confirmo retirar o reducir esta cantidad del SAT o la venta")
    origin_description = fields.Text(compute="_compute_origin_information", string="Documento de origen")
    blocking_reason = fields.Text(compute="_compute_origin_information", string="Revisión necesaria")
    has_origin_document = fields.Boolean(compute="_compute_origin_information")
    requires_origin_change = fields.Boolean(compute="_compute_origin_information")
    origin_is_repair = fields.Boolean(compute="_compute_origin_information")
    origin_change_summary = fields.Char(compute="_compute_origin_information")
    return_reason = fields.Selection(
        selection=lambda self: self.env["wex.purchase.return"]._fields["return_reason"]._description_selection(self.env),
        string="Motivo de devolución",
    )
    return_notes = fields.Text(string="Observaciones")
    request_replacement = fields.Boolean(string="Añadir nuevamente el repuesto al SAT y solicitarlo")
    replacement_quantity = fields.Float(string="Cantidad a solicitar", compute="_compute_replacement_quantity", store=True, readonly=False, digits="Product Unit of Measure")
    can_request_replacement = fields.Boolean(compute="_compute_can_request_replacement")

    @api.depends("quantity")
    def _compute_replacement_quantity(self):
        for wizard in self:
            wizard.replacement_quantity = wizard.quantity

    @api.depends("repair_move_id.repair_id.state", "purchase_list_line_id.repair_id.state")
    def _compute_can_request_replacement(self):
        for wizard in self:
            repair = wizard.repair_move_id.repair_id or wizard.purchase_list_line_id.repair_id
            wizard.can_request_replacement = bool(repair and repair.state not in ("done", "delivered"))

    def _check_replacement_request(self):
        self.ensure_one()
        if not self.request_replacement:
            return
        repair = self.repair_move_id.repair_id or self.purchase_list_line_id.repair_id
        if not repair:
            raise UserError(_("La nueva solicitud requiere una reparación de origen."))
        repair.check_access("write")
        self.env.cr.execute("SELECT id FROM repair_order WHERE id = %s FOR UPDATE", [repair.id])
        repair.invalidate_recordset()
        if repair.state in ("done", "delivered"):
            raise UserError(_("No se puede solicitar otra pieza para un SAT finalizado o entregado."))
        rounding = self.product_id.uom_id.rounding
        quantity = self.replacement_quantity
        if not math.isfinite(quantity) or float_compare(quantity, 0, precision_rounding=rounding) <= 0 or abs(quantity - float_round(quantity, precision_rounding=rounding)) > 0.000001:
            raise UserError(_("Indica una cantidad válida para solicitar otra pieza."))

    def _create_replacement_request(self, trace, reservation):
        self.ensure_one()
        move = self.env["stock.move"].create({
            "repair_id": trace.repair_id.id, "repair_line_type": "add",
            "product_id": trace.product_id.id, "product_uom": trace.product_uom_id.id,
            "product_uom_qty": self.replacement_quantity, "company_id": trace.company_id.id,
            "wex_is_reservation": reservation,
            "wex_replacement_return_id": trace.id,
        })
        result = self.env["wex_purchase_list.line"]._add_from_stock_move(
            move, product=move.product_id, qty=self.replacement_quantity,
            vendor=trace.vendor_id, vendor_url=trace.purchase_list_line_id.vendor_url, state="to_purchase",
            force_new_line=True,
        )
        trace.write({"replacement_move_id": move.id, "replacement_purchase_line_id": result["line"].id})

    @api.depends("purchase_list_line_id")
    def _compute_choices(self):
        for wizard in self:
            line = wizard.purchase_list_line_id
            wizard.receipt_move_ids = line._get_return_receipts() if line else False
            wizard.receipt_picking_ids = wizard.receipt_move_ids.picking_id
            wizard.repair_move_ids = line._get_return_repair_moves() if line else False
            wizard.has_multiple_receipt_moves = len(wizard.receipt_move_ids) > 1
            wizard.has_multiple_repair_moves = len(wizard.repair_move_ids) > 1

    @api.depends("receipt_picking_id", "purchase_list_line_id")
    def _compute_receipt_move(self):
        for wizard in self:
            moves = wizard.purchase_list_line_id._get_return_receipts().filtered(
                lambda move: move.picking_id == wizard.receipt_picking_id
            ) if wizard.purchase_list_line_id else self.env["stock.move"]
            wizard.receipt_move_id = moves if len(moves) == 1 else False

    @api.depends("receipt_move_id")
    def _compute_received_quantity(self):
        for wizard in self:
            move = wizard.receipt_move_id
            wizard.received_quantity = move.product_uom._compute_quantity(move.quantity, move.product_id.uom_id) if move else 0

    @api.depends("receipt_move_id")
    def _compute_source_location(self):
        for wizard in self:
            wizard.source_location_id = wizard.receipt_move_id.location_dest_id

    @api.onchange("quantity", "receipt_move_id", "repair_move_id")
    def _onchange_return_selection(self):
        self.confirm_origin_change = False

    @api.onchange("receipt_move_id")
    def _onchange_return_receipt(self):
        self.lot_id = False
        self.package_id = False

    def _get_origin_document(self):
        self.ensure_one()
        line = self.purchase_list_line_id
        return self.repair_move_id.repair_id or line.repair_id or line.sale_line_id.order_id

    @api.depends("purchase_list_line_id", "repair_move_id", "quantity")
    def _compute_origin_information(self):
        for wizard in self:
            line = wizard.purchase_list_line_id
            document = wizard._get_origin_document()
            wizard.has_origin_document = bool(document)
            wizard.origin_is_repair = bool(document and document._name == "repair.order")
            wizard.origin_change_summary = False
            parts = []
            if document:
                state_label = dict(document._fields["state"]._description_selection(self.env)).get(document.state, document.state)
                parts.append(_("Documento: %(name)s — Estado: %(state)s", name=document.display_name, state=state_label))
                parts.append(_("Cliente: %s", document.partner_id.display_name or "—"))
            origin = wizard.repair_move_id or line.sale_line_id
            sale_line = line._get_origin_sale_line(wizard.repair_move_id) if line else False
            if sale_line:
                invoices = sale_line.invoice_lines.move_id.filtered(lambda invoice: invoice.state != "cancel")
                if invoices:
                    parts.append(_("Facturación relacionada: %s", ", ".join(invoices.mapped("display_name"))))
            wizard.origin_description = "\n".join(parts) or _("Sin asignación activa en SAT o venta. Se comprobará el stock disponible.")
            wizard.blocking_reason = False
            wizard.requires_origin_change = False
            if not line:
                continue
            try:
                new_quantity = line._check_origin_for_return(wizard.repair_move_id, wizard.quantity)
                wizard.requires_origin_change = new_quantity is not False
                if new_quantity is not False:
                    wizard.origin_change_summary = _(
                        "Cantidad actual: %(current)s · A retirar: %(remove)s · Quedará en el documento: %(remaining)s",
                        current=formatLang(self.env, origin.product_uom_qty, digits=2),
                        remove=formatLang(self.env, origin.product_uom_qty - new_quantity, digits=2),
                        remaining=formatLang(self.env, new_quantity, digits=2),
                    )
            except UserError as error:
                wizard.blocking_reason = str(error)

    def action_open_origin(self):
        self.ensure_one()
        document = self._get_origin_document()
        if not document:
            raise UserError(_("No hay un documento de origen disponible."))
        document.check_access("read")
        return {"type": "ir.actions.act_window", "res_model": document._name,
                "res_id": document.id, "view_mode": "form", "target": "current"}

    def action_stage(self):
        self.ensure_one()
        self.check_access("write")
        self.purchase_list_line_id._check_return_access()
        self.env.flush_all()
        self.env.cr.execute("SELECT id FROM wex_return_prepare WHERE id = %s FOR UPDATE", [self.id])
        self.invalidate_recordset()
        if not self.receipt_move_id or not self.source_location_id:
            raise UserError(_("Selecciona la recepción y la ubicación física de la pieza."))
        if self.receipt_picking_id and self.receipt_move_id.picking_id != self.receipt_picking_id:
            raise UserError(_("El movimiento no corresponde a la recepción seleccionada."))
        trace = self.return_id
        if trace and trace.purchase_list_line_id != self.purchase_list_line_id:
            raise UserError(_("La solicitud no corresponde a la devolución registrada."))
        if not trace:
            with self.env.cr.savepoint():
                self._check_replacement_request()
                reservation = self.repair_move_id.wex_is_reservation
                trace = self.purchase_list_line_id._stage_vendor_return(
                    self.receipt_move_id, self.quantity, self.source_location_id,
                    self.lot_id, self.package_id, self.repair_move_id,
                    self.confirm_origin_change, self.rma_reference,
                    self.return_reason, self.return_notes,
                )
                if self.request_replacement:
                    self._create_replacement_request(trace, reservation)
                self.return_id = trace
        return {"type": "ir.actions.act_window", "name": _("Pieza apartada: traslado realizado"),
                "res_model": "stock.picking", "res_id": trace.internal_picking_id.id,
                "view_mode": "form", "target": "current"}
