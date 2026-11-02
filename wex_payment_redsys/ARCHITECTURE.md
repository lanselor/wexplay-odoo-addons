# Architecture — Wex Redsys

Date: 2026-10-18. Scope approved in conversation. See docs/SPEC.md.

## Models and fields
Extend payment.provider with code wex_redsys, merchant code, terminal and secret.
Extend payment.transaction without new business states or balances. Native
provider_reference stores the authorization reference, never a card reference.
No new models or ACLs. Secret field restricted to base.group_system.

## Ownership and flow
Native document token -> native transaction -> provider redirect template ->
Redsys -> signed POST -> _handle_notification_data -> native state setters ->
native payment cron/status post-processing -> account.payment/reconciliation and
sale confirmation. Browser return only opens /payment/status.

Global ir.sequence supplies 12-digit numeric references, keeping Odoo's unique
reference constraint. Distinct databases using the same terminal require separate
reference ranges or terminals before concurrent use; do not use cloned sequences.

## Security
The public POST uses narrowly scoped sudo to locate a transaction, then validates
the signed bytes and semantic fields before any state change. Row locking and
cache invalidation serialize duplicate callbacks. Native post-processing owns
accounting; callback only triggers its existing cron. Do not call _post_process
from the webhook. It may retry through Odoo without custom jobs.

Crypto and notification parsing are pure private helpers. Parsing has size/type
limits and rejects duplicate JSON keys. Never log bodies, signatures or secrets.
QWeb invokes a model preparation method only at render time: Odoo logs the safe
record context, not the signed form parameters. No business calculations in QWeb.
Initial payments accept only positive EUR online_redirect; version 1.1 also accepts native negative refund children. No tokenization.

## ADR — adaptation instead of OCA dependency
Accepted for implementation, 2026-10-18. OCA l10n-spain payment_redsys 18.0 was
reviewed. Its model/view architecture, protocol parameter mapping and SHA256
diversification are useful references, retained under AGPL-3 attribution.
An extension would replace notification lookup, signature checks, result mapping,
logging and post-processing behavior. Maintain a small independent adapter with
native Odoo extension hooks instead of that replacement layer. OCA is not installed
or modified. No new third-party payment service or library is required.

## Rollback and limitations
Disable/unpublish the provider; retain accounting records and transactions.
No automatic recovery of missing notifications or overpayments. Refund scope is defined in docs/REFUNDS.md.
Two separately authorized attempts are distinct receipts, not a duplicate callback.
Review such cases using native transactions/accounting and the bank console.
Native invoice state may remain in_payment until bank reconciliation.

## Refund extension 2026-11-01

See docs/REFUNDS.md for the approved scope, persistence boundaries, dedicated
cron, original environment verification and manual incident resolution. This
supersedes the v1 exclusion of refunds, retaining the original payment callback.

## Fuentes y estado vigente — 2026-11-01
Versión 18.0.1.1.0. README es la guía de entrada; SPEC define alcance;
TEST_RESULTS separa evidencia local, evidencia del usuario y pendientes.
Decisiones extraídas sin cambio funcional: docs/ADR-001_NATIVE_PROVIDER.md y
ADR-002_REFUNDS.md. Los apartados originales se conservan como historial.
No existe todavía ficha YAML. Su creación requiere autorización específica.

## Revisión frente a estándares nuevos
CODING_STANDARDS_ODOO18.md y AI_WORKFLOW.md son obligatorios para siguientes
cambios. Pendiente de revisión formal: SQL/flush, sudo acotado, cron por lotes y
justificación del despachador frente a queue_job; claves públicas de sandbox en
fixtures frente a la regla de secretos en tests. No se presenta esta documentación
como corrección ni excepción aprobada de esos puntos. El análisis de seguridad
con SECURITY_TEMPLATE.md también queda pendiente de consolidar.
