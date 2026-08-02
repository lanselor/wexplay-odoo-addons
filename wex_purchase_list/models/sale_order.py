from odoo import _, api, fields, models
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    wex_purchase_list_is_reservation = fields.Boolean(
        string="Marcar como reserva",
        default=True,
        help="Las líneas añadidas a la lista de compra desde esta venta requerirán aviso al cliente.",
    )
    wex_is_repair_quotation = fields.Boolean(
        compute="_compute_wex_is_repair_quotation",
        compute_sudo=True,
    )
    purchase_list_line_count = fields.Integer(
        string="Líneas de compra",
        compute="_compute_purchase_list_line_count",
    )

    def _compute_purchase_list_line_count(self):
        Line = self.env["wex_purchase_list.line"]
        for order in self:
            order.purchase_list_line_count = Line.search_count([
                ("sale_line_id.order_id", "=", order.id),
            ])

    @api.depends()
    def _compute_wex_is_repair_quotation(self):
        repair_sale_order_ids = set(self._get_repair_quotation_orders().ids)
        for order in self:
            order.wex_is_repair_quotation = order.id in repair_sale_order_ids

    def _get_repair_quotation_orders(self):
        if not self.ids:
            return self.env["sale.order"]
        repairs = self.env["repair.order"].search([("sale_order_id", "in", self.ids)])
        return repairs.mapped("sale_order_id")

    def _check_can_change_purchase_list_reservation(self):
        repair_quotation_ids = set(self._get_repair_quotation_orders().ids)
        repair_quotations = self.filtered(lambda order: order.id in repair_quotation_ids)
        if repair_quotations:
            raise UserError(_("Las cotizaciones SAT gestionan las reservas desde las piezas de reparación."))
        confirmed_orders = self.filtered(lambda order: order.state not in ("draft", "sent"))
        if confirmed_orders:
            raise UserError(_("Solo puedes cambiar la reserva mientras la cotización está en borrador o enviada."))

    def _get_syncable_purchase_list_lines(self):
        return self.env["wex_purchase_list.line"].search([
            ("sale_line_id.order_id", "in", self.ids),
            ("state", "!=", "cancelled"),
            ("customer_notified", "=", False),
        ])

    def _sync_purchase_list_reservation_policy(self):
        for order in self:
            order._get_syncable_purchase_list_lines().write({
                "is_reservation": order.wex_purchase_list_is_reservation,
            })

    def write(self, vals):
        orders_to_sync = self.env["sale.order"]
        if "wex_purchase_list_is_reservation" in vals:
            orders_to_sync = self.filtered(
                lambda order: order.wex_purchase_list_is_reservation != vals["wex_purchase_list_is_reservation"]
            )
            if orders_to_sync:
                orders_to_sync._check_can_change_purchase_list_reservation()
        result = super().write(vals)
        if orders_to_sync:
            orders_to_sync._sync_purchase_list_reservation_policy()
        return result

    def action_view_purchase_list_lines(self):
        self.ensure_one()
        action = self.env.ref("wex_purchase_list.action_wex_purchase_list_line").read()[0]
        action["domain"] = [("sale_line_id.order_id", "=", self.id)]
        return action


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    # Campo estable para attrs en tree (store=True)
    # Valores: 'product', 'consu', 'service'
    wex_product_type = fields.Selection(
        related="product_id.type",
        store=True,
        readonly=True,
    )

    purchase_list_line_id = fields.Many2one(
        "wex_purchase_list.line",
        string="Línea lista de compra",
        readonly=True,
        copy=False,
        index=True,
    )

    def action_add_to_purchase_list(self):
        self.ensure_one()

        result = self.env["wex_purchase_list.line"].add_from_origin(
            origin_model="sale.order.line",
            origin_id=self.id,
            product_id=self.product_id.id,
            qty=self.product_uom_qty or 0.0,
            state="to_purchase",
        )

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("OK"),
                "message": result.get("message") or _("Operación completada."),
                "type": "success",
                "sticky": False,
            }
        }

