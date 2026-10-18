# Changelog

## 18.0.1.0.0 — 2026-10-18

- Añadido proveedor de tarjeta EUR mediante redirección y firma HMAC SHA256 V1.
- Reutilizados enlaces con token, transacciones, estados, pagos y conciliación
  nativos de Odoo, sin modelos nuevos ni dependencias SAT/portal personalizadas.
- Añadidas validación de notificación, protección contra duplicados, restricciones
  de secreto y exclusión de datos de tarjeta y tokenización.
- Instalación inicial desactivada. Pruebas externas con el banco pendientes.
- ADR: adaptación independiente del conector OCA para evitar sobrescribir sus
  rutas, validación, clasificación de resultados y procesamiento central.
