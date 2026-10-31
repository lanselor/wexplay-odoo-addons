from odoo.exceptions import UserError
from odoo.tests import tagged, Form

from .return_common import ReturnWorkflowCommon


@tagged("post_install", "-at_install")
class TestReturnStaging(ReturnWorkflowCommon):
    def test_stages_with_native_transfer_and_keeps_receipt(self):
        wizard = self._wizard(rma_reference="RMA-TEST")
        action = wizard.action_stage()
        trace = wizard.return_id
        self.assertEqual(action["res_id"], trace.internal_picking_id.id)
        self.assertEqual(trace.internal_picking_id.state, "done")
        self.assertEqual(trace.state, "pending")
        self.assertEqual(trace.rma_reference, "RMA-TEST")
        self.assertFalse(trace.return_picking_id)
        self.assertEqual(self._available(), 1)
        self.assertEqual(self._available(self.env.company.wex_return_location_id), 1)
        self.assertEqual(self.receipt.quantity, 2)
        self.assertEqual(self.line.wex_return_quantity, 1)
        self.assertEqual(self.receipt.wex_return_committed_qty, 1)

    def test_request_is_idempotent(self):
        wizard = self._wizard()
        first = wizard.action_stage()
        second = wizard.action_stage()
        self.assertEqual(first["res_id"], second["res_id"])
        self.assertEqual(len(self.line.return_ids), 1)

    def test_capacity_and_quantity_checks(self):
        self._wizard(quantity=2).action_stage()
        with self.assertRaises(UserError), self.cr.savepoint():
            self._wizard().action_stage()
        self.assertEqual(self.line.wex_return_quantity, 2)
        self.assertEqual(self._available(), 0)
        with self.assertRaises(UserError):
            self.line.action_prepare_vendor_return()

    def test_nonpositive_and_nonrepresentable_quantities(self):
        for quantity in (0, -1):
            with self.assertRaises(UserError), self.cr.savepoint():
                self._wizard(quantity=quantity).action_stage()
        with self.assertRaises(UserError), self.cr.savepoint():
            self.line._stage_vendor_return(
                self.receipt, self.part.uom_id.rounding / 2,
                self.receipt.location_dest_id, self.env["stock.lot"],
                self.env["stock.quant.package"], self.env["stock.move"], False, False,
            )
        self.assertFalse(self.line.return_ids)

    def test_confirmation_is_required_for_quote(self):
        order, sale_line = self._sale()
        with self.assertRaises(UserError), self.cr.savepoint():
            self._wizard().action_stage()
        self.assertEqual(sale_line.product_uom_qty, 2)
        self.assertEqual(order.state, "draft")
        self.assertFalse(self.line.return_ids)

    def test_full_quote_removal_preserves_order_reference(self):
        order, sale_line = self._sale(quantity=1)
        wizard = self._wizard(confirm_origin_change=True)
        wizard.action_stage()
        self.assertFalse(sale_line.exists())
        self.assertEqual(wizard.return_id.sale_order_id, order)
        self.assertEqual(order.state, "draft")

    def test_confirmed_sale_is_reduced_without_reopening(self):
        order, sale_line = self._sale(confirmed=True)
        self.assertEqual(self._available(), 0)
        wizard = self._wizard(confirm_origin_change=True)
        wizard.action_stage()
        self.assertEqual(order.state, "sale")
        self.assertEqual(sale_line.product_uom_qty, 1)
        self.assertEqual(sum(sale_line.move_ids.filtered(lambda move: move.state != "cancel").mapped("product_uom_qty")), 1)
        self.assertEqual(wizard.return_id.state, "pending")

    def test_confirmed_sale_keeps_zero_quantity_line(self):
        order, sale_line = self._sale(confirmed=True, quantity=1)
        self._wizard(confirm_origin_change=True).action_stage()
        self.assertTrue(sale_line.exists())
        self.assertEqual(sale_line.product_uom_qty, 0)
        self.assertEqual(order.state, "sale")

    def test_invoice_draft_or_posted_blocks_changes(self):
        order, sale_line = self._sale(confirmed=True)
        invoice = order._create_invoices()
        with self.assertRaises(UserError), self.cr.savepoint():
            self._wizard(confirm_origin_change=True).action_stage()
        invoice.action_post()
        with self.assertRaises(UserError), self.cr.savepoint():
            self._wizard(confirm_origin_change=True).action_stage()
        self.assertEqual(sale_line.product_uom_qty, 2)
        self.assertEqual(invoice.state, "posted")
        self.assertFalse(self.line.return_ids)

    def test_done_delivery_blocks_changes(self):
        order, sale_line = self._sale(confirmed=True)
        picking = order.picking_ids
        picking.move_ids.picked = True
        picking.button_validate()
        with self.assertRaises(UserError), self.cr.savepoint():
            self._wizard(confirm_origin_change=True).action_stage()
        self.assertEqual(sale_line.product_uom_qty, 2)
        self.assertFalse(self.line.return_ids)

    def test_failure_rolls_back_origin_and_tracking(self):
        order, sale_line = self._sale(quantity=1)
        empty = self.env["stock.location"].create({
            "name": "Empty staging source", "location_id": self.warehouse.lot_stock_id.id,
            "usage": "internal", "company_id": self.env.company.id,
        })
        with self.assertRaises(UserError):
            self._wizard(source_location_id=empty.id, confirm_origin_change=True).action_stage()
        self.assertTrue(sale_line.exists())
        self.assertEqual(sale_line.product_uom_qty, 1)
        self.assertFalse(self.line.return_ids)

    def test_other_sale_reservations_are_not_released(self):
        order, sale_line = self._sale(confirmed=True)
        self.line.sale_line_id = False
        with self.assertRaises(UserError), self.cr.savepoint():
            self._wizard().action_stage()
        self.assertEqual(sale_line.product_uom_qty, 2)
        self.assertEqual(order.picking_ids.state, "assigned")
        self.assertFalse(self.line.return_ids)

    def test_repair_part_is_reduced_natively(self):
        repair, move = self._repair()
        wizard = self._wizard(repair_move_id=move.id, confirm_origin_change=True)
        wizard.action_stage()
        self.assertEqual(move.product_uom_qty, 1)
        self.assertEqual(repair.state, "confirmed")
        self.assertEqual(wizard.return_id.repair_id, repair)

    def test_full_repair_part_is_removed_natively(self):
        repair, move = self._repair(quantity=1)
        wizard = self._wizard(repair_move_id=move.id, confirm_origin_change=True)
        wizard.action_stage()
        self.assertFalse(move.exists())
        self.assertEqual(wizard.return_id.repair_id, repair)

    def test_repair_sale_line_is_synchronized_by_odoo(self):
        repair, move = self._repair()
        repair.action_create_sale_order()
        sale_line = move.sale_line_id
        self.assertEqual(sale_line.product_uom_qty, 2)
        wizard = self._wizard(repair_move_id=move.id, confirm_origin_change=True)
        wizard.action_stage()
        self.assertEqual(sale_line.product_uom_qty, 1)
        self.assertEqual(wizard.return_id.sale_order_id, repair.sale_order_id)

    def test_picked_repair_part_is_blocked(self):
        repair, move = self._repair(quantity=1)
        move.picked = True
        with self.assertRaises(UserError), self.cr.savepoint():
            self._wizard(repair_move_id=move.id, confirm_origin_change=True).action_stage()
        self.assertTrue(move.exists())
        self.assertFalse(self.line.return_ids)

    def test_native_supplier_return_reduces_capacity(self):
        native = self.env["stock.return.picking"].create({"picking_id": self.receipt.picking_id.id})
        native.product_return_moves.filtered(lambda item: item.move_id == self.receipt).quantity = 1
        returned = native._create_return()
        returned.move_ids.picked = True
        returned.button_validate()
        with self.assertRaises(UserError), self.cr.savepoint():
            self._wizard(quantity=2).action_stage()
        self._wizard().action_stage()
        self.assertEqual(self._available(), 0)

    def test_wizard_view_and_default_selection(self):
        action = self.line.action_prepare_vendor_return()
        wizard = self.env["wex.return.prepare"].browse(action["res_id"])
        with Form(wizard) as form:
            form.return_reason = "unused"
            self.assertEqual(form.receipt_move_id, self.receipt)
            self.assertEqual(form.source_location_id, self.receipt.location_dest_id)
        self.assertFalse(wizard.return_id)

    def test_tracked_lot_is_preserved(self):
        product = self._create_product(name="Tracked staging part", tracking="lot", is_storable=True)
        self.line, self.receipt, lot = self._receive(product, lot_name="LOT-STAGING")
        with self.assertRaises(UserError), self.cr.savepoint():
            self._wizard().action_stage()
        wizard = self._wizard(lot_id=lot.id)
        wizard.action_stage()
        self.assertEqual(wizard.return_id.lot_id, lot)
        self.assertEqual(wizard.return_id.internal_picking_id.move_line_ids.lot_id, lot)

    def test_serial_number_is_preserved(self):
        product = self._create_product(name="Serial staging part", tracking="serial", is_storable=True)
        self.line, self.receipt, lot = self._receive(product, quantity=1, lot_name="SERIAL-STAGING")
        with self.assertRaises(UserError), self.cr.savepoint():
            self._wizard(quantity=2, lot_id=lot.id).action_stage()
        wizard = self._wizard(lot_id=lot.id)
        wizard.action_stage()
        self.assertEqual(wizard.return_id.internal_picking_id.move_line_ids.lot_id, lot)

    def test_partial_receipt_limits_quantity(self):
        self.line, self.receipt, self.lot = self._receive(self.part, quantity=2, ordered_quantity=4)
        self.line.state = "ordered"
        self.assertEqual(self.receipt.picking_id.state, "done")
        self.assertEqual(self.receipt.quantity, 2)
        with self.assertRaises(UserError), self.cr.savepoint():
            self._wizard(quantity=3).action_stage()
        self._wizard(quantity=2).action_stage()
        self.assertEqual(self.line.wex_return_quantity, 2)

    def test_multiple_lines_share_receipt_capacity(self):
        other = self.line.copy({
            "quantity": 2, "purchase_order_id": self.line.purchase_order_id.id,
            "purchase_order_line_id": self.line.purchase_order_line_id.id,
        })
        self.assertIn(self.receipt, other._get_return_receipts())
        self._wizard(quantity=2).action_stage()
        with self.assertRaises(UserError), self.cr.savepoint():
            self._wizard(purchase_list_line_id=other.id).action_stage()

    def test_lot_from_another_receipt_is_rejected(self):
        product = self._create_product(name="Other receipt lot part", tracking="lot", is_storable=True)
        first_line, first_receipt, first_lot = self._receive(product, lot_name="FIRST-LOT")
        other_line, other_receipt, other_lot = self._receive(product, lot_name="OTHER-LOT")
        with self.assertRaises(UserError), self.cr.savepoint():
            self._wizard(purchase_list_line_id=first_line.id, receipt_move_id=first_receipt.id, lot_id=other_lot.id).action_stage()

    def test_consigned_stock_is_not_taken(self):
        source = self.env["stock.location"].create({
            "name": "Consigned source", "location_id": self.warehouse.lot_stock_id.id,
            "usage": "internal", "company_id": self.env.company.id,
        })
        self.env["stock.quant"]._update_available_quantity(self.part, source, 1, owner_id=self.vendor)
        with self.assertRaises(UserError), self.cr.savepoint():
            self._wizard(source_location_id=source.id).action_stage()
        self.assertFalse(self.line.return_ids)

    def test_origin_from_another_source_is_rejected(self):
        other_line = self.line.copy()
        original = self.line
        self.line = other_line
        repair, move = self._repair(quantity=1)
        self.line = original
        with self.assertRaises(UserError), self.cr.savepoint():
            self._wizard(repair_move_id=move.id, confirm_origin_change=True).action_stage()
        self.assertTrue(move.exists())

    def test_locked_sale_is_not_reopened(self):
        order, sale_line = self._sale(confirmed=True)
        order.action_lock()
        with self.assertRaises(UserError), self.cr.savepoint():
            self._wizard(confirm_origin_change=True).action_stage()
        self.assertTrue(order.locked)
        self.assertEqual(sale_line.product_uom_qty, 2)

    def test_fully_staged_reservation_does_not_request_customer_notice(self):
        self.line.write({"is_reservation": True, "customer_id": self.customer.id})
        self._wizard(quantity=2).action_stage()
        self.assertFalse(self.line.is_reservation)
        self.assertFalse(self.line.customer_notified)

    def test_recorded_customer_notice_is_preserved(self):
        self.line.write({"is_reservation": True, "customer_id": self.customer.id, "customer_notified": True})
        self._wizard(quantity=2).action_stage()
        self.assertTrue(self.line.customer_notified)
        self.assertTrue(self.line.is_reservation)

    def test_packaged_stock_is_reserved_from_selected_package(self):
        source = self.env["stock.location"].create({
            "name": "Packaged staging source", "location_id": self.warehouse.lot_stock_id.id,
            "usage": "internal", "company_id": self.env.company.id,
        })
        package = self.env["stock.quant.package"].create({"name": "Staging package"})
        self.env["stock.quant"]._update_available_quantity(self.part, source, 1, package_id=package)
        wizard = self._wizard(source_location_id=source.id, package_id=package.id)
        wizard.action_stage()
        lines = wizard.return_id.internal_picking_id.move_line_ids
        self.assertEqual(lines.package_id, package)
        self.assertEqual(lines.location_id, source)

    def test_staged_identity_cannot_be_changed(self):
        wizard = self._wizard()
        wizard.action_stage()
        with self.assertRaises(UserError), self.cr.savepoint():
            wizard.return_id.write({"quantity": 2})

    def test_missing_internal_operation_does_not_change_origin(self):
        order, sale_line = self._sale(quantity=1)
        self.warehouse.int_type_id.active = False
        with self.assertRaises(UserError), self.cr.savepoint():
            self._wizard(confirm_origin_change=True).action_stage()
        self.assertTrue(sale_line.exists())
        self.assertFalse(self.line.return_ids)
