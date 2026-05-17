# Wexplay Repair Workflow Module Dependencies

## Hard Addon Dependencies

| Addon | Why it is required |
| --- | --- |
| `repair` | Base `repair.order` model and inherited form view |
| `mail` | Tracking fields on workflow timestamps and budget stage |
| `wexplay_repair` | Provides SAT base fields, SAT settings and shared repair extension context |
| `repair_picking_after_done` | Provides the OCA transfer button that must be hidden for not-repairable diagnostic closures |

## XML/View Dependencies

- Inherits `repair.view_repair_order_form`
- Inherits `repair_picking_after_done.repair_type_form_inherit`
- Uses wizard views defined inside the module itself

## Functional Couplings

| Coupling | Why it matters |
| --- | --- |
| `company_id.x_repair_*` fields from `wexplay_repair` | Budget and repair state location mapping depends on these settings |
| `repair.order.x_device_type` from `wexplay_repair` | Glue-desk finish decision depends on the SAT device type |
| `repair.order.move_ids` from core repair/stock flow | Waiting-spare confirmation checks whether spare moves exist |

## Risks If Dependencies Are Missing

- Missing `wexplay_repair` breaks company settings, SAT fields and workflow assumptions.
- Missing configured SAT locations does not block install, but blocks workflow actions at runtime with user errors.
