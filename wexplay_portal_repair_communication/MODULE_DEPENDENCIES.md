# Module Dependencies - Wexplay Portal Repair Communication

## Direct dependencies

| Module | Why it is required |
| --- | --- |
| `mail` | Required to reuse Odoo messaging surfaces and mail-related infrastructure for technician-side conversation projection. |
| `hr` | Required to resolve the employee manager fallback when the SAT responsible user is missing. |
| `portal` | Required for authenticated portal access and portal user flows. |
| `website` | Required because the Wexplay B2B portal stack depends on website rendering and routes. |
| `wexplay_portal` | Required to project the SAT conversation into the existing B2B portal repair detail. |
| `wexplay_repair` | Required because `repair.order` is the functional owner record of every conversation. |
| `wexplay_repair_warranty` | Required to determine whether the SAT remains active for customer replies based on warranty rules. |

## Functional couplings to watch

| Coupling | Why it matters |
| --- | --- |
| `repair.order.user_id` | Current SAT responsible drives the main routing destination. |
| `hr.employee.parent_id` or equivalent manager relation | Manager fallback must remain explicit and testable, not inferred in scattered places. |
| Warranty-active SAT definition | Customer write access depends on warranty validity, so the communication module should not redefine that rule locally. |
| Portal access by `commercial_partner_id` | Conversation access must stay aligned with the same security boundary already used by `wexplay_portal`. |
| Odoo conversation UI | Technician chat must feel native, but the module must avoid turning that UI into the functional source of truth. |

## Architectural rules

- `wexplay_portal_repair_communication` owns the conversation logic.
- `wexplay_portal` only exposes the conversation on the customer-facing portal.
- `wexplay_repair` only exposes the conversation on the backend SAT form.
- Warranty logic must stay in the warranty module.
- Routing and fallback decisions must stay in Python and must not depend only on XML or frontend code.

## Known dependency risks

- Missing employee linkage for the responsible user may make the manager fallback ambiguous.
- Over-coupling to mail UI internals could make upgrades more fragile than necessary.
- If warranty rules evolve, portal write access for old SAT conversations may change and should be reviewed together.
