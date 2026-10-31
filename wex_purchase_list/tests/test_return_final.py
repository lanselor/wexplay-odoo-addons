from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import tagged

from .return_common import ReturnWorkflowCommon


@tagged("post_install", "-at_install")
class TestReturnFinalReview(ReturnWorkflowCommon):
    def _dispatch_and_validate(self, records):
        action = records.action_open_dispatch()
        wizard = self.env["wex.return.dispatch"].browse(action["res_id"])
        wizard.action_create_returns()
        for picking in wizard.picking_ids:
            picking.move_ids.picked = True
            picking.button_validate()
        return wizard.picking_ids

    def test_repair_origin_is_preserved_and_cannot_be_reassigned(self):
        repair, move = self._repair(quantity=1)
        wizard = self._wizard(repair_move_id=move.id, confirm_origin_change=True)
        wizard.action_stage()
        record = wizard.return_id
        self.assertFalse(move.exists())
        self.assertEqual(record.repair_id, repair)
        other = self.env["repair.order"].create({"partner_id": self.customer.id, "product_id": self.part.id})
        with self.assertRaises(UserError), self.cr.savepoint():
            self.line.repair_id = other
        with self.assertRaises(UserError), self.cr.savepoint():
            record.repair_id = other
        self.assertEqual(record.repair_id, repair)

    def test_new_repair_trace_keeps_sale_after_original_part_was_removed(self):
        repair, move = self._repair(quantity=1)
        extra = move.copy({"repair_id": repair.id, "purchase_list_line_id": self.line.id})
        repair.action_create_sale_order()
        first = self._wizard(repair_move_id=move.id, confirm_origin_change=True)
        first.action_stage()
        self.assertFalse(move.exists())
        second = self._wizard(repair_move_id=extra.id, confirm_origin_change=True)
        second.action_stage()
        self.assertEqual(second.return_id.sale_order_id, repair.sale_order_id)
        self.assertEqual(first.return_id.sale_order_id, repair.sale_order_id)

    def test_receipt_in_purchase_uom_dispatches_in_base_units(self):
        dozen = self.env.ref("uom.product_uom_dozen")
        order = self.env["purchase.order"].create({
            "partner_id": self.vendor.id,
            "order_line": [Command.create({"name": self.part.name, "product_id": self.part.id,
                "product_qty": 2, "product_uom": dozen.id, "price_unit": 120})],
        })
        order.button_confirm()
        receipt = order.picking_ids.move_ids
        receipt.quantity = receipt.product_uom_qty
        receipt.picked = True
        receipt.picking_id.button_validate()
        source = self.env["wex_purchase_list.line"].create({
            "product_id": self.part.id, "vendor_id": self.vendor.id, "quantity": 24,
            "state": "received", "purchase_order_id": order.id, "purchase_order_line_id": order.order_line.id,
        })
        wizard = self._wizard(purchase_list_line_id=source.id, receipt_move_id=receipt.id, quantity=12)
        wizard.action_stage()
        record = wizard.return_id
        pickings = self._dispatch_and_validate(record)
        self.assertEqual(record.returned_quantity, 12)
        self.assertEqual(record.remaining_quantity, 0)
        self.assertEqual(pickings.move_ids.product_uom, self.part.uom_id)
        self.assertEqual(source._get_native_return_quantity(receipt), 12)

    def test_two_companies_can_dispatch_without_mixing_documents(self):
        first_wizard = self._wizard()
        first_wizard.action_stage()
        first = first_wizard.return_id
        first_company = self.env.company
        other = self.setup_other_company()["company"]
        original_env = self.env
        try:
            self.env = self.env["base"].with_company(other).env
            self.line, self.receipt, self.lot = self._receive(self.part)
            wizard = self._wizard()
            wizard.action_stage()
            second = wizard.return_id
        finally:
            self.env = original_env
        records = (first | second).with_context(allowed_company_ids=[first_company.id, other.id])
        action = records.action_open_dispatch()
        dispatch = self.env["wex.return.dispatch"].with_context(allowed_company_ids=[first_company.id, other.id]).browse(action["res_id"])
        dispatch.action_create_returns()
        self.assertEqual(len(dispatch.picking_ids), 2)
        self.assertEqual(set(dispatch.picking_ids.company_id.ids), {first_company.id, other.id})
        for picking in dispatch.picking_ids:
            self.assertEqual(picking.move_ids.company_id, picking.company_id)
            self.assertEqual(picking.move_ids.wex_vendor_return_id.company_id, picking.company_id)

    def test_sending_return_does_not_trigger_receipt_notifications(self):
        wizard = self._wizard()
        wizard.action_stage()
        record = wizard.return_id
        action = record.action_open_dispatch()
        dispatch = self.env["wex.return.dispatch"].browse(action["res_id"])
        dispatch.action_create_returns()
        other_product = self._create_product(name="Other fully received part", is_storable=True)
        other_purchase_line = self.env["purchase.order.line"].create({
            "order_id": self.line.purchase_order_id.id, "product_id": other_product.id,
            "name": other_product.name, "product_qty": 1, "product_uom": other_product.uom_id.id,
            "price_unit": 10,
        })
        other_receipt = other_purchase_line.move_ids.filtered(lambda move: move.state not in ("done", "cancel"))
        other_receipt.quantity = 1
        other_receipt.picked = True
        other_receipt.picking_id.button_validate()
        other_source = self.env["wex_purchase_list.line"].create({
            "product_id": other_product.id, "vendor_id": self.vendor.id,
            "quantity": 1, "state": "ordered", "is_reservation": True,
            "customer_id": self.customer.id, "purchase_order_id": self.line.purchase_order_id.id,
            "purchase_order_line_id": other_purchase_line.id,
        })
        self.line.state = "ordered"
        dispatch.picking_ids.move_ids.picked = True
        result = dispatch.picking_ids.button_validate()
        self.assertIs(result, True)
        self.assertEqual(self.line.state, "ordered")
        self.assertEqual(other_source.state, "ordered")
