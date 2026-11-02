# Proveedor nativo independiente

| Campo | Valor |
|---|---|
| Fecha de consolidación | 2026-11-01 |
| Estado | Decisión existente, documentada sin cambio funcional |
| Módulo | wex_payment_redsys |
| Origen | Plan autorizado y arquitectura de la conversación |
| Revisión | Extraída de arquitectura; no supone auditoría nueva |

## Contexto, decisión y consecuencias
Se conserva la adaptación independiente de la estructura y firma OCA bajo AGPL-3,
utilizando payment.provider, payment.transaction, tokens de documentos, estados,
pagos y conciliación nativos. No depender del conector OCA para sustituir su
tratamiento central de notificaciones. Alternativas: dependencia con overrides o
motor paralelo. La primera exigía reemplazar lógica central; la segunda duplica
Odoo. Consecuencia: Wexplay mantiene validación y compatibilidad del adaptador.
No introducir lógica SAT ni portal B2B en el proveedor.

## Referencias
ARCHITECTURE.md, docs/SPEC.md, docs/REFUNDS.md y docs/TEST_RESULTS.md.
