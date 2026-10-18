# Implementation plan

1. Move shared SVG composition to repair_order_inspection.py with semantic methods
   _prepare_device_inspection_snapshot, _get_device_inspection_document_views and
   _get_device_inspection_document_image; retain the report collector wrapper.
2. Extend wex_consent_document.py snapshot and add private snapshot readers,
   content locking and frozen-field validation. Serialize document refresh/request/
   signing with a document row lock; no user-controlled context bypass.
3. Keep an existing active request without refreshing. Cancellation/requeue must
   capture updated data. Signed content and generated PDF remain immutable.
4. Add readonly kiosk inspection and reception PDF section from the saved snapshot;
   add form readonly modifiers matching server protections. No live repair reads.
5. Port SavepointCase tests to TransactionCase and current signature API; test
   freezing, both faces, legacy snapshots, cancellation, PDF and DMS roundtrip.
6. Validate real PDFs and kiosk in an isolated DB, then update docs and fiches.

## Confirmación final — 17/10/2026

Funcionamiento confirmado por el usuario tras la integración completa. La
[guía consolidada](../../wexplay_repair/docs/DEVICE_INSPECTION_GUIDE.md) recoge las
reglas vigentes y sus diferencias documentales. Los resultados de pruebas descritos
corresponden a las ejecuciones anteriores; no se han repetido en esta tarea de
documentación. No se registra como realizada una prueba física específica de tablet.
