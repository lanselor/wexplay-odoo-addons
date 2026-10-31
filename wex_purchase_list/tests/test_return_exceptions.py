from odoo import Command
from odoo.exceptions import AccessError, UserError
from odoo.tests import Form, tagged
from odoo.tests.common import new_test_user

from .return_common import ReturnWorkflowCommon


@tagged("post_install", "-at_install")
class TestReturnExceptions(ReturnWorkflowCommon):
    def _stage(self, **values):
        wizard = self._wizard(**values)
        wizard.action_stage()
        return wizard.return_id

    def _resolve(self, trace, disposition="recover", **values):
        wizard = self.env["wex.return.resolve"].create({
            "return_id": trace.id, "quantity": 1, "disposition": disposition,
            "destination_location_id": self.warehouse.lot_stock_id.id if disposition == "recover" else False,
            "explanation": "Changed decision after checking physical part", **values,
        })
        wizard.action_resolve()
        return wizard

    def _dispatch(self, trace):
        action = trace.action_open_dispatch()
        wizard = self.env["wex.return.dispatch"].browse(action["res_id"])
        wizard.action_create_returns()
        return wizard.picking_ids

    def _validate(self, picking):
        picking.move_ids.picked = True
        return picking.button_validate()

    def test_reason_required_and_other_needs_explanation(self):
        for vals in ({"return_reason": False}, {"return_reason": "other", "return_notes": "  "}):
            with self.assertRaises(UserError), self.cr.savepoint():
                self._stage(**vals)
        trace = self._stage(return_reason="other", return_notes="Packaging incomplete")
        self.assertEqual(trace.return_reason, "other")
        self.assertEqual(trace.return_notes, "Packaging incomplete")

    def test_legacy_trace_without_reason_remains_valid(self):
        trace = self.env["wex.purchase.return"].create({
            "company_id": self.env.company.id, "purchase_list_line_id": self.line.id,
            "receipt_move_id": self.receipt.id, "quantity": 1,
        })
        self.assertFalse(trace.return_reason)
        trace.rma_reference = "LEGACY"

    def test_replacement_creates_new_part_and_new_pending_request(self):
        repair, old = self._repair(quantity=1)
        old.wex_is_reservation = True
        wizard = self._wizard(repair_move_id=old.id, confirm_origin_change=True,
                              request_replacement=True, replacement_quantity=2)
        self.assertTrue(wizard.can_request_replacement)
        wizard.action_stage()
        trace = wizard.return_id
        new = trace.replacement_move_id
        request = trace.replacement_purchase_line_id
        self.assertFalse(old.exists())
        self.assertEqual(new.repair_id, repair)
        self.assertEqual(new.product_uom_qty, 2)
        self.assertEqual(new.wex_replacement_return_id, trace)
        self.assertNotEqual(request, self.line)
        self.assertEqual(request.state, "to_purchase")
        self.assertEqual(request.quantity, 2)
        self.assertTrue(new.wex_is_reservation)
        self.assertTrue(request.is_reservation)
        wizard.action_stage()
        self.assertEqual(trace.replacement_move_id, new)
        self.assertEqual(request.quantity, 2)

    def test_partial_removal_still_creates_distinct_sat_part(self):
        repair, old = self._repair(quantity=2)
        wizard = self._wizard(repair_move_id=old.id, confirm_origin_change=True, request_replacement=True)
        wizard.action_stage()
        self.assertTrue(old.exists())
        self.assertEqual(old.product_uom_qty, 1)
        self.assertNotEqual(wizard.return_id.replacement_move_id, old)
        self.assertEqual(len(repair.move_ids.filtered(lambda move: move.product_id == self.part)), 2)

    def test_replacement_does_not_merge_with_another_ordered_request(self):
        repair, old = self._repair(quantity=1)
        existing = self.env["wex_purchase_list.line"].create({
            "repair_id": repair.id, "product_id": self.part.id, "vendor_id": self.vendor.id,
            "quantity": 3, "state": "ordered",
        })
        wizard = self._wizard(repair_move_id=old.id, confirm_origin_change=True, request_replacement=True)
        wizard.action_stage()
        request = wizard.return_id.replacement_purchase_line_id
        self.assertNotEqual(request, existing)
        self.assertEqual(existing.quantity, 3)
        self.assertEqual(existing.state, "ordered")
        self.assertEqual(request.state, "to_purchase")

    def test_replacement_failure_rolls_back_staging_and_origin(self):
        repair, old = self._repair(quantity=1)
        wizard = self._wizard(repair_move_id=old.id, confirm_origin_change=True,
                              request_replacement=True, replacement_quantity=-1)
        available_before = self._available()
        with self.assertRaises(UserError):
            wizard.action_stage()
        self.assertTrue(old.exists())
        self.assertFalse(wizard.return_id)
        self.assertFalse(self.line.return_ids)
        self.assertEqual(self._available(), available_before)

    def test_finalized_sat_cannot_request_replacement(self):
        repair, old = self._repair()
        wizard = self._wizard(repair_move_id=old.id, request_replacement=True)
        repair.state = "done"
        self.assertFalse(wizard.can_request_replacement)
        with self.assertRaises(UserError):
            wizard._check_replacement_request()

    def test_replacement_is_optional_and_absent_for_sale(self):
        order, line = self._sale()
        wizard = self._wizard(confirm_origin_change=True)
        self.assertFalse(wizard.can_request_replacement)
        wizard.action_stage()
        self.assertFalse(wizard.return_id.replacement_move_id)

    def test_recover_stock_and_allow_return_again(self):
        trace = self._stage()
        wizard = self._resolve(trace)
        self.assertEqual(wizard.resolution_id.picking_id.state, "done")
        self.assertEqual(trace.recovered_quantity, 1)
        self.assertEqual(trace.remaining_quantity, 0)
        self.assertEqual(trace.state, "resolved")
        self.assertEqual(self.line.wex_return_quantity, 0)
        self.assertEqual(self.receipt.wex_return_committed_qty, 0)
        self.assertEqual(self._available(), 2)
        wizard.action_resolve()
        self.assertEqual(trace.recovered_quantity, 1)
        second = self._stage()
        self.assertEqual(second.remaining_quantity, 1)

    def test_recovered_piece_can_be_assigned_to_another_repair(self):
        trace = self._stage()
        self._resolve(trace)
        repair = self.env["repair.order"].create({"partner_id": self.customer.id, "product_id": self.part.id})
        move = self.env["stock.move"].create({
            "repair_id": repair.id, "repair_line_type": "add", "product_id": self.part.id,
            "product_uom": self.part.uom_id.id, "product_uom_qty": 1,
        })
        repair._action_repair_confirm()
        repair.action_assign()
        self.assertEqual(move.state, "assigned")
        self.assertFalse(move.wex_recovered_return_id)

    def test_review_note_does_not_restrict_subsequent_dispatch(self):
        trace = self._stage()
        wizard = self._resolve(trace, "hold")
        self.assertEqual(wizard.resolution_id.state, "done")
        self.assertEqual(trace.state, "pending")
        picking = self._dispatch(trace)
        self._validate(picking)
        self.assertEqual(trace.state, "returned")

    def test_scrap_uses_native_review_and_confirmation(self):
        trace = self._stage(return_reason="defective")
        wizard = self._resolve(trace, "scrap")
        scrap = wizard.resolution_id.scrap_ids
        self.assertEqual(scrap.state, "draft")
        self.assertEqual(trace.remaining_quantity, 1)
        self.assertEqual(trace.scrapped_quantity, 0)
        scrap.action_validate()
        self.assertEqual(scrap.state, "done")
        self.assertEqual(trace.scrapped_quantity, 1)
        self.assertEqual(trace.remaining_quantity, 0)
        self.assertEqual(trace.state, "resolved")
        self.assertEqual(self._available(trace.staging_location_id), 0)

    def test_unused_scrap_draft_does_not_block_shipping(self):
        trace = self._stage()
        wizard = self._resolve(trace, "scrap")
        picking = self._dispatch(trace)
        self._validate(picking)
        with self.assertRaises(UserError), self.cr.savepoint():
            wizard.resolution_id.scrap_ids.action_validate()
        self.assertEqual(trace.returned_quantity, 1)

    def test_recovery_cannot_release_prepared_supplier_return(self):
        trace = self._stage()
        picking = self._dispatch(trace)
        with self.assertRaises(UserError):
            self._resolve(trace)
        self.assertEqual(picking.state, "assigned")
        self.assertEqual(trace.recovered_quantity, 0)
        picking.action_cancel()
        self._resolve(trace)
        self.assertEqual(trace.state, "resolved")

    def test_partial_recovery_then_dispatch_remaining(self):
        trace = self._stage(quantity=2)
        self._resolve(trace)
        self.assertEqual(trace.state, "partial")
        self.assertEqual(trace.remaining_quantity, 1)
        picking = self._dispatch(trace)
        self.assertEqual(picking.move_ids.product_uom_qty, 1)
        self._validate(picking)
        self.assertEqual(trace.state, "closed")
        self.assertEqual(trace.returned_quantity, 1)
        self.assertEqual(trace.recovered_quantity, 1)
        self.assertEqual(trace.remaining_quantity, 0)

    def test_recover_and_scrap_independent_partial_quantities(self):
        trace = self._stage(quantity=2)
        self._resolve(trace)
        scrap = self._resolve(trace, "scrap").resolution_id.scrap_ids
        scrap.action_validate()
        self.assertEqual(trace.state, "resolved")
        self.assertEqual(trace.recovered_quantity, 1)
        self.assertEqual(trace.scrapped_quantity, 1)
        self.assertEqual(trace.remaining_quantity, 0)

    def test_native_reverse_of_recovery_restores_pending_quantity(self):
        trace = self._stage()
        resolution = self._resolve(trace).resolution_id
        native = self.env["stock.return.picking"].create({"picking_id": resolution.picking_id.id})
        native.product_return_moves.quantity = 1
        inverse = native._create_return()
        self._validate(inverse)
        self.assertEqual(trace.recovered_quantity, 0)
        self.assertEqual(trace.remaining_quantity, 1)
        self.assertEqual(trace.state, "pending")
        self.assertEqual(self.line.wex_return_quantity, 1)

    def test_wrong_destination_quantity_or_explanation_rolls_back(self):
        trace = self._stage()
        for values in ({"quantity": 2}, {"explanation": "  "}, {"destination_location_id": trace.staging_location_id.id}):
            with self.assertRaises(UserError), self.cr.savepoint():
                self._resolve(trace, **values)
        self.assertFalse(trace.resolution_ids)
        self.assertEqual(trace.remaining_quantity, 1)

    def test_serial_recovery_preserves_identity(self):
        product = self._create_product(name="Resolution serial", tracking="serial", is_storable=True)
        self.line, self.receipt, lot = self._receive(product, quantity=1, lot_name="RESOLUTION-SERIAL")
        trace = self._stage(lot_id=lot.id)
        picking = self._resolve(trace).resolution_id.picking_id
        self.assertEqual(picking.move_line_ids.lot_id, lot)
        self.assertEqual(self._available(product=product), 1)

    def test_native_scrap_tampering_is_rejected(self):
        trace = self._stage()
        scrap = self._resolve(trace, "scrap").resolution_id.scrap_ids
        scrap.location_id = self.warehouse.lot_stock_id
        with self.assertRaises(UserError), self.cr.savepoint():
            scrap.do_scrap()
        self.assertEqual(trace.scrapped_quantity, 0)

    def test_history_is_immutable_and_user_cannot_resolve(self):
        trace = self._stage()
        resolution = self._resolve(trace, "hold").resolution_id
        with self.assertRaises(UserError):
            resolution.explanation = "Rewrite history"
        user = new_test_user(self.env, login="resolution_reader", groups="wex_purchase_list.group_wex_purchase_list_user")
        self.assertEqual(trace.with_user(user).resolution_ids, resolution)
        with self.assertRaises(AccessError):
            trace.with_user(user).action_open_resolution()

    def test_resolution_form_loads_with_required_fields(self):
        trace = self._stage()
        action = trace.action_open_resolution()
        wizard = self.env["wex.return.resolve"].browse(action["res_id"])
        with Form(wizard) as form:
            form.disposition = "hold"
            form.explanation = "Pending supplier answer"
        wizard.action_resolve()
        self.assertEqual(trace.state, "pending")

    def test_missing_physical_stock_rolls_back_recovery(self):
        trace = self._stage()
        self.env["stock.quant"]._update_available_quantity(self.part, trace.staging_location_id, -1)
        with self.assertRaises(UserError):
            self._resolve(trace)
        self.assertFalse(trace.resolution_ids)
        self.assertEqual(trace.recovered_quantity, 0)

    def test_recovery_destination_from_other_company_is_rejected(self):
        trace = self._stage()
        other = self.setup_other_company()["company"]
        location = self.env["stock.location"].create({
            "name": "Foreign recovery destination", "usage": "internal", "company_id": other.id,
        })
        with self.assertRaises(UserError), self.cr.savepoint():
            self._resolve(trace, destination_location_id=location.id)
        self.assertFalse(trace.resolution_ids)

    def test_lot_scrap_keeps_received_lot(self):
        product = self._create_product(name="Resolution lot", tracking="lot", is_storable=True)
        self.line, self.receipt, lot = self._receive(product, lot_name="RESOLUTION-LOT")
        trace = self._stage(lot_id=lot.id)
        scrap = self._resolve(trace, "scrap").resolution_id.scrap_ids
        scrap.action_validate()
        self.assertEqual(scrap.move_ids.move_line_ids.lot_id, lot)
        self.assertEqual(trace.scrapped_quantity, 1)

    def test_partial_shipment_can_recover_cancelled_remainder(self):
        trace = self._stage(quantity=2)
        picking = self._dispatch(trace)
        picking.move_ids.quantity = 1
        picking.move_ids.picked = True
        result = picking.button_validate()
        self.env["stock.backorder.confirmation"].with_context(result.get("context", {})).create({
            "pick_ids": [Command.set(picking.ids)],
        }).process_cancel_backorder()
        self._resolve(trace)
        self.assertEqual(trace.state, "closed")
        self.assertEqual(trace.returned_quantity, 1)
        self.assertEqual(trace.recovered_quantity, 1)

    def test_replacement_failure_after_staging_rolls_back_all(self):
        from unittest.mock import patch

        repair, old = self._repair(quantity=1)
        wizard = self._wizard(repair_move_id=old.id, confirm_origin_change=True, request_replacement=True)
        before = self._available()
        with patch.object(type(wizard), "_create_replacement_request", side_effect=UserError("Request failed")):
            with self.assertRaises(UserError):
                wizard.action_stage()
        self.assertTrue(old.exists())
        self.assertEqual(old.product_uom_qty, 1)
        self.assertFalse(self.line.return_ids)
        self.assertFalse(wizard.return_id)
        self.assertEqual(self._available(), before)

    def test_no_resolution_required_for_legacy_record_to_ship(self):
        trace = self._stage()
        trace.return_reason = False
        self._validate(self._dispatch(trace))
        self.assertEqual(trace.state, "returned")
        self.assertFalse(trace.resolution_ids)

    def test_resolution_company_rule_is_global_for_manager(self):
        trace = self._stage()
        resolution = self._resolve(trace, "hold").resolution_id
        other = self.setup_other_company()["company"]
        with self.assertRaises(AccessError):
            resolution.with_context(allowed_company_ids=[other.id]).read(["explanation"])

    def test_batch_scrap_cannot_dispose_same_units_twice(self):
        trace = self._stage()
        first = self._resolve(trace, "scrap").resolution_id.scrap_ids
        second = self._resolve(trace, "scrap").resolution_id.scrap_ids
        with self.assertRaises(UserError):
            (first | second).do_scrap()
        self.assertEqual(first.state, "draft")
        self.assertEqual(second.state, "draft")
        self.assertEqual(trace.scrapped_quantity, 0)

    def test_reversing_recovery_cannot_reuse_already_reallocated_receipt(self):
        trace = self._stage(quantity=2)
        resolution = self._resolve(trace, quantity=2).resolution_id
        self._stage(quantity=2)
        # Otra compra aporta stock físico, pero no capacidad adicional a esta recepción.
        self._receive(self.part, quantity=2)
        native = self.env["stock.return.picking"].create({"picking_id": resolution.picking_id.id})
        native.product_return_moves.quantity = 2
        inverse = native._create_return()
        with self.assertRaises(UserError), self.cr.savepoint():
            self._validate(inverse)
        self.assertEqual(trace.recovered_quantity, 2)
        self.assertEqual(self.line.wex_return_quantity, 2)
