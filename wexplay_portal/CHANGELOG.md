# Changelog

## 18.0.1.1.0 — 2026-10-17

- Add readonly reception inspection below diagnosis in Ficha, with visible text/tags
  and both faces in a native collapsed disclosure. Hero tabs remain unchanged.
- Prefer frozen signed reception, handle legacy snapshots without mixing live data,
  and label current registered inspection when no signed source exists.
- Keep internal fields/consent/DMS inaccessible to portal and validate repair access
  before bounded sudo. Return an explicit display allowlist and embedded SVGs only.
- Add ORM/HTTP access, source, empty, escaping and placement tests. Adapt the existing
  HTTP delivered-state fixture to run with native repair when delivery is absent.
- Verify in isolated databases with/without consent and in a real portal browser.

## 2026-10-17 — Consolidación documental y validación final

El usuario confirma que el conjunto funciona. Se consolida la documentación de
inspección, informe técnico, firma de recepción y portal, conservando el historial
y distinguiendo datos actuales, instantáneas firmadas y exposición autorizada.
Referencia: [guía consolidada](../wexplay_repair/docs/DEVICE_INSPECTION_GUIDE.md).
Esta revisión solo modifica documentación; no cambia código, versiones, permisos,
configuración ni datos funcionales, ni atribuye un despliegue de producción al agente.
