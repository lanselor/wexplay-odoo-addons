# Wex Print Core Architecture

## Purpose

`wex_print_core` is the shared technical printing module for the Wexplay stack.

It centralizes:
- QZ Tray integration
- shared printer configuration
- print routing
- print traces
- profiles and assignments
- printer diagnostics snapshots

It must stay free from product-only or SAT-only business logic.

## Current Responsibilities

### QZ integration
- Loads and manages QZ Tray client-side integration
- Resolves printer settings with this priority:
  - user override
  - company fallback
- Executes PDF printing through QZ

### Routing
- Provides the shared print router
- Supports:
  - `legacy`
  - `hybrid`
  - `new_only`
- `Hybrid` can execute the new path only when an assignment explicitly enables `Pilot new resolution`
- If the new path fails in `Hybrid`, it falls back to `legacy`

### Profiles and assignments
- `wex.print.profile`
  - stores printer target and advanced output options
  - currently includes `duplex_mode` for A4
- `wex.print.assignment`
  - links document types to profiles
  - can enable `Pilot new resolution`

### Tracing
- `wex.print.trace` stores technical evidence of:
  - requested mode
  - execution mode
  - resolution source
  - next profile/printer
  - duplex mode
  - pilot activation
  - fallback behavior

### Diagnostics
- `wex.print.device.snapshot` stores snapshots loaded from `qz.printers.details()`
- This is meant for investigation and capability discovery, not for changing the live print flow

## Validated Production State

The following has been validated in production:
- `Hybrid` mode
- product label printing
- SAT label printing
- SAT ticket printing
- SAT A4 printing
- A4 duplex through `Double-sided (long edge)`
- rollback back to `legacy`

## Production Configuration Baseline

### Active profiles
- `A4 Prod`
- `Product Label Prod`
- `SAT Accessory Label Prod`
- `SAT Main Label Prod`
- `SAT Ticket Prod`

### Active assignments with pilot enabled
- `Product Label Default`
- `SAT Main Label Default`
- `SAT Accessory Label Default`
- `SAT Ticket Default`
- `SAT A4 Default`

### Validated printers
- labels: `Brother QL-710W`
- thermal: `PRP-300 (Copiar 1)`
- A4: `Brother MFC-L2800DW Printer`

## Resolution Priority

Current legacy-compatible printer resolution is:
- user printer override on `res.users`
- company-level fallback from shared QZ settings

This keeps the old configuration valid while allowing progressive per-user rollout.

## Boundaries

This module should contain:
- shared QZ helpers
- shared settings
- routing and fallback logic
- diagnostics and traces
- technical profile/assignment models

This module should not contain:
- product report definitions
- SAT-only QWeb reports
- repair-specific business calculations

## Known Debt

- Legacy printer resolution still relies on company config parameters keyed by `kind`
- Report selection is still partially hardcoded by report name
- There is still no formal print variant layer separating:
  - logical document
  - QWeb variant
  - physical medium/size

## Next Recommended Direction

Do not open the print-variant refactor until hybrid behavior is considered stable enough.

Once resumed, the next serious architectural step should be:
- introduce print variants
- decouple `document_type` from hardcoded `report_name`
- keep coexistence with legacy during migration
