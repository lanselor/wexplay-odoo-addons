from odoo import _, fields, models
from odoo.exceptions import UserError


class RepairOrder(models.Model):
    _inherit = "repair.order"

    purchase_list_line_count = fields.Integer(
        string="Líneas de compra",
        compute="_compute_purchase_list_line_count",
    )

    def _compute_purchase_list_line_count(self):
        line_model = self.env["wex_purchase_list.line"]
        for rec in self:
            rec.purchase_list_line_count = line_model.search_count([("repair_id", "=", rec.id)])

    def action_view_purchase_list_lines(self):
        self.ensure_one()
        action = self.env.ref("wex_purchase_list.action_wex_purchase_list_line").read()[0]
        action["domain"] = [("repair_id", "=", self.id)]
        action["context"] = {"default_repair_id": self.id}
        return action


class RepairOrderLine(models.Model):
   # _inherit = "repair.order.line"

    purchase_list_line_id = fields.Many2one(
        "wex_purchase_list.line",
        string="Línea lista de compra",
        readonly=True,
        copy=False,
        index=True,
        help="Si se creó una línea de lista de compra desde esta pieza, queda vinculada aquí.",
    )

    def action_add_to_purchase_list(self):
        self.ensure_one()

        missing = []
        product = getattr(self, "product_id", False)
        qty = getattr(self, "product_uom_qty", False) or getattr(self, "quantity", False) or 0.0

        if not product:
            missing.append(_("Producto"))
        if not qty or qty <= 0:
            missing.append(_("Cantidad"))

        # Evitar duplicados desde la misma línea
        if self.purchase_list_line_id:
            raise UserError(_("Esta línea ya tiene una solicitud en la lista de compra."))

        seller = False
        if product:
            sellers = product.seller_ids
            if not sellers:
                missing.append(_("Proveedor en el producto (pestaña Compras / Proveedores)"))
            else:
                seller = sellers[0]

        if missing:
            raise UserError(_(
                "No se puede añadir a la lista de la compra.\n"
                "Faltan datos: %s"
            ) % (", ".join(missing)))

        vendor = seller.partner_id
        if not vendor or vendor.supplier_rank <= 0:
            raise UserError(_(
                "No se puede añadir a la lista de la compra.\n"
                "El proveedor del producto no está marcado como proveedor válido."
            ))

        repair = self.order_id if hasattr(self, "order_id") else self.repair_id
        if not repair:
            raise UserError(_("No se ha podido determinar la reparación asociada."))

        vals = {
            "company_id": repair.company_id.id if repair.company_id else self.env.company.id,
            "requested_by": self.env.user.id,
            "product_id": product.id,
            "quantity": qty,
            "vendor_id": vendor.id,
            "state": "to_purchase",
            "repair_id": repair.id,
            "repair_part_line_id": self.id,
        }

        line = self.env["wex_purchase_list.line"].create(vals)
        self.purchase_list_line_id = line.id

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("OK"),
                "message": _("Producto añadido a la lista de la compra correctamente."),
                "type": "success",
                "sticky": False,
            }
        }
