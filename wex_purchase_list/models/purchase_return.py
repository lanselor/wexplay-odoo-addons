from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_compare


class WexPurchaseReturn(models.Model):
    _name = "wex.purchase.return"
    _description = "Vendor Return Tracking"
    _order = "id desc"
    _check_company_auto = True
    _rec_name = "product_id"

    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company, index=True,
    )
    purchase_list_line_id = fields.Many2one(
        "wex_purchase_list.line", required=True, ondelete="restrict",
        check_company=True, index=True, copy=False,
    )
    product_id = fields.Many2one(related="purchase_list_line_id.product_id", store=True)
    vendor_id = fields.Many2one(related="purchase_list_line_id.vendor_id", store=True)
    repair_id = fields.Many2one("repair.order", readonly=True, copy=False, check_company=True, ondelete="restrict")
    sale_line_id = fields.Many2one(related="purchase_list_line_id.sale_line_id", store=True)
    purchase_order_id = fields.Many2one(
        related="purchase_list_line_id.purchase_order_id", store=True,
    )
    purchase_order_line_id = fields.Many2one(
        related="purchase_list_line_id.purchase_order_line_id", store=True,
    )
    receipt_move_id = fields.Many2one(
        "stock.move", required=True, ondelete="restrict", check_company=True, copy=False,
    )
    receipt_picking_id = fields.Many2one(related="receipt_move_id.picking_id", store=True)
    product_uom_id = fields.Many2one(related="product_id.uom_id")
    quantity = fields.Float(required=True, digits="Product Unit of Measure", copy=False)
    rma_reference = fields.Char(string="Referencia RMA", copy=False)
    return_reason = fields.Selection([
        ("unused", "No utilizado / ya no necesario"),
        ("defective", "Defectuoso"),
        ("wrong_reference", "Referencia incorrecta"),
        ("damaged", "Dañado al recibir"),
        ("other", "Otro"),
    ], string="Motivo de devolución", copy=False)
    return_notes = fields.Text(string="Observaciones", copy=False)
    replacement_move_id = fields.Many2one("stock.move", readonly=True, copy=False, check_company=True, ondelete="set null")
    replacement_purchase_line_id = fields.Many2one("wex_purchase_list.line", readonly=True, copy=False, check_company=True, ondelete="restrict")
    internal_picking_id = fields.Many2one(
        "stock.picking", ondelete="restrict", check_company=True, copy=False,
    )
    return_picking_id = fields.Many2one(
        "stock.picking", ondelete="restrict", check_company=True, copy=False,
    )

    @api.constrains("return_reason", "return_notes")
    def _check_return_reason(self):
        for record in self:
            if record.return_reason == "other" and not (record.return_notes or "").strip():
                raise ValidationError(_("Explica el motivo de devolución al seleccionar Otro."))

    @api.constrains("purchase_list_line_id", "receipt_move_id", "quantity", "company_id")
    def _check_receipt_and_quantity(self):
        for record in self:
            move = record.receipt_move_id
            line = record.purchase_list_line_id
            if (
                move.state != "done" or move.picking_id.state != "done"
                or move.location_id.usage != "supplier"
                or move.location_dest_id.usage != "internal"
                or move.origin_returned_move_id
            ):
                raise ValidationError(_("Selecciona una recepción de proveedor validada."))
            if (
                not line.purchase_order_line_id
                or move.product_id != line.product_id
                or move.purchase_line_id != line.purchase_order_line_id
                or line.purchase_order_id != move.purchase_line_id.order_id
                or line.vendor_id.commercial_partner_id != move.purchase_line_id.order_id.partner_id.commercial_partner_id
            ):
                raise ValidationError(_("La recepción debe corresponder al producto, proveedor y compra de la línea."))
            rounding = move.product_id.uom_id.rounding
            if float_compare(record.quantity, 0, precision_rounding=rounding) <= 0:
                raise ValidationError(_("La cantidad a devolver debe ser mayor que cero."))
            if float_compare(record.quantity, record._get_received_quantity(), precision_rounding=rounding) > 0:
                raise ValidationError(_("La cantidad no puede superar las unidades recibidas en ese movimiento."))

    def _get_received_quantity(self):
        self.ensure_one()
        move = self.receipt_move_id
        return move.product_uom._compute_quantity(move.quantity, move.product_id.uom_id)

    @api.constrains("internal_picking_id", "return_picking_id", "receipt_move_id", "purchase_list_line_id")
    def _check_transfer_links(self):
        for record in self:
            internal = record.internal_picking_id
            if internal and (
                internal.picking_type_id.code != "internal"
                or record.product_id not in internal.move_ids.product_id
            ):
                raise ValidationError(_("El traslado vinculado debe ser interno e incluir el producto."))
            returned = record.return_picking_id
            if returned and (
                returned.return_id != record.receipt_picking_id
                or returned.location_dest_id.usage != "supplier"
                or record.receipt_move_id not in returned.move_ids.origin_returned_move_id
            ):
                raise ValidationError(_("La devolución debe proceder de la recepción original y tener destino proveedor."))

    def copy(self, default=None):
        raise UserError(_("Los registros de trazabilidad de devoluciones no se pueden duplicar."))

    @api.ondelete(at_uninstall=False)
    def _unlink_except_without_transfers(self):
        if any(record.internal_picking_id or record.return_picking_id for record in self):
            raise UserError(_("No se puede eliminar la trazabilidad de una operación de inventario."))


class WexPurchaseListLine(models.Model):
    _inherit = "wex_purchase_list.line"

    @api.constrains("product_id", "vendor_id", "purchase_order_id", "purchase_order_line_id", "company_id")
    def _check_return_traceability(self):
        # Validación de integridad: no expone registros de otras compañías al editor.
        traces = self.env["wex.purchase.return"].sudo().search([
            ("purchase_list_line_id", "in", self.ids),
        ])
        traces._check_receipt_and_quantity()
        traces._check_transfer_links()
        traces._check_company()
