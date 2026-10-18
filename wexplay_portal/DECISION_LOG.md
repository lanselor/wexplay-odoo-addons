# Portal decisions

## 2026-10-17 — Reception state belongs below diagnosis in Ficha

Keep the existing Hero tabs. Add one full-width readonly card below diagnosis,
with description/tags visible and diagrams in native collapsed details. Show both
faces when the inspection contains drawings, using the shared prepared geometry.
Do not add dependencies or frontend JS for the disclosure.

## 2026-10-17 — Prefer signed reception without mixing current data

Signed snapshot takes precedence, labelled explicitly. Legacy signed data shows
its saved text only; empty signed data is not replaced by current inspection.
Without signed reception, show registered repair data with a different source
label. Optional consent lookup stays encapsulated in portal model after native
and commercial-partner authorization. No new portal access to internal fields,
DMS, signatures, legal snapshot data or unrelated repair records.

## 2026-10-17 — Consolidación documental y validación final

El usuario confirma que el conjunto funciona. Se consolida la documentación de
inspección, informe técnico, firma de recepción y portal, conservando el historial
y distinguiendo datos actuales, instantáneas firmadas y exposición autorizada.
Referencia: [guía consolidada](../wexplay_repair/docs/DEVICE_INSPECTION_GUIDE.md).
Esta revisión solo modifica documentación; no cambia código, versiones, permisos,
configuración ni datos funcionales, ni atribuye un despliegue de producción al agente.
