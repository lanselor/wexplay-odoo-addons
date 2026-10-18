# Historial del módulo

## 18/10/2026 — 18.0.1.0.4

Primera versión funcional confirmada por el usuario en pruebas; pendiente de
validación en producción. Suite final: 25 pruebas, sin fallos ni errores.

- Registro rápido de pagos nativos vinculados al SAT, sin servicio previo.
- Saldo disponible calculado desde la conciliación y aplicación a factura nativa.
- Cobro restante y devolución del disponible con los mecanismos de Odoo.
- Compatibilidad con diarios de banco, efectivo y tarjeta de crédito. Sin lista
  restrictiva, se ofrecen los diarios compatibles existentes de la compañía.
- Medios de cobro actualizados al cambiar el diario.
- Acciones de ventana con vistas explícitas para su apertura desde JavaScript.
- Resguardo térmico 80 × 170 mm rediseñado, UTF-8 y fecha dd/MM/yyyy.
- Eliminado el archivado DMS del módulo por decisión funcional. Ocultado Marcar
  como enviado exclusivamente en anticipos.
- Integración QZ opcional con identidad documental `sat_advance_receipt`.
- Avisos amarillos en SAT, pedido y factura, con importe pendiente y desglose si
  existen varios SAT; en reparación aparecen antes de Cliente Portal.
- Propuesta de entrega opcional cuando la factura queda pagada, sin entrega automática.

Decisiones: conservar la facturación habitual; no introducir saldo paralelo,
aplicación automática, exportaciones nuevas ni integración Redsys en esta versión.
Si no se puede reparar, se factura el diagnóstico realizado cuando corresponda;
la cancelación del SAT no devuelve dinero automáticamente. El tratamiento fiscal
documental del anticipo no queda certificado por la implementación.

La revisión de documentación consolida instalación, operación, límites y prueba
supervisada de producción. No modifica código, permisos ni datos de producción.
