# Wexplay Repair Architecture

## Purpose

`wexplay_repair` is the SAT base module for the current Wexplay repair stack.

It extends `repair.order` with:
- device identification data
- customer reception data
- SAT-oriented search helpers
- SAT settings on company/configuration
- DMS helper methods for SAT folders
- invoice/report integrations used by the SAT workflow
- a custom operational card view for repair orders

This module is currently both:
- the functional base for SAT repair operations
- the technical base consumed by `wexplay_repair_workflow` and `wexplay_repair_delivery`

## Current Responsibilities

### `models/repair_order.py`
- Adds SAT fields to `repair.order`
- Computes customer summary and SAT totals
- Adds phone/mobile search helper
- Handles basic device-history navigation

### `models/repair_order_dms.py`
- Provides DMS directory helper methods for SAT
- Centralizes SAT folder naming and DMS path resolution

### `models/res_company.py`
- Stores SAT workflow locations per company
- Stores SAT DMS storage and root directory configuration

### `models/res_config_settings.py`
- Exposes SAT company settings in the UI

### `models/account_move.py`
- Resolves SAT repairs linked to an invoice
- Exposes SAT invoice print actions

### `models/ir_ui_view.py` and `models/ir_actions_act_window.py`
- Registers the custom `repair_card` view type
- Makes the repair card view the default entry view for repair orders

### `views/repair_order_views.xml`
- Applies the main SAT form customization

## Boundaries

This module should remain the base SAT layer.

It should contain:
- stable SAT fields
- shared helpers reused by other repair modules
- company settings needed by the SAT stack
- base UI customizations that are truly common

It should not keep growing with:
- budget-state orchestration
- delivery-specific rules
- payment-triggered behavior
- channel notification rules

Those belong in extender modules.

## Known Architectural Debt

- QZ printing actions reference `wexplay_sat_print` client actions directly.
- The main repair form inheritance is large and therefore more sensitive to upstream view changes.
- There are historical backup files in the module tree that should not be treated as live source.
- The SAT invoice report still resolves repairs directly in QWeb instead of receiving fully prepared values.

## Notes For Next Phases

- Decide whether QZ printing is a hard dependency or an optional integration.
- Revisit the SAT invoice report so repair resolution is prepared in Python.
- Reduce fragility in the large form inheritance only when there is a concrete business reason to touch it.
