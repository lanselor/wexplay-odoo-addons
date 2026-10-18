# Portal reception inspection validation — 2026-10-17

## Automated

With consent: portal suite selects 28 tests, **0 failures, 0 errors**. One existing
warranty-specific test is skipped because warranty is absent; the 27 applicable
tests execute, including all new inspection tests.
Without consent: same suite selects 28 tests, **0 failures, 0 errors**. Four signed-
source tests and the existing warranty test are appropriately skipped; 23 applicable
tests execute, including live-source, access and HTTP rendering checks.

New coverage: owner vs foreign commercial partner, public user denial, no sudo
bypass of the commercial-partner check, readonly field access, allowlisted output,
no internal notes/legal data, signed precedence, legacy text without live marks,
empty signed/current data, pending-source exclusion, no remote image URLs, QWeb
escaping, correct Ficha placement, collapsed initial details, foreign URL 404 and
anonymous login redirect. Python/XML/SCSS and diff whitespace validation pass.

The first detail-page HTTP check found a pre-existing base-portal assumption that
wex.image.record exists even without images installed. The test DB was aligned
with that existing image-core requirement; no dependency or unrelated image logic
was changed. Both final test DBs include wexplay_image_core. The HTTP delivered
fixture now uses native done when the optional delivered state is unavailable.

## Browser

Authenticated a fictitious portal contact below the repair's commercial partner
on localhost:8102. Ficha displays inspection immediately after diagnosis. Signed
source shows original description/front mark and unmarked back after live repair
edits; native disclosure starts closed and opens both faces. Another own repair
without a signed source shows the registered-data label. Foreign SAT URL returns
404 without revealing its description. No new Hero tab or editable controls.

Proof: output/device_inspection_20261017/portal-reception-inspection.png.
Only isolated databases were changed; no production deployment or external email.
Physical mobile/tablet acceptance remains pending; CSS stacks faces below 768px.

## Deploy

Restart Odoo, update wexplay_portal and reload website/browser assets. Current
wexplay_repair inspection helpers are required; if deploying the whole feature
series together, update repair/consent modules as previously documented. No field
migration, ACL expansion or hard dependency on wex_consent is introduced.

## Confirmación final — 17/10/2026

Funcionamiento confirmado por el usuario tras la integración completa. La
[guía consolidada](../../wexplay_repair/docs/DEVICE_INSPECTION_GUIDE.md) recoge las
reglas vigentes y sus diferencias documentales. Los resultados de pruebas descritos
corresponden a las ejecuciones anteriores; no se han repetido en esta tarea de
documentación. No se registra como realizada una prueba física específica de tablet.
