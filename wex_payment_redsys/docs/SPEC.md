# SPEC — Redsys redirect payments

Date: 2026-10-18. Version: 1.0. Implementation authorized by the user.

## Problem and scope
Customers must pay native Odoo quotations and invoices from their existing token
links, without visiting the shop. Administrators configure the provider; customers
use the native payment form. V1 supports EUR, card redirect payments and the
SHA256 protocol supplied by CaixaBank. No SAT, B2B customization, Bizum-specific
flow, refunds, subscriptions, card capture or stored payment tokens.

## Rules and use cases
1. Existing document access checks and transaction creation remain native.
2. Only an authenticated Redsys POST may confirm a payment. Browser return does not.
3. Verify signature, order, amount, currency, merchant, terminal and operation type.
4. Repeated notifications must not recreate payments or regress a completed result.
5. Never persist card metadata, raw notifications or reusable card identifiers.
6. Use native transaction states, accounting post-processing and sales confirmation.
7. Do not force invoice payment_state or automatically deliver any repair.
8. A new attempt is a new transaction, not a duplicate of a provider notification.

## Acceptance
- Install without credentials, disabled and unpublished.
- Configure test provider and pay quotation/invoice through native token links.
- Verify successful, declined, malformed, tampered and duplicate notifications.
- Verify missing browser return uses native post-processing cron.
- Verify multi-company consistency, secret access and absence of payment tokens.
- Verify rendered form and logging do not disclose card data or signing material.

## Dependencies and impact
Native account_payment (payment and account), cryptography already available in
the Odoo runtime. Sales integration is supplied by sale when installed. No changes
to existing Wexplay modules or OCA checkouts. No historical data migration.

## Pending external acceptance
PENDIENTE: public HTTPS test URL, proxy/database routing, selected journal and
outstanding receipts account, native Sales automatic invoicing configuration,
terminal acceptance of HMAC_SHA256_V1. Bank sandbox and real payments have not
been tested. The bank email explicitly specifies SHA256; do not silently negotiate
algorithms. Production activation is outside this delivery.
