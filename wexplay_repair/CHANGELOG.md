# Changelog

## 18.0.1.5.1 — 2026-10-17

- Move document inspection preparation and SVG composition to the shared inspection model so technical reports and reception signatures reuse the same geometry. Retain report context wrapper and existing report output.
- Validate 47 combined repair/consent tests and actual PDF/signature integration.

## 18.0.1.5.0 — 2026-10-17

- Include reception description, damage tags and annotated diagrams on a conditional new report page before photos. Any marked face includes both labelled faces; empty inspection adds no section.
- Compose trusted SVGs and saved strokes server-side, including all console formats, without new dependencies or stored images.
- Keep the same DMS archive, permissions and generation lifecycle. Long descriptions flow without clipping.
- Pass 26 core tests and verify six rendered PDF scenarios, pagination and DMS binary roundtrips in an isolated integration database.

### 2026-10-17 — Compact console format cards

- Reduce format thumbnails to 72px height (56px on narrow or short screens), cap their width and tighten card spacing on small screens. The drawing board and inspection behaviour remain unchanged.

## 18.0.1.4.0 — 2026-10-17

- Add illustrated Sobremesa, Portátil clásica and PC de mano cards inside console inspection, with six front/back SVG assets.
- Persist console format in validated inspection JSON without adding a repair subtype. Require a format before applying console inspection.
- Confirm format changes when drawings exist, clear both faces and preserve tags/text. Whole-modal cancellation discards the draft.
- Validate all three formats, empty drawings and invalid payloads in 20 passing inspection tests.

## 18.0.1.3.0 — 2026-10-17

- Add front/back SVG schemes for Todo en Uno, Mini PC, monitor and smartwatch.
- Add type-specific stand, ports, housing, strap and crown/button conditions.
- Centralize supported diagram types in Python and provide face-label metadata to
  the modal, keeping validation and display consistent.
- Keep existing coordinates, single-face tools, confirmed resets and green mark
  indicator. No schema change or rewrite of historical inspections.

## 18.0.1.2.1 — 2026-10-17

- Align inspection panels with the SAT form palette, borders and typography.
- Reuse one visual DeviceTypePicker component in form and modal, preserving the
  existing confirmation and local draft behaviour.
- Enlarge the heading action to 42 x 42px and show a green dot for drawn marks in
  either face. Conditions alone do not activate it. No schema or business changes.

## 18.0.1.2.0 — 2026-10-17

- Show one enlarged face at a time, with Frontal/Trasera buttons (device-specific
  labels for laptops), mark indicators and face-local undo/clear.
- Both device-type selectors confirm before clearing existing marks and tags.
  Empty inspections change directly, and free text is always preserved.
- Confirmed changes clear both faces and all conditions, immediately loading the
  new device. Modal Cancel still discards its whole draft.
- Python resets evidence on actual type changes while preserving explicitly
  submitted new inspection data and unchanged records in multi-record writes.

## 2026-10-17 — Inspection field layout refinement

- Restored full-width device description, matching delivered accessories.
- Moved the inspection action to the heading's right edge as an icon-only button
  with tooltip and accessible label. Tags and inspection behaviour are unchanged.

## 18.0.1.1.0 — 2026-10-17

- Added internal reception inspection: native dialog, mobile/tablet/laptop generic
  front/back silhouettes, freehand red pencil, undo and clear.
- Added controlled damage selections displayed as subtle tags below description.
- Kept the existing description field and moved its declaration from wex_consent
  into the SAT base. Update both modules together; no column is renamed or deleted.
- Added server-side type, condition compatibility and stroke bounds validation.
- Kept unrelated legacy repairs editable and new inspection data internal only.
- No document generation, DMS image export, portal, workflow or delivery changes.
- Decisions and validation: docs/SPEC_DEVICE_INSPECTION.md,
  docs/PLAN_DEVICE_INSPECTION.md and docs/TEST_DEVICE_INSPECTION.md.

### 2026-10-17 — Desktop console silhouette correction

- Replace the compact-PC-like desktop console views with a generic horizontal console inspired by Series S, using a circular cooling grille, power control and console rear ports. Keep the same asset paths, viewBox and compact selector sizing.

## 2026-10-17 — Consolidación documental y validación final

El usuario confirma que el conjunto funciona. Se consolida la documentación de
inspección, informe técnico, firma de recepción y portal, conservando el historial
y distinguiendo datos actuales, instantáneas firmadas y exposición autorizada.
Referencia: [guía consolidada](../wexplay_repair/docs/DEVICE_INSPECTION_GUIDE.md).
Esta revisión solo modifica documentación; no cambia código, versiones, permisos,
configuración ni datos funcionales, ni atribuye un despliegue de producción al agente.
