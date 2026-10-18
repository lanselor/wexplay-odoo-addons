# Changelog

## 18.0.1.1.0 — 2026-10-17

- Capture reception description, tag names and composed front/back diagrams with the signature request, including console format. Kiosk and PDF use the saved snapshot.
- Freeze queued/presented content; cancellation and resend capture updates. Protect signed fields/PDF in Python and remove forced regeneration bypass.
- Add readonly reception inspection in the kiosk and on a new PDF page before signature. Keep delivery content, old documents and SIGNATURES storage compatible.
- Serialize document content transitions and test atomic rollback on DMS failure.
- Port legacy tests to Odoo 18; 47 combined tests pass. Verify real kiosk signing and five actual signed PDFs against DMS.

## 18.0.1.0.1 — 2026-10-17

- Device description declaration and reception form block now belong to the
  existing dependency wexplay_repair. The field name and database column remain
  x_device_description, preserving all stored descriptions and document consumers.
- Update wexplay_repair and wex_consent together. Consent generation, signature
  snapshots and PDF contents remain unchanged; new inspection marks/tags are not
  included in signed documents.

## 2026-10-17 — Consolidación documental y validación final

El usuario confirma que el conjunto funciona. Se consolida la documentación de
inspección, informe técnico, firma de recepción y portal, conservando el historial
y distinguiendo datos actuales, instantáneas firmadas y exposición autorizada.
Referencia: [guía consolidada](../wexplay_repair/docs/DEVICE_INSPECTION_GUIDE.md).
Esta revisión solo modifica documentación; no cambia código, versiones, permisos,
configuración ni datos funcionales, ni atribuye un despliegue de producción al agente.
