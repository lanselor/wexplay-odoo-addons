# Wexplay Repair Delivery Architecture

## Purpose

`wexplay_repair_delivery` adds the delivery stage on top of the SAT repair stack.

It currently covers:
- extra `delivered` state on `repair.order`
- pending-delivery filter logic
- delivery confirmation wizard after payment
- delivery action from repair order
- SAT internal notification when a budget is explicitly accepted
- repair shipping operations with one pickup and one delivery maximum per repair

## Current Responsibilities

### `models/repair_order.py`
- Adds the `delivered` state
- Computes delivery helper fields
- Validates whether a repair can be marked as delivered
- Posts SAT channel notifications
- Hooks budget acceptance through `action_budget_accept()`
- Exposes pickup/delivery operation shortcuts from the repair form
- Keeps the repair-level activation flag `x_requires_shipping`, which gates
  logistics editing/actions while still showing historical operations.

### `models/repair_shipping_operation.py`
- Owns one logistics operation for a repair
- Supports two operation types:
  - `pickup`: customer to Wexplay
  - `delivery`: Wexplay to customer
- Enforces one pickup and one delivery maximum per repair
- Stores the configuration, cost policy, operation result, tracking, label, and
  last error per operation
- Creates incoming or outgoing `stock.picking` records
- Sends delivery pickings through Odoo's native `delivery.carrier` flow
- Creates MRW customer pickups through `mrw.shipping.shipment` when the carrier
  is MRW
- Links any created pickup `mrw.shipping.shipment` back to the SAT operation and
  to the optional incoming `stock.picking`
- Reuses MRW label retrieval from the linked MRW shipment or the linked picking
- Reuses MRW public tracking URL from the linked MRW shipment or the linked
  picking
- Keeps tracking, label, picking, invoice, and sale-line references per
  operation

### `models/stock_picking.py`
- Stores the originating SAT shipping operation on the picking
- Exposes the related repair on the picking for traceability
- Marks the SAT operation as done when the linked picking is validated
- Preserves the special pickup case where a picking may exist before the MRW
  shipment is requested

### `models/account_payment_register.py`
- Intercepts the customer payment wizard
- Detects the relevant invoice after payment
- Resolves the related repair
- Opens the delivery confirmation wizard when appropriate

### `models/account_move.py`
- Provides a thin bridge method to obtain SAT repairs from an invoice

### `wizard/repair_delivery_wizard.py`
- Confirms whether the paid repair should be marked as delivered

## Current Boundary

This module should own:
- delivery-specific state and actions
- payment-to-delivery orchestration
- delivery UI and filters
- repair-level logistics orchestration through `wex.repair.shipping.operation`
- the Wexplay-specific bridge between repair pickups and `mrw_shipping_connector`

This module should not become the general owner of:
- budget workflow rules
- stock-location mapping rules that belong to the workflow module
- broad discuss/channel strategy for the whole SAT ecosystem
- generic carrier logic that belongs to `delivery.carrier`
- MRW SOAP mapping/client details that belong to `mrw_shipping_connector`

## MRW Integration Summary

- Delivery operations reuse standard Odoo carrier behavior on `stock.picking`.
- Pickup operations currently support automatic carrier sending only for MRW.
- The MRW pickup path creates a `mrw.shipping.shipment` with
  `movement_type="pickup"`, sends it through the generic connector, retrieves
  the label when available, and stores the resulting MRW references on the SAT
  operation.
- If an incoming picking exists for that pickup, the module links the same
  `mrw.shipping.shipment` to the picking so MRW audit, label, and stock receipt
  stay connected.
- `repair.order` exposes the tracking link directly from the `Envíos` tab so
  logistics follow-up does not require opening the technical MRW shipment
  record.

## Known Architectural Debt

- Delivery state change still relies on workflow-side location synchronization.
- Delivery accepts both operationally finalized repairs and historical cancelled
  repairs that are physically in the pending-pickup location, but new
  not-repairable diagnostics should be finalized through workflow instead of
  being cancelled.
- Older test databases may still contain obsolete direct logistics columns on
  `repair.order`; the active model no longer uses the old single-slot delivery
  fields such as `x_delivery_picking_id` or `x_shipping_flow`.

## Notes For Next Phases

- Decide when the channel-name fallback can be removed after production settings are configured.
- Consider making delivery-to-location synchronization more explicit if the current indirection becomes a maintenance issue.
- Add tests around one-pickup/one-delivery constraints and picking creation.
- Add tests around MRW tracking link exposure in repair shipping operations.
