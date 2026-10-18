# Device inspection — Validation and diff review

## Current validated state — 2026-10-17

The user confirmed the final repair/report/signature/portal behaviour. The latest
repair+consent suite has 47 passing tests; portal results are recorded separately
with applicable optional-module skips. The original SavepointCase limitation below
is resolved. Earlier sections remain historical evidence, not current blockers.
See [DEVICE_INSPECTION_GUIDE.md](DEVICE_INSPECTION_GUIDE.md) for the final matrix.
No tests were rerun during this documentation-only consolidation.

## 18.0.1.3.0 — Four additional types (2026-10-17)

- **16 tests, 0 failures, 0 errors** on the isolated core test database. New coverage
  saves/reloads both faces and type-specific tags for all four added types, rejects
  mismatched tags and denies portal access to the diagram metadata endpoint.
- Python/XML/JavaScript syntax passed. All fourteen catalog SVG files exist, parse
  correctly and preserve the shared 0 0 320 400 viewBox.
- Integration test module update passed. Browser inspected front/back for all-in-one,
  Mini PC, monitor and smartwatch, including their type-specific condition options.
- Confirmed reset from existing tablet to all-in-one still works. Subsequent empty
  inspections switch directly; selecting a type returns to its first face.
- Browser roundtrip saved a smartwatch with one stroke on each face and the strap
  condition. Reopening recovered both strokes, the selected condition, description
  and green heading indicator. This was purpose-created test data, not production.
- Captures: inspection-all-in-one.png, inspection-mini-pc.png, inspection-monitor.png
  and inspection-smartwatch.png under output/device_inspection_20261017/.
- The existing combined-suite consent SavepointCase limitation remains; the core
  tests and consent-installed integration database are validated separately.

## 18.0.1.2.1 — Shared SAT styling and mark indicator (2026-10-17)

- XML parsing, JavaScript syntax, both SCSS files and isolated module update pass.
- Browser confirmed identical DeviceTypePicker presentation in the form and modal,
  with the full icon grid. Both parent selectors still request reset confirmation.
- Modal confirmation cancellation preserves the original device; confirming loads
  mobile immediately. Cancelling the modal restores the parent tablet inspection.
- Button measured at 42 x 42 CSS pixels. Indicator count is 0 after removing the
  only front stroke while retaining conditions, and 1 after drawing rear-only
  evidence and applying. Native Discard restores the original saved inspection.
- Existing Python rules/storage are unchanged; the earlier 14-test core suite is
  the baseline, not a newly executed suite for this visual refinement.
- Captures: output/device_inspection_20261017/inspection-sat-style.png and
  output/device_inspection_20261017/inspection-green-indicator.png.

## 18.0.1.2.0 — One face and confirmed reset (2026-10-17)

- Core-only Odoo test database: **14 tests, 0 failures, 0 errors**. New coverage:
  automatic evidence reset while retaining description, unchanged type preservation,
  a new inspection supplied with the new type, and mixed changed/unchanged records.
- Python/JS syntax, XML parsing and Odoo SCSS compilation passed.
- Browser: exactly one SVG board; changing faces preserves its strokes and shows
  mark indicators. Clearing the rear face leaves the saved front stroke intact.
- Modal type change: cancellation retains type/evidence; confirmation immediately
  loads tablet with no marks/tags and unchanged text. Empty inspection switches
  directly to laptop. Cancelling the entire modal restores the original inspection.
- Main form picker: cancelling retains mobile; confirming changes to tablet,
  clears all evidence in the parent draft and preserves description. Native
  Discard restores the saved mobile inspection.
- A tags-only inspection also requests confirmation. No schema/data migration.
- Full integration roundtrip: confirmed mobile-to-tablet reset in the modal,
  drew a new stroke, selected a new condition, applied and saved the parent form.
  Reopening recovered tablet, new stroke/condition and unchanged description.
- Final capture: output/device_inspection_20261017/inspection-single-face.png.
- Prior combined-test limitation (legacy consent SavepointCase import) still applies;
  the core suite and the consent-installed browser integration were tested separately.

## 2026-10-17 — Field layout refinement

XML parsing, SCSS compilation and local module update passed. Browser measurement
at 1280 x 720 confirmed identical textarea dimensions for accessories and device
description: 549.5 x 83 CSS pixels. The icon appears at the heading's right edge,
retains the accessible name and tooltip, and opens the existing inspection modal.
Capture: output/device_inspection_20261017/inspection-field-layout.png.

Date: 2026-10-17. Related: SPEC_DEVICE_INSPECTION.md.
Environment: local isolated PostgreSQL databases, Odoo 18.0-20260220.
Production database and the existing server on port 8069 were not updated.

## Automated validation — initial iteration (historical)

- Python AST, XML/SVG parsing and JavaScript syntax: passed.
- New SCSS compiled with the installed Odoo Sass runtime: passed.
- Fresh wexplay_repair installation in codex_device_inspection_core_20261017:
  **11 tests, 0 failures, 0 errors**.
- Tests cover type requirement for text/tags/marks, saved inspection roundtrip,
  explicit mark clearing on type change, condition compatibility, malformed/out of
  bounds coordinates, stroke/point limits, historical untyped repairs, unsupported
  device diagrams, portal denial, catalog write denial and multi-company denial.
- wex_consent installation without its test suite: passed.
- Joint update of wexplay_repair and wex_consent on the integration test database:
  passed. Saved description, type, tags and marks retained; the combined form has
  exactly one x_device_description field.

## Browser validation — initial iteration (historical)

Used the local isolated integration database codex_device_inspection_20261017 on
port 8079 with purpose-created sample data. No customer data was used.

| Case | Result |
|---|---|
| Open without type | Only mandatory selector; Apply disabled |
| Select mobile | Front/back drawings, applicable checkboxes and text appear |
| Select tags | Tags appear in modal and below description after Apply |
| Draw and save | Pointer stroke persists and reappears after reopening/reloading |
| Edit text directly in parent | Immediate modal opening recovers the latest text |
| Cancel modal edits | Parent text, type and saved drawing remain unchanged |
| Undo / clear | Remove marks from draft without changing saved parent |
| Change type with marks in modal | Rejected with explicit warning |
| Change type in parent, then open | Incompatible drawing hidden; Apply disabled until cleared |
| Tablet and laptop | Correct two views and device-specific conditions |
| Native Discard | Cancels parent draft changes, retaining saved mobile inspection |
| 1280 x 720 layout | Both views, conditions and description fit together |

Capture: output/device_inspection_20261017/inspection-modal.png.

## Historical test-suite limitation — resolved

wex_consent/tests/test_wex_consent.py imports the removed Odoo SavepointCase.
Running combined module tests fails at import before those tests execute. This
pre-existing incompatibility was not changed in this scoped iteration. Core tests
were therefore run in a separate database without consent; consent installation,
combined views, joint module update and browser integration were checked separately.
This does not constitute a full regression run of signatures, workflow or delivery.

## Diff review

Accepted for local trial. No new dependency, sudo, public route, generated document
or frontend business persistence rule. Python owns integrity. Coordinates contain
no user SVG/HTML, inspection fields are internal and inherit native repair rules.
The existing description SQL column and its document consumers remain unchanged.
The mandatory type applies to inspection edits rather than all legacy operations.

Deployment: restart the target Odoo server and update both wexplay_repair and
wex_consent together, then reload backend assets. Do not uninstall either module.

Final status: the user confirmed functionality; reception signatures and portal
integration are implemented. Specific physical touch-device ergonomics remain
unrecorded. This replaces the initial scope/pending decisions above.

## Console iteration — 18.0.1.4.0, 2026-10-17

The isolated core test run completed with **0 failures, 0 errors in 20 tests**.
Four new tests cover all console formats, both-face JSON roundtrips, format-only
persistence, invalid/missing format rejection and preservation of tags/text.
Python/XML/JS syntax and SCSS compilation pass; all 20 SVGs have the expected viewBox.

Browser checks on the isolated integration database (with wex_consent installed):
- Three illustrated cards show the approved labels without descriptive subtitles.
- No format selected: diagram absent and Apply disabled.
- Saving/reopening an inspection without strokes restores its selected format;
  the form icon has no green indicator for format metadata or tags alone.
- Changing format with tags only is immediate and retains those tags.
- With marks on both faces, cancelling confirmation preserves format and marks.
  Confirming clears both faces and retains the selected tag and description.
- Cancelling the entire modal restores the previously saved console format.
- Saving and reopening a drawn PC de mano inspection restores its format and stroke,
  and activates the green indicator in the parent form.

Proof: `output/device_inspection_20261017/inspection-console-formats.png`.
The earlier combined consent-suite limitation remains; this is not a full
regression of unrelated signatures, workflow or delivery functionality.

## Compact format cards — 2026-10-17

SCSS compilation and diff whitespace validation pass. Thumbnails have explicit
maximum widths and heights; the existing small-screen breakpoint also covers
short viewports. Drawing board selectors and application logic are unchanged.
Visual acceptance on the reception screen remains pending.

## Desktop console asset correction — 2026-10-17

Both revised SVGs parse successfully and retain the 320 × 400 viewBox. Paths and
selector sizing are unchanged. Only silhouettes change; existing strokes are not
rewritten and may require visual review against the new contours.

## Technical report integration — 18.0.1.5.0, 2026-10-17

Core suite: **0 failures, 0 errors in 26 tests**. Six report tests cover empty and
whitespace-only descriptions, tags, escaped multiline text, either marked face,
all supported device schemes and console formats, both-face path geometry,
single-point strokes and console metadata without drawings.

Six actual PDFs rendered with Odoo/wkhtmltopdf in the isolated integration database:
mobile (front only), console (both), laptop (back only), long tablet description,
tags only and empty inspection. All generated bytes were saved/read through the
existing DMS helper and matched exactly. Repeated saves reused the same repair
report file. Test records and settings were rolled back afterwards.

PDF text assertions and rendered-page visual review confirm:
- Normal reports put inspection on page 2 and photos on page 3.
- The empty inspection adds no page; photos remain on page 2.
- The long description flows over pages 2–3, keeps paired diagrams together and
  starts photos on page 4, without clipping or overlap.
- Unmarked counterpart faces remain present if either face has strokes.
- Labels, red marks, tags and line breaks are legible in the real PDF.

Proofs: `output/pdf/inspection-mobile.pdf` and the five other inspection PDFs;
rendered contact sheet: `output/pdf/inspection-review.png`.
No production database was updated. The existing unrelated consent-test import
limitation still applies; this is not a full signature/workflow regression.
Deploy by restarting Odoo and updating wexplay_repair (also update wex_consent if
its earlier description-field ownership change has not yet been deployed).
Existing archived reports need regeneration to include the reception section.

## Shared signature preparation — 18.0.1.5.1

Composition helpers moved to repair_order_inspection.py; report context retains
its wrapper. The combined 47-test suite now runs successfully, including the
previously incompatible consent tests. Receipt kiosk/PDF checks confirm shared
geometry with frozen signature snapshots; report assertions continue to pass.
See wex_consent/docs/TEST_RECEPTION_INSPECTION.md for the signature-specific results.
