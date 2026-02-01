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
            rec.purchase_list_line_count = line_model.search_count([
                ("repair_id", "=", rec.id)
            ])

    def action_view_purchase_list_lines(self):
        self.ensure_one()
        action = self.env.ref(
            "wex_purchase_list.action_wex_purchase_list_line"
        ).read()[0]
        action["domain"] = [("repair_id", "=", self.id)]
        action["context"] = {"default_repair_id": self.id}
        return action


class StockMove(models.Model):
    _inherit = "stock.move"

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

        product = self.product_id
        qty = self.product_uom_qty or 0.0

        missing = []
        if not product:
            missing.append(_("Producto"))
        if not qty or qty <= 0:
            missing.append(_("Cantidad"))

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

        repair = self.repair_id
        if not repair:
            raise UserError(_("No se ha podido determinar la reparación asociada."))

        PurchaseLine = self.env["wex_purchase_list.line"]

        # 🔹 FASE 2.1 — buscar línea existente activa
        existing_line = PurchaseLine.search([
            ("repair_id", "=", repair.id),
            ("product_id", "=", product.id),
            ("state", "not in", ("cancelled", "received")),
        ], limit=1)

        if existing_line:
            existing_line.quantity += qty
            self.purchase_list_line_id = existing_line.id

            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("OK"),
                    "message": _(
                        "La cantidad se ha sumado a una línea existente de la lista de compra."
                    ),
                    "type": "success",
                    "sticky": False,
                }
            }

        # 🔹 comportamiento actual (crear línea nueva)
        vals = {
            "company_id": repair.company_id.id if repair.company_id else self.env.company.id,
            "requested_by": self.env.user.id,
            "product_id": product.id,
            "quantity": qty,
            "vendor_id": vendor.id,
            "state": "to_purchase",
            "repair_id": repair.id,
            "repair_part_move_id": self.id,
        }

        line = PurchaseLine.create(vals)
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
