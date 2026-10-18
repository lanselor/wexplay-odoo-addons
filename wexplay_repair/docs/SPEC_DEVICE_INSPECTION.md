# SPEC — Internal device inspection

Date: 2026-10-17. Modules: wexplay_repair, wex_consent. Version: 5 (consolidated final scope).
Functional scope implemented and confirmed working by the user on 2026-10-17.
Current consolidated reference: [DEVICE_INSPECTION_GUIDE.md](DEVICE_INSPECTION_GUIDE.md).

## Problem and context
Reception staff need a quicker way to describe visible device damage. The existing
free-text field must remain the same source of truth and preserve existing data.

## Users and solution
Internal users with repair write access open a modal below delivered accessories.
They select a device type, draw on generic front/back silhouettes, select controlled
damage tags and edit the existing description. Portal users cannot edit/read the
internal fields directly; wexplay_portal exposes only authorized display values.

## Business rules
- No inspection content is shown until a device type is selected.
- A type is required when editing description or saving inspection data, not for
  unrelated operations on historical repairs without a type.
- Mobile, tablet, laptop, all-in-one, Mini PC, monitor, smartwatch and console have two
  drawable views, one visible at a time. Buttons
  select the face and indicate marks; undo/clear operate only on the visible face.
  Opening or changing type selects the first face. Other types allow text/tags.
- Tags do not generate text. They appear in the modal and below the description.
- Cancel discards modal edits. Apply updates the unsaved parent form atomically;
  the native repair Save persists it, and native Discard reverts it.
- A type change resets both drawings and all conditions, preserving free text.
  Both selectors confirm first if there are marks or tags; declining or dismissing
  the confirmation changes nothing. Empty inspections change directly. Cancelling
  the entire modal also discards any type change confirmed within its draft.
- Inspection fields remain internal. Their prepared content is included in the
  technical report, frozen reception signatures and authorized B2B portal display,
  following the source and lifecycle rules in the consolidated guide.

## Use cases and acceptance
1. Empty type: open modal, see selector only, select mobile, inspect, apply, save.
2. Existing inspection: reopen, recover both views, tags and text; undo and clear.
3. Cancel after changing type/text/tags/drawing: parent remains unchanged.
4. RPC attempts without a type or with inconsistent drawing/tag data fail in Python.
5. Unrelated edits to historical untyped repairs still succeed.
6. Internal permissions and native company record rules apply; portal cannot read
   the new fields or damage catalog.

## Dependencies, impact and risks
No new external dependency. Reports retain DOCUMENTS and signatures SIGNATURES
in existing OCA DMS. Description ownership moves from
wex_consent to its existing dependency wexplay_repair using the same SQL column.
Upgrade both modules together to avoid a duplicate description block.

## Final scope and remaining validation
Technical report, reception signature and portal integration are implemented and
user-confirmed. Workflow, delivery inspection content and independent DMS image
exports are outside this iteration. Specific physical tablet/touch acceptance
has not been recorded; functional confirmation does not claim that hardware test.

## Approved console iteration — 2026-10-17

- The main repair type stays Consola; a modal-only selector offers Sobremesa,
  Portátil clásica and PC de mano with generic illustrations and names only.
- No default format: choose one before showing its diagram or applying changes.
- Keep the existing face selector and drawing tools; provide six console SVGs.
- Persist the chosen format in inspection JSON, even without drawings.
- Changing format with marks asks for confirmation, then clears both faces only.
  Tags and description remain. Without marks the format changes immediately.
- Cancelling confirmation preserves the draft; cancelling the modal restores all
  original parent values. Format metadata alone never lights the green indicator.
- Existing supported types and general type-reset rules remain compatible.

## Compact format cards — 2026-10-17

Console format thumbnails are limited to 112 × 72px. At viewport widths up to
767px or heights up to 800px they use 80 × 56px with tighter card padding and
spacing. Keep names visible and preserve the full drawing board dimensions.

## Desktop console visual reference — 2026-10-17

Sobremesa means a living-room gaming console (such as PS5 or Xbox), not a desktop
computer. Its generic front/back schemes use a Series S-inspired horizontal body
and prominent circular cooling grille, without logos. Existing drawing coordinates
are preserved; previously marked inspections should be visually reviewed against
the revised silhouette.

## Technical report integration — approved 2026-10-17

Include an automatic “Estado del dispositivo en recepción” section on a new page
before photographic evidence if description, tags or strokes exist. Include only
available text/tags; if either face has strokes, include both labelled faces.
Format-only metadata adds no page. Use the same PDF, DMS file, permissions and
manual generation/regeneration lifecycle. No independent documents or browser
screenshots. Long descriptions flow without truncation, photos start on a new page.
This content becomes visible to report recipients, as explicitly approved.
