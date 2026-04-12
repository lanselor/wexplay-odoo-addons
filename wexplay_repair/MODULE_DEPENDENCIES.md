# Wexplay Repair Module Dependencies

## Hard Addon Dependencies

| Addon | Why it is required |
| --- | --- |
| `repair` | Base model `repair.order`, views and actions extended by the module |
| `repair_scheduled_date_calendar_view` | The module inherits `view_repair_order_form_inherit_duration` |
| `dms` | SAT DMS storage and directory fields, plus directory helper methods |
| `stock` | SAT locations are stored on `stock.location` and used in repair flows |
| `mail` | Tracking fields on `repair.order` and mail-thread behavior inherited from repair |
| `hr` | Reception employee is stored as `hr.employee` |
| `account` | Invoice extension and SAT invoice report |
| `sale` | SAT totals and invoice-to-repair relation rely on sale orders |
| `web` | Custom JS/XML assets and custom backend view type registration |

## Current Direct Integrations

| Integration | Type | Current status |
| --- | --- | --- |
| `wexplay_sat_print` | Functional integration | Used directly by QZ client actions from `account.move`, but not hardened as a manifest dependency in this phase |

## XML/View Dependencies

- Inherits `repair.view_repair_order_form`
- Inherits `repair.view_repair_order_tree`
- Inherits `repair.view_repair_order_form_filter`
- Inherits `repair_scheduled_date_calendar_view.view_repair_order_form_inherit_duration`
- Inherits `account.view_move_form`
- Inherits `base.res_config_settings_view_form`

## External Python Dependencies

No extra Python library is declared in this phase.

Note:
- The SAT base module does not import third-party libraries outside the standard Odoo/Python environment.
- Optional review remains pending for the broader print stack.

## Risks If Dependencies Are Missing

- Missing `repair_scheduled_date_calendar_view` breaks the duration cleanup view inheritance.
- Missing `dms` breaks both settings fields and SAT directory helpers.
- Missing `web` breaks custom backend assets and `repair_card` behavior.
- Missing `wexplay_sat_print` does not block install today, but QZ print actions can fail at runtime.
