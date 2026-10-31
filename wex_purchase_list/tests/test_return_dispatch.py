from odoo import Command
from odoo.exceptions import UserError, AccessError
from odoo.tests import tagged, Form
from odoo.tests.common import new_test_user
from unittest.mock import patch

from .return_common import ReturnWorkflowCommon


@tagged("post_install", "-at_install")
class TestReturnDispatch(ReturnWorkflowCommon):
    def _stage(self, quantity=1, **values):
        wizard = self._wizard(quantity=quantity, **values)
        wizard.action_stage()
        return wizard.return_id

    def _dispatch_wizard(self, records):
        action = records.action_open_dispatch()
        return self.env["wex.return.dispatch"].browse(action["res_id"])

    def _dispatch(self, records):
        wizard = self._dispatch_wizard(records)
        wizard.action_create_returns()
        return wizard.picking_ids

    def _validate(self, picking, cancel_backorder=False):
        picking.move_ids.filtered(lambda move: move.state not in ("done", "cancel")).picked = True
        result = picking.button_validate()
        if isinstance(result, dict) and result.get("res_model") == "stock.backorder.confirmation":
            wizard = self.env["stock.backorder.confirmation"].with_context(result.get("context", {})).create({
                "pick_ids": [Command.set(picking.ids)],
            })
            return wizard.process_cancel_backorder() if cancel_backorder else wizard.process()
        return result

    def test_prepare_and_validate_native_supplier_return(self):
        record = self._stage()
        picking = self._dispatch(record)
        self.assertNotEqual(picking.state, "done")
        self.assertEqual(record.state, "return_prepared")
        self.assertEqual(record.prepared_quantity, 1)
        self.assertEqual(record.remaining_quantity, 1)
        self.assertEqual(self._available(self.env.company.wex_return_location_id), 0)
        self.assertEqual(picking.location_id, record.staging_location_id)
        self.assertEqual(picking.location_dest_id.usage, "supplier")
        self.assertEqual(picking.return_id, self.receipt.picking_id)
        self.assertEqual(picking.move_ids.origin_returned_move_id, self.receipt)
        self._validate(picking)
        self.assertEqual(record.state, "returned")
        self.assertEqual(record.returned_quantity, 1)
        self.assertEqual(record.remaining_quantity, 0)
        self.assertEqual(record.prepared_quantity, 0)
        self.assertEqual(self.line.wex_return_quantity, 1)
        self.assertEqual(self.receipt.wex_return_committed_qty, 0)

    def test_same_receipt_groups_without_merging_trace_identity(self):
        records = self._stage() | self._stage()
        picking = self._dispatch(records)
        self.assertEqual(len(picking), 1)
        self.assertEqual(len(picking.move_ids), 2)
        self.assertEqual(picking.move_ids.wex_vendor_return_id, records)
        self._validate(picking)
        self.assertEqual(records.mapped("state"), ["returned", "returned"])

    def test_different_receipts_create_separate_native_documents(self):
        first = self._stage()
        self.line, self.receipt, self.lot = self._receive(self.part)
        second = self._stage()
        picking = self._dispatch(first | second)
        self.assertEqual(len(picking), 2)
        self.assertEqual(len(picking.return_id), 2)

    def test_same_receipt_with_different_buffers_keeps_both_reservations(self):
        first = self._stage()
        location = self.env["stock.location"].create({
            "name": "Second return buffer", "usage": "internal", "company_id": self.env.company.id,
            "location_id": self.env.ref("stock.stock_location_locations").id,
        })
        self.env.company.wex_return_location_id = location
        second = self._stage()
        pickings = self._dispatch(first | second)
        self.assertEqual(len(pickings), 2)
        self.assertTrue(all(picking.state == "assigned" for picking in pickings))
        self.assertEqual(sum(pickings.move_ids.mapped("quantity")), 2)
        for picking in pickings:
            self._validate(picking)
        self.assertEqual((first | second).mapped("state"), ["returned", "returned"])

    def test_bulk_rma_and_per_piece_edit(self):
        records = self._stage() | self._stage()
        action = records.action_open_rma_assignment()
        wizard = self.env["wex.return.rma"].browse(action["res_id"])
        wizard.rma_reference = "  COMMON-123  "
        wizard.action_assign()
        self.assertEqual(records.mapped("rma_reference"), ["COMMON-123", "COMMON-123"])
        records[0].rma_reference = "ITEM-123"
        self.assertEqual(records[1].rma_reference, "COMMON-123")

    def test_prepared_or_completed_records_cannot_be_prepared_twice(self):
        record = self._stage()
        picking = self._dispatch(record)
        with self.assertRaises(UserError):
            record.action_open_dispatch()
        self._validate(picking)
        with self.assertRaises(UserError):
            record.action_open_dispatch()

    def test_dispatch_request_is_idempotent(self):
        record = self._stage()
        wizard = self._dispatch_wizard(record)
        first = wizard.action_create_returns()
        second = wizard.action_create_returns()
        self.assertEqual(first["res_id"], second["res_id"])
        self.assertEqual(len(record.dispatch_move_ids), 1)

    def test_cancelled_native_document_can_be_prepared_again(self):
        record = self._stage()
        first = self._dispatch(record)
        first.action_cancel()
        self.assertEqual(record.state, "pending")
        self.assertEqual(record.prepared_quantity, 0)
        self.assertEqual(self.receipt.wex_return_committed_qty, 1)
        second = self._dispatch(record)
        self.assertNotEqual(first, second)
        self.assertEqual(record.return_picking_id, first)
        self.assertEqual(len(record.return_picking_ids), 2)
        self._validate(second)
        self.assertEqual(record.state, "returned")

    def test_partial_delivery_keeps_native_backorder_and_history(self):
        record = self._stage(quantity=2)
        picking = self._dispatch(record)
        picking.move_ids.quantity = 1
        self._validate(picking)
        backorder = self.env["stock.picking"].search([("backorder_id", "=", picking.id)])
        self.assertEqual(len(backorder), 1)
        self.assertEqual(backorder.move_ids.wex_vendor_return_id, record)
        self.assertEqual(record.state, "partial")
        self.assertEqual(record.returned_quantity, 1)
        self.assertEqual(record.remaining_quantity, 1)
        self.assertEqual(record.prepared_quantity, 1)
        backorder.action_assign()
        self._validate(backorder)
        self.assertEqual(record.state, "returned")
        self.assertEqual(record.returned_quantity, 2)
        self.assertEqual(len(record.return_picking_ids), 2)

    def test_cancelled_partial_backorder_allows_remaining_quantity(self):
        record = self._stage(quantity=2)
        picking = self._dispatch(record)
        picking.move_ids.quantity = 1
        self._validate(picking, cancel_backorder=True)
        self.assertEqual(record.remaining_quantity, 1)
        self.assertEqual(record.prepared_quantity, 0)
        second = self._dispatch(record)
        self.assertEqual(second.move_ids.product_uom_qty, 1)
        self._validate(second)
        self.assertEqual(record.returned_quantity, 2)

    def test_lot_and_serial_identity_survives_dispatch(self):
        for tracking in ("lot", "serial"):
            product = self._create_product(name="Dispatch " + tracking, tracking=tracking, is_storable=True)
            self.line, self.receipt, lot = self._receive(product, quantity=1, lot_name="DISPATCH-" + tracking)
            record = self._stage(lot_id=lot.id)
            picking = self._dispatch(record)
            self.assertEqual(picking.move_line_ids.lot_id, lot)
            self._validate(picking)
            self.assertEqual(record.returned_quantity, 1)

    def test_missing_buffer_stock_rolls_back_all_generated_documents(self):
        record = self._stage()
        self.env["stock.quant"]._update_available_quantity(self.part, record.staging_location_id, -1)
        before = self.env["stock.picking"].search_count([])
        with self.assertRaises(UserError):
            self._dispatch(record)
        self.assertEqual(self.env["stock.picking"].search_count([]), before)
        self.assertFalse(record.return_picking_id)
        self.assertEqual(record.state, "pending")

    def test_over_delivery_is_rejected(self):
        record = self._stage()
        picking = self._dispatch(record)
        picking.move_ids.quantity = 2
        with self.assertRaises(UserError), self.cr.savepoint():
            self._validate(picking)
        self.assertNotEqual(picking.state, "done")

    def test_missing_stock_after_preparation_cannot_be_forced_negative(self):
        record = self._stage()
        picking = self._dispatch(record)
        self.env["stock.quant"]._update_available_quantity(self.part, record.staging_location_id, -1)
        with self.assertRaises(UserError), self.cr.savepoint():
            self._validate(picking)
        self.assertNotEqual(picking.state, "done")
        self.assertEqual(record.returned_quantity, 0)

    def test_changing_supplier_on_document_is_blocked(self):
        record = self._stage()
        picking = self._dispatch(record)
        picking.partner_id = self.customer
        with self.assertRaises(UserError), self.cr.savepoint():
            self._validate(picking)
        self.assertEqual(record.returned_quantity, 0)

    def test_supplier_return_can_be_received_back_natively(self):
        record = self._stage()
        picking = self._dispatch(record)
        self._validate(picking)
        native = self.env["stock.return.picking"].create({"picking_id": picking.id})
        native.product_return_moves.quantity = 1
        incoming = native._create_return()
        self._validate(incoming)
        self.assertEqual(record.returned_quantity, 0)
        self.assertEqual(record.state, "pending")
        self.assertEqual(record.remaining_quantity, 1)
        self.assertEqual(self.receipt.wex_return_committed_qty, 1)
        self.assertEqual(self.line._get_native_return_quantity(self.receipt), 0)

    def test_native_exchange_does_not_reuse_returned_piece_identity(self):
        record = self._stage()
        picking = self._dispatch(record)
        self._validate(picking)
        native = self.env["stock.return.picking"].create({"picking_id": picking.id})
        native.product_return_moves.quantity = 1
        incoming = native._create_return()
        exchange = native._create_exchange(incoming)
        self.assertFalse(exchange.move_ids.wex_vendor_return_id)

    def test_multiple_suppliers_dispatch_separately_and_cannot_share_bulk_rma(self):
        first = self._stage()
        self.vendor = self.env["res.partner"].create({"name": "Other dispatch supplier", "supplier_rank": 1})
        self.line, self.receipt, self.lot = self._receive(self.part)
        second = self._stage()
        records = first | second
        with self.assertRaises(UserError):
            records.action_open_rma_assignment()
        pickings = self._dispatch(records)
        self.assertEqual(len(pickings), 2)
        self.assertEqual(len(pickings.partner_id.commercial_partner_id), 2)

    def test_untouched_receipt_line_dependencies_are_not_unreserved(self):
        record = self._stage()
        other_product = self._create_product(name="Untouched product", is_storable=True)
        other_move = self.receipt.copy({"product_id": other_product.id, "name": other_product.name})
        destination = self.env["stock.move"].create({
            "name": "Untouched dependency", "product_id": other_product.id,
            "product_uom": other_product.uom_id.id, "product_uom_qty": 1,
            "location_id": self.warehouse.lot_stock_id.id,
            "location_dest_id": self.env.ref("stock.stock_location_customers").id,
            "move_orig_ids": [Command.link(other_move.id)],
        })
        destination._action_confirm()
        original = type(destination)._do_unreserve
        unreserved_ids = []

        def track_unreserve(moves):
            unreserved_ids.extend(moves.ids)
            return original(moves)

        with patch.object(type(destination), "_do_unreserve", track_unreserve):
            picking = self._dispatch(record)
        self.assertEqual(len(picking), 1)
        self.assertNotIn(destination.id, unreserved_ids)

    def test_selected_receipt_with_pending_dependency_is_blocked(self):
        record = self._stage()
        move = self.env["stock.move"].create({
            "name": "Pending receipt dependency", "product_id": self.part.id,
            "product_uom": self.part.uom_id.id, "product_uom_qty": 1,
            "location_id": self.warehouse.lot_stock_id.id,
            "location_dest_id": self.env.ref("stock.stock_location_customers").id,
            "move_orig_ids": [Command.link(self.receipt.id)],
        })
        move._action_confirm()
        move._action_assign()
        reserved = move.quantity
        with self.assertRaises(UserError):
            record.action_open_dispatch()
        self.assertEqual(move.quantity, reserved)
        self.assertFalse(record.return_picking_id)

    def test_menu_views_and_dispatch_preview(self):
        record = self._stage()
        wizard = self._dispatch_wizard(record)
        with Form(wizard) as form:
            self.assertEqual(form.operation_count, 1)
            self.assertEqual(form.supplier_count, 1)
        menu = self.env.ref("wex_purchase_list.menu_wex_purchase_returns")
        self.assertEqual(menu.action.res_model, record._name)
        with Form(record) as form:
            self.assertEqual(form.state, "pending")

    def test_read_only_user_cannot_create_supplier_return(self):
        record = self._stage()
        user = new_test_user(self.env, login="dispatch_reader", groups="base.group_user,wex_purchase_list.group_wex_purchase_list_user", company_id=self.env.company.id)
        with self.assertRaises(AccessError):
            record.with_user(user).action_open_dispatch()

    def test_inactive_company_context_cannot_prepare_or_assign_rma(self):
        record = self._stage()
        other = self.env["res.company"].create({"name": "Other dispatch company"})
        self.env.user.company_ids = [Command.link(other.id)]
        foreign = record.with_context(allowed_company_ids=[other.id])
        with self.assertRaises(AccessError):
            foreign.action_open_dispatch()
        with self.assertRaises(AccessError):
            foreign.action_open_rma_assignment()

    def test_record_without_staging_transfer_cannot_be_dispatched(self):
        record = self.env["wex.purchase.return"].create({
            "purchase_list_line_id": self.line.id, "receipt_move_id": self.receipt.id, "quantity": 1,
        })
        with self.assertRaises(UserError):
            record.action_open_dispatch()
