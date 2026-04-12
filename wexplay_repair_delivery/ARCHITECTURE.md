# Wexplay Repair Delivery Architecture

## Purpose

`wexplay_repair_delivery` adds the delivery stage on top of the SAT repair stack.

It currently covers:
- extra `delivered` state on `repair.order`
- pending-delivery filter logic
- delivery confirmation wizard after payment
- delivery action from repair order
- SAT internal notification when the repair reaches the expected point of readiness

## Current Responsibilities

### `models/repair_order.py`
- Adds the `delivered` state
- Computes delivery helper fields
- Validates whether a repair can be marked as delivered
- Posts SAT channel notifications
- Watches state transitions in `write()`

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

This module should not become the general owner of:
- budget workflow rules
- stock-location mapping rules that belong to the workflow module
- broad discuss/channel strategy for the whole SAT ecosystem

## Known Architectural Debt

- The notification trigger is inferred from `state == confirmed`, which is less explicit than a dedicated business event.
- `x_pending_delivery_filter` still uses a Python-side filtered search instead of a more direct persisted criterion.
- Delivery state change still relies on workflow-side location synchronization.

## Notes For Next Phases

- Revisit whether SAT notification should be triggered by a more explicit budget event.
- Decide if pending-delivery detection should remain dynamic or gain a more query-friendly persistence strategy.
- Consider making delivery-to-location synchronization more explicit if the current indirection becomes a maintenance issue.
