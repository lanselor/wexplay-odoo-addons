# Devoluciones persistentes sin reenvío automático

| Campo | Valor |
|---|---|
| Fecha de consolidación | 2026-11-01 |
| Estado | Decisión existente, documentada sin cambio funcional |
| Módulo | wex_payment_redsys |
| Origen | Plan autorizado y arquitectura de la conversación |
| Revisión | Extraída de arquitectura; no supone auditoría nueva |

## Contexto, decisión y consecuencias
Utilizar asistente, transacciones hijas, disponible y pagos salientes nativos.
Persistir solicitud y marca de envío antes del contacto REST mediante cron con
cursor propio. Un resultado incierto mantiene pendiente y bloquea nuevas
solicitudes hasta verificación de Canales con evidencia y permisos contables.
No reenviar automáticamente: un timeout puede ocurrir tras devolver dinero.
No crear notas de crédito ni cancelar pedidos automáticamente. Mantener entorno,
comercio y terminal originales; verificar explícitamente cobros históricos.
Alternativas descartadas: llamada bancaria dentro de la petición UI y reintentos
ciegos. Compromiso: resolución manual y posible demora; no consulta automática.
Revisar el cron frente a las nuevas normas de lotes y queue_job antes de ampliar
la operativa. Esta extracción del ADR no modifica ni vuelve a aprobar código.

## Referencias
ARCHITECTURE.md, docs/SPEC.md, docs/REFUNDS.md y docs/TEST_RESULTS.md.
