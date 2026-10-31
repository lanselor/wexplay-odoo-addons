from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


class ReturnWorkflowCommon(AccountTestInvoicingCommon):
    @classmethod
    def get_default_groups(cls):
        return (
            super().get_default_groups()
            | cls.env.ref("wex_purchase_list.group_wex_purchase_list_manager")
            | cls.env.ref("stock.group_stock_manager")
            | cls.env.ref("stock.group_stock_multi_locations")
            | cls.env.ref("purchase.group_purchase_manager")
            | cls.env.ref("sales_team.group_sale_manager")
        )

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.vendor = cls.env["res.partner"].create({"name": "Staging vendor", "supplier_rank": 1})
        cls.customer = cls.env["res.partner"].create({"name": "Staging customer"})
        cls.part = cls._create_product(**{
            "name": "Staging part", "type": "consu", "is_storable": True,
            "uom_id": cls.env.ref("uom.product_uom_unit").id,
            "uom_po_id": cls.env.ref("uom.product_uom_unit").id,
            "invoice_policy": "order", "taxes_id": [Command.clear()],
        })
        cls.warehouse = cls.env["stock.warehouse"].search([("company_id", "=", cls.env.company.id)], limit=1)
        cls.env.company._ensure_wex_return_location()

    def setUp(self):
        super().setUp()
        self.line, self.receipt, self.lot = self._receive(self.part)

    def _receive(self, product, quantity=2, lot_name=None, ordered_quantity=None):
        order = self.env["purchase.order"].create({
            "partner_id": self.vendor.id,
            "order_line": [Command.create({
                "product_id": product.id, "name": product.name, "product_qty": ordered_quantity or quantity,
                "product_uom": product.uom_id.id, "price_unit": 10,
            })],
        })
        order.button_confirm()
        receipt = order.picking_ids
        receipt.move_ids.quantity = quantity
        lot = self.env["stock.lot"]
        if lot_name:
            lot = self.env["stock.lot"].create({"name": lot_name, "product_id": product.id, "company_id": self.env.company.id})
            receipt.move_line_ids.lot_id = lot
        receipt.move_ids.picked = True
        validation = receipt.button_validate()
        if isinstance(validation, dict) and validation.get("res_model") == "stock.backorder.confirmation":
            self.env["stock.backorder.confirmation"].with_context(validation.get("context", {})).create({
                "pick_ids": [Command.set(receipt.ids)],
            }).process()
        line = self.env["wex_purchase_list.line"].create({
            "product_id": product.id, "vendor_id": self.vendor.id, "quantity": ordered_quantity or quantity,
            "state": "received", "purchase_order_id": order.id,
            "purchase_order_line_id": order.order_line.id,
        })
        return line, receipt.move_ids, lot

    def _wizard(self, **values):
        move = self.env["stock.move"].browse(values.get("receipt_move_id", self.receipt.id))
        return self.env["wex.return.prepare"].create({
            "purchase_list_line_id": self.line.id, "receipt_move_id": self.receipt.id,
            "receipt_picking_id": move.picking_id.id,
            "quantity": 1, "return_reason": "unused", **values,
        })

    def _sale(self, confirmed=False, quantity=2):
        order = self.env["sale.order"].create({
            "partner_id": self.customer.id, "warehouse_id": self.warehouse.id,
            "order_line": [Command.create({"product_id": self.part.id, "product_uom_qty": quantity})],
        })
        line = order.order_line
        self.line.sale_line_id = line
        line.purchase_list_line_id = self.line
        if confirmed:
            order.action_confirm()
        return order, line

    def _repair(self, quantity=2):
        repair = self.env["repair.order"].create({"partner_id": self.customer.id, "product_id": self.part.id})
        move = self.env["stock.move"].create({
            "name": "Staging repair part", "repair_id": repair.id, "repair_line_type": "add",
            "product_id": self.part.id, "product_uom_qty": quantity,
            "product_uom": self.part.uom_id.id, "purchase_list_line_id": self.line.id,
        })
        self.line.write({"repair_id": repair.id, "repair_part_move_id": move.id})
        repair._action_repair_confirm()
        repair.action_assign()
        return repair, move

    def _available(self, location=None, product=None):
        return self.env["stock.quant"]._get_available_quantity(
            product or self.part, location or self.warehouse.lot_stock_id,
        )

