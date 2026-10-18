# Wex Consent architecture

## Scope

Owns reception/delivery documents, signature requests and kiosk sessions. Depends
on wexplay_repair for SAT identity, description, DMS directory strategy and shared
inspection composition. No independent repair or document taxonomy is introduced.

## Reception inspection snapshot — 2026-10-17

The existing snapshot_json captures device type, console format and a conditional
device_inspection object: description, condition names and two labelled SVG data
images if either face has marks. SVG composition belongs to the shared inspection
model in wexplay_repair; the signature module copies its result, including the
original contours. No new stored field or attachment is needed for those diagrams.
Neither the kiosk nor the reception PDF reads current repair inspection values.
The archived PDF, not a future rerender, remains the signed document.

## Content lifecycle

Drafts may refresh from repair. Request creation refreshes once, then freezes
content while any request is queued/presented. Reopening an existing active request
never refreshes it. Cancel/requeue captures new saved repair data. Signed records
reject content, signature, consent, state and PDF replacement writes at ORM level.
The server action writes the initial PDF/archive references through its private
internal path; no caller-supplied context bypass is accepted. PDF generation
requires signed state and refuses a second PDF even with the old force context.

Document-level row locks serialize refresh, request creation, cancellation and
signature registration. They do not lock the repair, other documents or the kiosk
queue globally. Failed rendering/DMS saving rolls back the entire signature RPC,
leaving the request available for retry. Existing ACLs and company rules still apply.
These are application-level lifecycle protections, not a new cryptographic scheme.

## Presentation and DMS

Kiosk inspection is readonly, with wrapped tags and both labelled faces; faces stack
below 768px. Empty content is omitted. Reception PDF adds the inspection on a new
page before the signature block, permits long text to flow and keeps diagrams and
signature blocks together. Delivery gains no inspection section. Existing documents
without the snapshot key render without it; no backfill or signed-PDF migration.
Pending historical requests keep their old content until cancelled and resent.

PDFs use the existing SIGNATURES folder and DMS configuration/access groups. No new
sudo, permission group, route or public exposure is introduced. Mail behaviour is
unchanged; all automated/UI tests use fictitious recipients with no outgoing email.

## Referencia consolidada y aceptación — 2026-10-17

El usuario confirmó el funcionamiento del conjunto de inspección, informes,
firmas y portal. La [guía transversal](../wexplay_repair/docs/DEVICE_INSPECTION_GUIDE.md)
describe su matriz de fuentes y actualización. Se mantienen las fronteras de cada
módulo: base SAT prepara evidencia, firmas conserva la copia presentada y portal
solo entrega valores autorizados. Esta confirmación no registra un cambio de
estado del módulo ni un despliegue de producción realizado por el agente.
