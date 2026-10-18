# Wexplay Repair Decision Log

## 2026-10-17 Additional inspection device types

- Add front/back schemes for all-in-one, Mini PC, monitor and smartwatch, using
  the existing coordinate format, single-face navigation and confirmation rules.
- Define supported types once in Python and expose face-label metadata through
  get_device_inspection_diagrams after checking repair read access. The modal reads
  the catalog rather than maintaining a second list of supported types in JS.
- Add two specific conditions per new type. Preserve the existing common catalog
  and its identifiers; do not migrate or rewrite historical inspections.

## 2026-10-17 Inspection visual alignment

- Reuse the SAT palette, base panels and shared DeviceTypePicker presentation
  component in the modal. Keep confirmation and draft persistence in their existing
  parents, avoiding duplicate icon catalogs or device selection interfaces.
- Increase the heading action to 42 x 42px. A green dot means there are drawn
  strokes in either face, including rear-only evidence; tags alone do not count.
  Derive this state from the existing JSON rather than adding a stored flag.

## 2026-10-17 Internal device reception inspection

- Keep the existing description as free text and move its ownership from consent
  to the SAT base using the same field and SQL column. No data migration or reverse
  dependency is needed; deploy by updating both modules together.
- Keep damage selections separate from text. Display subtle tags below the field.
- Require a device type for description/inspection edits, without imposing a
  global required field that blocks unrelated legacy repair operations.
- Store bounded editable stroke coordinates on the repair and use six static SVG
  backgrounds. Do not create DMS documents or image attachments for drawing data.
- Use a native Dialog draft and parent form Save/Discard. No independent modal RPC
  save that could overwrite other unsaved repair edits.
- Restrict new inspection fields and condition catalog to internal users. Keep the
  existing description's consent use unchanged. No drawings or tags in portal,
  reports or signed documents during this iteration.
- Initial decision (superseded by the iteration below): block type changes until
  drawings or incompatible tags are explicitly removed.

### Iteration: one visible face and confirmed type reset

- Show one enlarged face at a time; face buttons indicate existing marks. Undo and
  clear operate on the active face. Stored front/back coordinates remain unchanged.
- Replace the previous blocking behaviour with a shared confirmation in modal and
  main form type selectors, only if there are marks or selected conditions.
- Confirmation resets both faces and all conditions, including common conditions;
  free text is preserved. Cancel/Escape/close preserve current evidence and type.
- Type changes without evidence require no confirmation. Modal Cancel still
  discards all modal changes, including confirmed resets.
- Python resets old evidence only on actual type changes; explicit new inspection
  data may accompany the new type in the same write. No reset when the type is
  unchanged, including mixed recordsets. No context flags or new schema are needed.

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

### 2026-10-17 — Console formats belong to internal inspection

Keep the repair classified as Consola. Offer Sobremesa, Portátil clásica and PC de
mano as illustrated cards, with no model examples or descriptive subtitles.
Persist the selected format in validated inspection JSON, including empty drawings,
rather than adding a repair subtype or model. Changing format resets both drawings
only after confirmation when marks exist; tags and free text remain. Cancelling
the modal discards the full draft. Existing non-console payloads stay compatible.
This represents different physical silhouettes without changing repair taxonomy.

### 2026-10-17 — Include reception inspection in the technical report

Decision: Include existing description, tags and annotated diagrams automatically
in “Estado del dispositivo en recepción” before photographs. No content means no
section; no strokes means no diagrams; any marked face means both labelled faces.
Recipients may see this content, explicitly approved after the earlier internal-only
scope. Reuse the same PDF, DMS file and report permissions. Compose local SVGs in
Python from validated coordinates and trusted device metadata; QWeb handles layout.
No new model, stored image, public route, dependency or automatic regeneration on
inspection edits. Long text flows and photographs always begin on their own page.

### 2026-10-17 — Share inspection preparation with reception signatures

Move SVG composition from report-specific code into the shared inspection model.
Keep the report wrapper and use the same normalized coordinates for signature
snapshots. wex_consent owns capture/freeze/signing and DMS SIGNATURES storage;
wexplay_repair owns the device inspection and current technical report.

## 2026-10-17 — Consolidación documental y validación final

El usuario confirma que el conjunto funciona. Se consolida la documentación de
inspección, informe técnico, firma de recepción y portal, conservando el historial
y distinguiendo datos actuales, instantáneas firmadas y exposición autorizada.
Referencia: [guía consolidada](../wexplay_repair/docs/DEVICE_INSPECTION_GUIDE.md).
Esta revisión solo modifica documentación; no cambia código, versiones, permisos,
configuración ni datos funcionales, ni atribuye un despliegue de producción al agente.
