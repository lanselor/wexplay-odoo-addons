# Wexplay Repair Decision Log

## 2026-04 Phase 0-1

### Keep `wexplay_repair` as SAT base module

Decision:
- Do not split the module yet.

Reason:
- `wexplay_repair_workflow` and `wexplay_repair_delivery` already depend on this module as their functional base.
- A structural split now would increase migration and regression risk.

### Make manifests more explicit, but avoid forced ecosystem reshaping

Decision:
- Clean obvious manifest issues now.
- Do not force new addon installation paths in this phase unless the dependency is unquestionably hard and safe to enforce.

Reason:
- The current goal is stabilization, not reorganization.
- Forcing a new dependency too early may break update paths in active databases.

### Keep QZ printing as documented latent coupling for now

Decision:
- Document `wexplay_sat_print` as a runtime integration not yet hardened in `depends`.

Reason:
- `wexplay_repair` references QZ client action tags directly.
- That coupling is real.
- Hardening it in `depends` needs a conscious product decision because it changes installation requirements.

### DMS remains in the base module for now

Decision:
- Keep SAT DMS helpers in `wexplay_repair` during this phase.

Reason:
- They are already consumed as shared SAT infrastructure.
- Moving them now would mix architectural cleanup with functional refactor.

### Sequence hook is accepted as technical debt, not as target behavior

Decision:
- Leave `post_init_hook` unchanged in this phase.

Reason:
- It is installation-sensitive.
- The current phase should not alter setup behavior.
- It is explicitly tracked as debt for a later hardening phase.

## 2026-08 Technical service reports

### Treat the SAT report as technical documentation

Decision:
- Redesign the service report from the existing QWeb base instead of creating a
  second document model.
- Remove economic totals and prices from the report while keeping material and
  services as technical evidence.

Reason:
- A service report should explain what was received, found and carried out.
- Financial information is already owned by quotes, proformas and invoices.

### Keep the report PDF in DMS, but use the native mail composer

Decision:
- The internal SAT report remains archived as the current PDF in DMS.
- Sending the report opens Odoo's standard email composer with a temporary
  attachment generated from that archived PDF.

Reason:
- The sent PDF must be identical to the document available for download.
- A temporary mail attachment avoids duplicate DMS documents while preserving
  the normal email and chatter traceability of Odoo.

### Separate complementary report notes from repair notes

Decision:
- Store report-only text in `x_sat_report_notes` and expose it through a
  compact action in the document card.
- Regenerate the archived report automatically when those notes are saved.

Reason:
- Legal, insurance or client-specific clarifications must not pollute the
  technician's normal repair notes.
- The field is marginal to daily SAT work and should not occupy permanent space
  in the main repair form.

### Separate report permission from generic DMS permission

Decision:
- Create two explicit SAT report groups: consult/download, and manage.
- Authorize actions in Python and provide report download through a controlled
  route after confirming access to the repair.

Reason:
- A TPV or restricted internal user may need a specific report capability
  without browsing or modifying SAT DMS folders.
- View-level visibility is insufficient because actions and file URLs must also
  resist direct invocation.
