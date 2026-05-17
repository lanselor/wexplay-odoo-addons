# Wexplay Repair Workflow Architecture

## Purpose

`wexplay_repair_workflow` extends the SAT base repair flow with budget and internal movement rules.

It adds:
- budget state lifecycle
- timestamps for budget start and resolution
- waiting-spare timestamp
- SAT location synchronization based on budget stage and repair state
- sale-order confirmation/cancellation rules tied to budget acceptance/rejection
- glue-desk finish decision for mobile/tablet repairs
- technical not-repairable diagnosis outcome and diagnostic closure

## Current Responsibilities

### `models/repair_order.py`
- Defines `x_budget_stage`
- Validates budget transitions
- Validates whether the linked quotation allows accepting or rejecting the budget
- Decides target SAT locations
- Synchronizes `product_location_src_id`
- Protects standard repair actions
- Opens the glue-choice and waiting-spare wizards
- Opens confirmation wizards for budget actions that need explicit operator intent
- Adjusts workflow state side effects in `write()`
- Marks repairs as not repairable when diagnosis determines there is no viable repair
- Finalizes not-repairable diagnostics into Odoo `done` without using `cancel`

### `wizard/finish_repair_glue_choice_wizard.py`
- Finalizes the repair and chooses final SAT location

### `wizard/waiting_spare_confirm_wizard.py`
- Confirms transition to waiting-spare when there are no spare moves

## Single Source Of Truth

Business rules should live in Python here, especially for:
- allowed budget transitions
- location mapping by budget stage
- location mapping by repair state
- when a wizard must be opened
- how a linked `sale.order` must behave when a budget is accepted or rejected
- the distinction between customer rejection and internal not-repairable diagnosis

The XML layer should stay limited to visibility and access to actions.

## Not Repairable Contract

`not_repairable` is a technical diagnosis result, not an Odoo cancellation.

When a repair is marked as not repairable:
- `x_budget_stage` is set to `not_repairable`.
- `x_budget_resolved_at` is updated.
- Odoo `state` is not changed.
- `product_location_src_id` is not changed.

When a not-repairable diagnosis is complete, `action_finish_not_repairable_diagnosis()`
sets Odoo `state` to `done` and moves the device to the configured `Finalizada`
location. The technical state remains `done`, but the SAT base module labels it
as `Finalizado`.

This keeps `cancel` reserved for administrative cancellations where the SAT
work should not be treated as completed or billable. Physical pickup and final
delivery remain owned by the normal delivery flow.

The OCA `repair_picking_after_done` transfer button remains available for normal
finalized repairs, but is hidden when `x_budget_stage == not_repairable` because
that diagnostic closure does not represent repaired stock moves.

## Known Architectural Debt

- `write()` still carries too much workflow coupling.
- XML button invisibility still duplicates part of the Python business rules.
- Location synchronization is split across several helpers and post-write behavior.

## `write()` Side-Effect Contract

`write()` in this module owns only workflow side effects caused by `state` changes:
- `cancel` marks the budget as rejected and syncs to the rejected budget location,
  except when the budget is already `not_repairable`, because that technical
  diagnosis must remain traceable.
- `under_repair`, `done` and `delivered` sync `product_location_src_id` from the configured state location.
- The context flag `skip_repair_state_location_sync` intentionally bypasses state-location synchronization when a caller must set the final location itself in the same business action.

Downstream modules may call public actions such as `action_budget_accept()` or `action_mark_delivered()`, but should avoid duplicating workflow location rules.

## Budget And Quotation Contract

- Moving to `waiting_customer` may happen without quotation, but only after an
  explicit operator confirmation.
- Accepting a budget requires a linked quotation.
- If the linked quotation is in `draft` or `sent`, budget acceptance confirms
  the quotation and confirms the repair through Odoo `action_validate()`.
- If the linked quotation is already in `sale`, the workflow can still mark the
  budget as accepted without reconfirming it.
- Rejecting a budget requires explicit operator confirmation and cancels the
  linked quotation when it is still cancelable (`draft` or `sent`).

## Notes For Next Phases

- Reduce duplicated XML conditions by relying more clearly on Python helpers.
- Make `write()` thinner and move workflow side effects into named helpers.
- Clarify the contract between budget acceptance, repair confirmation and downstream delivery behavior.
