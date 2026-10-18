# Decisions

## 2026-10-17 — Fix reception content when requesting signature

Copy description, tag names and composed diagrams into the existing snapshot.
Store both faces if either has marks, including their original artwork. This keeps
kiosk and signed PDF consistent after repair edits, catalog renames or asset changes.
Freeze from queue entry; correction requires cancelling and resending. Protect
signed data in Python, retain existing DMS storage and do not rewrite old PDFs.
Reception only gains the inspection section. Generic content lifecycle guards also
protect delivery, whose document content remains unchanged.

## 2026-10-17 — Reuse inspection composition and native test support

Move composition to the shared repair inspection model and keep the report context
wrapper, avoiding duplicate geometry rules. No new dependency or persistent field.
Port obsolete SavepointCase tests to TransactionCase and update fixtures for current
mandatory device type, signer VAT and sanitized DMS names. Validate the real kiosk,
PDF/DMS and rollback behaviour in an isolated database before production rollout.

## 2026-10-17 — Consolidación documental y validación final

El usuario confirma que el conjunto funciona. Se consolida la documentación de
inspección, informe técnico, firma de recepción y portal, conservando el historial
y distinguiendo datos actuales, instantáneas firmadas y exposición autorizada.
Referencia: [guía consolidada](../wexplay_repair/docs/DEVICE_INSPECTION_GUIDE.md).
Esta revisión solo modifica documentación; no cambia código, versiones, permisos,
configuración ni datos funcionales, ni atribuye un despliegue de producción al agente.
