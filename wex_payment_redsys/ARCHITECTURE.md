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
Only online_redirect positive EUR transactions are accepted; no tokenization.

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
No automatic recovery of missing Redsys notifications, refunds or overpayments.
Two separately authorized attempts are distinct receipts, not a duplicate callback.
Review such cases using native transactions/accounting and the bank console.
Native invoice state may remain in_payment until bank reconciliation.
