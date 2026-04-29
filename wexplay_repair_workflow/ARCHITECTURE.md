# Wexplay Repair Workflow Architecture

## Purpose

`wexplay_repair_workflow` extends the SAT base repair flow with budget and internal movement rules.

It adds:
- budget state lifecycle
- timestamps for budget start and resolution
- waiting-spare timestamp
- SAT location synchronization based on budget stage and repair state
- glue-desk finish decision for mobile/tablet repairs

## Current Responsibilities

### `models/repair_order.py`
- Defines `x_budget_stage`
- Validates budget transitions
- Decides target SAT locations
- Synchronizes `product_location_src_id`
- Protects standard repair actions
- Opens the glue-choice and waiting-spare wizards
- Adjusts workflow state side effects in `write()`

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

The XML layer should stay limited to visibility and access to actions.

## Known Architectural Debt

- `write()` still carries too much workflow coupling.
- XML button invisibility still duplicates part of the Python business rules.
- Location synchronization is split across several helpers and post-write behavior.

## `write()` Side-Effect Contract

`write()` in this module owns only workflow side effects caused by `state` changes:
- `cancel` marks the budget as rejected and syncs to the rejected budget location.
- `under_repair`, `done` and `delivered` sync `product_location_src_id` from the configured state location.
- The context flag `skip_repair_state_location_sync` intentionally bypasses state-location synchronization when a caller must set the final location itself in the same business action.

Downstream modules may call public actions such as `action_budget_accept()` or `action_mark_delivered()`, but should avoid duplicating workflow location rules.

## Notes For Next Phases

- Reduce duplicated XML conditions by relying more clearly on Python helpers.
- Make `write()` thinner and move workflow side effects into named helpers.
- Clarify the contract between budget acceptance, repair confirmation and downstream delivery behavior.
