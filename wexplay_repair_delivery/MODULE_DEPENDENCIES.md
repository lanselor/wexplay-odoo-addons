# Wexplay Repair Delivery Module Dependencies

## Hard Addon Dependencies

| Addon | Why it is required |
| --- | --- |
| `repair` | Base `repair.order` model and inherited search/form views |
| `account` | Extends invoice and payment register flows |
| `stock` | Delivery readiness depends on SAT stock locations |
| `mail` | Uses `discuss.channel`, `mail.mt_comment` and channel message posting |
| `wexplay_repair` | Reuses SAT base fields, helpers and company SAT settings |
| `wexplay_repair_workflow` | Depends on workflow location behavior and inherits its repair form extension |

## XML/View Dependencies

- Inherits `repair.view_repair_order_form_filter`
- Inherits `wexplay_repair_workflow.view_repair_order_form_wexplay_budget_workflow`

## Functional Couplings

| Coupling | Why it matters |
| --- | --- |
| `repair.order._get_sat_repairs()` from `wexplay_repair` via invoice flow | Delivery resolution ultimately relies on the SAT invoice-to-repair relation |
| `company_id.x_repair_state_location_done_id` and `x_repair_state_location_delivered_id` | Pending-delivery logic and delivery completion depend on these locations |
| Workflow module location synchronization | Marking a repair as delivered relies on the broader repair workflow to keep locations aligned |
| `discuss.channel` named SAT channel | Notification logic assumes a channel with one of the configured names exists |

## External Python Dependencies

No extra dependency is declared in this phase.

Note:
- `markupsafe` is imported directly in module code, but is currently assumed to be available in the Odoo runtime environment.
- If the deployment policy requires explicit declaration of bundled Python libraries, this should be revisited in a later hardening phase.

## Risks If Dependencies Are Missing

- Missing `mail` breaks SAT discuss channel lookup and posting.
- Missing workflow module breaks the inherited form view and delivery assumptions.
- Missing SAT channel does not block install, but the notification is silently degraded to logs.
