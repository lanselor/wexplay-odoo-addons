# Phase 1 Scope

Esta fase cubre exclusivamente la prueba de conexión entre una app Android y Odoo mediante un endpoint JSON protegido con Bearer token.

Incluye:

- Persistencia de sesiones de ping en Odoo.
- Configuración del token compartido en `ir.config_parameter`.
- Endpoint mínimo para crear o actualizar una sesión por `device_uuid`.
- Vistas básicas de backend para revisar las sesiones recibidas.
- Validación del flujo tanto por terminal como desde Android Studio.
- Soporte funcional para despliegue real por HTTPS y para prueba local controlada por HTTP en red privada.

Queda expresamente fuera de esta fase:

- Sensores.
- Altavoz.
- Giroscopio.
- Proximidad.
- Diagnóstico técnico del dispositivo.
- Integración SAT.
- `repair.order`.
- QR.
- Login de usuario final.

## Nota de evolución posterior

En iteraciones posteriores el módulo sí pasó a integrarse con `repair.order`, QR y runs operativos de test.

Esa evolución no cambia el criterio de fondo:

- `Test` sigue siendo un dominio funcional general del SAT
- la especialización Android actual aplica solo a `Móvil` y `Tablet`
- no debe haber dos pestañas `Test` visibles para el técnico en la misma reparación
