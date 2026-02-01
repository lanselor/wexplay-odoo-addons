from odoo import _, fields, models
from odoo.exceptions import UserError


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    purchase_list_line_id = fields.Many2one(
        "wex_purchase_list.line",
        string="Línea lista de compra",
        readonly=True,
        copy=False,
        index=True,
    )

    def action_add_to_purchase_list(self):
        self.ensure_one()

        if self.purchase_list_line_id:
            raise UserError(_("Esta línea ya está en la lista de compra."))

        product = self.product_id
        qty = self.product_uom_qty or 0.0

        if not product or product.type != "product":
            raise UserError(_("Solo se pueden añadir productos almacenables."))

        if qty <= 0:
            raise UserError(_("La cantidad debe ser mayor que cero."))

        sellers = product.seller_ids
        if not sellers:
            raise UserError(_(
                "El producto no tiene proveedores configurados."
            ))

        seller = sellers[0]
        vendor = seller.partner_id

        if not vendor or vendor.supplier_rank <= 0:
            raise UserError(_("El proveedor no es válido."))

        order = self.order_id

        vals = {
            "company_id": order.company_id.id,
            "requested_by": self.env.user.id,
            "product_id": product.id,
            "quantity": qty,
            "vendor_id": vendor.id,
            "state": "to_purchase",
            "sale_line_id": self.id,
        }

        line = self.env["wex_purchase_list.line"].create(vals)
        self.purchase_list_line_id = line.id

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("OK"),
                "message": _("Producto añadido a la lista de compra."),
                "type": "success",
                "sticky": False,
            }
        }
