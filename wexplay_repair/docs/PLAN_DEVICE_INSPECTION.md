# Architecture and execution plan — Device inspection

This file preserves approved implementation stages. The final integrated behaviour
and user confirmation are in [DEVICE_INSPECTION_GUIDE.md](DEVICE_INSPECTION_GUIDE.md).
Early exclusions below describe their original phase, not the final scope.

## Additional device types — 2026-10-17

Approved in chat: Todo en Uno, Mini PC, monitor and smartwatch, using the current
inspection workflow and data format. No fields/models or dependencies are added.

1. device_constants.py: DEVICE_INSPECTION_TYPES is the single catalog. In
   repair_order_inspection.py, get_device_inspection_diagrams checks read access
   and returns face labels; mark validation consumes the same catalog.
2. repair_device_inspection_field.js: load diagram metadata and conditions in
   parallel; use metadata in hasDiagram and viewLabel, removing the JS type list.
3. static/src/img/device_inspection/: eight additional 320 x 400 SVG resources,
   one front and one back for all_in_one, mini_pc, monitor and smartwatch.
4. device_condition_data.xml: two additional controlled conditions per new type,
   preserving all historical XML identifiers and common conditions.
5. Tests: save/reload both faces and a specific tag for each new type, reject
   incompatible tags and deny portal diagram metadata access. Validate all fourteen
   SVG paths and visually inspect the eight new faces in the isolated test system.
6. Version 18.0.1.3.0, architecture, decisions, test report, project log and ficha.

## Visual alignment iteration — 2026-10-17

Approved in chat: reuse repair.order styling, its device picker, and enlarge the
heading action with a green mark indicator. Existing persistence is unchanged.

- repair_device_type_picker_field.js/xml: extract DeviceTypePicker presentation
  (same icons/options) and keep the ORM field wrapper responsible for form updates.
- repair_device_inspection_field.js/xml: use the shared picker in the local draft;
  changeDeviceType accepts a selected value. hasInspectionMarks derives the dot
  from both stroke arrays, without a new database field.
- repair_order_form.scss: share existing SAT variables, base cards, eyebrows and
  picker selectors with the inspection scope, preserving their form scope.
- repair_device_inspection.scss: panel integration, 42px action and green dot.
- Manifest, architecture, changelog, module ficha and browser validation report.
- Check modal/main picker confirmations, new device loading, rear-only indication,
  labels-only absence and Cancel/Discard restoration in the isolated test database.

Date: 2026-10-17. Related: SPEC_DEVICE_INSPECTION.md. Scope authorized in chat.

## Models and fields
repair.order is extended in models/repair_order_inspection.py:
- x_device_description: existing Text moved from wex_consent, same column.
- x_device_condition_ids: Many2many to wex.repair.device.condition, internal only.
- x_device_inspection_marks: Json coordinates with device_type, front and back,
  internal only, copy=False. These are editable domain data, not DMS documents.

wex.repair.device.condition is a controlled shared catalog, not customer data:
name, sequence, active and optional device_type (empty means common).
Internal users read it; administrators maintain it. No sudo or public routes.
Repair ACLs and company rules continue governing all inspection data.

## Files and responsibilities
- models/repair_order_inspection.py: require type, validate marks and tag scope.
  Methods: _check_inspection_device_type, _check_inspection_marks,
  _check_inspection_conditions, _validate_inspection_view.
- models/device_condition.py and data/device_condition_data.xml: catalog and seeds.
- static/src/js/repair_device_inspection_field.js: native text wrapper, Dialog,
  draft editing, pointer coordinates, undo, clear and form record.update.
- static/src/xml/repair_device_inspection_field.xml: modal and wrapper templates.
- static/src/scss/repair_device_inspection.scss: responsive layout and subtle tags.
- static/src/img/device_inspection/*.svg: six code-native generic silhouettes.
- views/repair_order_views.xml: description widget and readonly tags below accessories.
- security/ir.model.access.csv, models/__init__.py, __manifest__.py: registration.
- wex_consent/models/repair_order.py and views/repair_order_views.xml: remove the
  relocated declaration and insertion; existing consent consumers remain intact.
- tests/test_device_inspection.py: ORM integrity, access, legacy and company cases.
- ARCHITECTURE.md, DECISION_LOG.md, CHANGELOG.md and project fichas/changelog:
  durable decisions and release evidence.

## Flow and phases
1. Models, catalog and permissions (small phase); validate Python/XML.
2. Modal, silhouettes and form integration; native update writes all draft values
   together. No independent RPC save, transient wizard or duplicate description.
3. ORM tests, diff review, installation/update verification when local test DB is
   available; document limitations rather than implying production validation.

## ADR — Keep editable marks in the repair
Chosen: bounded normalized stroke coordinates in Json, SVG static backgrounds.
Rejected: raster attachments/DMS files per stroke (unnecessary document lifecycle),
and storing rendered SVG/HTML from users (unneeded executable markup).
Chosen: relocate description to SAT base, avoiding a reverse dependency on consent.
Chosen: native form persistence, preventing a modal from independently saving a
stale parent form or losing unsaved reception fields.

## Rollback
Restore the changed source files and update both modules. Do not uninstall repair
or consent. Existing description column is retained; new fields can remain unused.
No destructive data migration or production database action is included.

## Iteration 2 — one visible face and confirmed reset

Approved in conversation on 2026-10-17. No schema change.

1. Update repair_device_inspection_field.js/xml/scss: activeView, face buttons,
   mark indicators, enlarged single SVG, face-local undo and clear; retain both
   sets of coordinates and modal cancellation semantics.
2. Add device_inspection_confirmation.js and register in manifest. Both selectors
   reuse confirmDeviceInspectionReset; only prompt when there is marks/tag evidence.
   Confirm resets both faces/tags and displays the new device immediately.
3. Update repair_device_type_picker_field.js to confirm and update parent draft.
4. repair_order_inspection.py: write delegates type-change value preparation to
   _prepare_inspection_type_change_values. Split changed/unchanged recordsets;
   default-clear prior evidence, preserve explicitly submitted new inspection data.
5. Extend ORM tests for reset, free-text retention, unchanged type, mixed recordsets
   and new evidence on changed type; browser-test confirmation, cancellation,
   both face drafts, active-face tools and the two type selectors.
6. Update architecture, decisions, test report, project changelog and module ficha.

## Console iteration — implemented 2026-10-17

1. Extend `models/device_constants.py` and `models/repair_order_inspection.py`:
   metadata via `_get_console_inspection_formats`, format validation via
   `_check_console_inspection_format`; retain existing non-console JSON.
2. Extend `device_inspection_confirmation.js` with `confirmConsoleInspectionReset`.
   In `repair_device_inspection_field.js`, `changeConsoleFormat` manages the local
   draft and `prepareInspectionMarks` serializes the format with both faces.
3. Add three illustrated cards in the existing OWL template and shared SAT SCSS.
   Six static SVGs provide front/back silhouettes without dependencies.
4. Extend `tests/test_device_inspection.py` with four console integrity tests;
   verify cards, metadata persistence, confirmations and cancellation in browser.
5. Update architecture, decision log, changelogs and module fiche. No new database
   field, model, portal route or document integration is introduced.

## Compact format cards — 2026-10-17

Change only the console-card selectors in repair_device_inspection.scss: bound
thumbnail dimensions and reduce spacing on narrow/short screens. Compile SCSS
and inspect the diff; no new methods, persistence changes or business tests needed.

## Technical report integration plan — 2026-10-17

- models/repair_order_sat_report.py: `_prepare_sat_report_inspection` collects data;
  `_get_sat_report_inspection_views` resolves trusted diagram metadata and faces;
  `_get_sat_report_inspection_image` composes local SVG and normalized paths.
- reports/sat_service_report.xml: conditional new-page section before photos,
  flowable description, printable tags and paired labelled diagrams.
- tests/test_sat_report_inspection.py: empty, tags/text, one/both marked faces,
  every supported scheme and console format, SVG geometry and escaped text.
- Validate actual PDF pagination and drawing appearance in an isolated database,
  verify the archived DMS PDF, then update architecture, decisions and fiche.
No new fields, routes, permissions, dependencies or DMS storage conventions.
