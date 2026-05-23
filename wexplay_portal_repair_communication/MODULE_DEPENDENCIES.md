# Module Dependencies - Wexplay Portal Repair Communication

## Direct dependencies

| Module | Why it is required |
| --- | --- |
| `mail` | Required to store messages, schedule activities, reuse Odoo messaging surfaces and bridge the technician-side chat window. |
| `hr` | Required to resolve the employee manager fallback when the SAT responsible user is missing. |
| `portal` | Required for authenticated portal access and portal user flows. |
| `website` | Required because the Wexplay B2B portal stack depends on website rendering, portal templates and website routes. |
| `wexplay_portal` | Required to project the SAT conversation into the existing B2B portal repair detail. |
| `wexplay_repair` | Required because `repair.order` is the functional owner record of every conversation. |
| `wexplay_portal_repair_workflow` | Required for workflow state access used in conversation write-access rules. |
| `wexplay_repair_warranty` | Required to determine whether the SAT remains writable from portal based on SAT-active and warranty rules. |

## Runtime library dependencies

| Library | Why it is required |
| --- | --- |
| `pytz` | Required by the business hours SLA algorithm to convert UTC datetimes to Europe/Madrid and iterate over business windows correctly. Available in all standard Odoo 18 environments; no extra install needed. |

## Internal technical couplings

| Coupling | Why it matters |
| --- | --- |
| `repair.order.user_id` | Current SAT responsible drives the main routing destination. |
| `hr.employee.parent_id` or equivalent manager relation | Manager fallback must remain explicit and testable, not inferred in scattered places. |
| `repair.order._is_portal_repair_active()` | Customer write access and some contextual messages depend on the active SAT rule exposed by the repair/portal stack. |
| `repair.order.x_is_any_warranty_valid` | Customer write access depends on warranty validity when the SAT is no longer active. |
| `repair.order.internal_notes` and SAT-specific note fields | Technician-side summary must sanitize and project useful notes without leaking raw HTML editor markup. |
| `commercial_partner_id` security boundary | Portal conversation access must stay aligned with the same security rule already used by `wexplay_portal`. |
| `discuss.channel` | Used as technician-side operational surface, but must not become the functional source of truth. |
| `mail.activity.schedule` | Used from the technician chat context to create pending follow-up activities on the SAT, and automatically from the SLA cron when a deadline is breached. |
| `ir.cron` | The SLA checker runs as a scheduled action every 15 minutes. Any change to the cron interval or the `_cron_check_sla` method signature must be coordinated with the XML data file `data/ir_cron_sla.xml`. |

## Architectural rules

- `wexplay_portal_repair_communication` owns the conversation logic.
- `wexplay_portal` only exposes the conversation on the customer-facing portal.
- `wexplay_repair` only exposes the conversation on the backend SAT form.
- Warranty logic must stay in the warranty/repair stack.
- Routing and fallback decisions must stay in Python and must not depend only on XML or frontend code.
- Portal popup behavior should remain conservative unless a change clearly improves UX without reducing stability.

## Known dependency risks

- Missing employee linkage for the responsible user may make the manager fallback ambiguous.
- Over-coupling to mail UI internals could make upgrades more fragile than necessary.
- If warranty rules evolve, portal write access for old SAT conversations may change and should be reviewed together.
- Patching `mail.ChatWindow` requires care because upstream Owl templates and action ids can change between versions.
- Real-time improvements based on bus/websocket would increase coupling with frontend messaging services and should be introduced carefully.
- The SLA business hours constants (`_SLA_WINDOWS`, `_SLA_TZ`, `_SLA_DAYS`) are hardcoded in `portal_repair_conversation.py`. If working hours change, the constants must be updated manually and the cron re-triggered to recompute existing deadlines.
- `pytz` is available in all Odoo 18 environments but is not declared as an explicit Python package dependency. If ever running outside a standard Odoo environment, ensure `pytz` is installed.
