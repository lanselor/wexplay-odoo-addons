# Reception inspection validation — 2026-10-17

## Automated

Odoo 18 isolated integration database, wexplay_repair + wex_consent updated together:
**0 failures, 0 errors in 47 tests** (26 repair, 21 consent).
Coverage includes both faces with only one marked, snapshot metadata, queued and
presented freezing, renamed conditions, repair edits, no live asset reads at render,
cancel/requeue, old snapshots, empty/text/tag inspections, delivery compatibility,
signed content/forced PDF replacement, direct manager ORM writes, company access,
rejecting queued signatures and atomic rollback after failed DMS storage.
Old SavepointCase import and outdated fixture/API expectations are corrected.
Python/XML/JS syntax, SCSS compilation and diff whitespace checks pass.

## Real kiosk and PDF

Fictitious mobile reception request opened in the browser at localhost:8099.
After queueing, repair description was changed and marks cleared in a separate
committed transaction. Reloading the kiosk still showed the original text, tag,
front mark and unmarked rear. A test stroke was signed on the canvas and confirmed.
The signed PDF was created in SIGNATURES, binary-matched to the archived DMS file,
and the kiosk returned to waiting. No email was sent and no production DB changed.

Initial attempt exposed missing access-group configuration in the isolated DMS
storage. Signature transaction rolled back correctly; directory permissions were
configured for the existing test user and the same request completed successfully.
No module ACL or sudo workaround was added.

Five real PDFs rendered and reviewed: mobile, handheld-PC console, long laptop
reception, empty reception and delivery. Mobile/console use 2 pages with inspection
and signature on page 2; long text flows across pages 2–4 with both diagrams and
signature intact; empty reception and delivery stay at 1 page. No clipping or
blank extra pages. Edited live repair text never appears in the signed PDF.
Other PDF fixtures/settings were rolled back; the browser proof remains in the
isolated DB. Physical tablet/touch-device acceptance remains pending.

Proofs: output/device_inspection_20261017/consent-kiosk-inspection.png,
output/pdf/consent-reception-mobile.pdf and output/pdf/consent-review.png.

## Deployment

Restart Odoo and update wexplay_repair + wex_consent together, then reload browser
assets. Pending pre-update requests retain their old snapshot; cancel and resend
if they should include new inspection data. Existing signed PDFs remain unchanged.

## Confirmación final — 17/10/2026

Funcionamiento confirmado por el usuario tras la integración completa. La
[guía consolidada](../../wexplay_repair/docs/DEVICE_INSPECTION_GUIDE.md) recoge las
reglas vigentes y sus diferencias documentales. Los resultados de pruebas descritos
corresponden a las ejecuciones anteriores; no se han repetido en esta tarea de
documentación. No se registra como realizada una prueba física específica de tablet.
