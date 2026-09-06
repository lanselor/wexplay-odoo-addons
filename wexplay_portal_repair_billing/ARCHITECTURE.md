# Portal SAT billing administration

## Scope
This bridge depends on the existing portal/workflow/dashboard integration. It adds
an administrative selection on repair.order; there is no parallel invoice model,
invoice calculation, payment registration or automatic invoice posting.

## Ownership
- Portal owns the active portal indicator and repair header badge.
- Repair owns SAT customer classification and customer-reference descriptions on sale invoice lines.
- This bridge owns customer automation, inclusion tracking, finish dialog and the internal queue.
- Workflow continues to own repair completion and glue/pickup locations.

## Inclusion
A commercial partner must be a company, a professional SAT customer and have an
active portal user. A contact on the repair is resolved to its commercial partner.
Manual inclusion is available from the native Action menu on forms and lists,
including missing quotations and exceptional diagnoses/warranty work.
Normal completion offers inclusion only for accepted budgets, outside warranty.
The customer can enable automatic inclusion for that same scope.
Mobile/tablet completion combines the billing choice with the existing location
wizard. Other devices receive Finalizar y añadir / Finalizar sin añadir.
Cancelling the dialog writes nothing; completion and inclusion share a transaction.
Inclusion is idempotent and keeps the first user and date. It does not create or
confirm a sale order. No historical repairs are enrolled during installation.

## Queue and native invoicing
The queue is repair.order grouped by commercial customer, without a time cutoff.
It shows the native order invoice status and warnings for missing/non-invoiceable
orders. Existing repair ACLs and company rules apply; portal users cannot enroll
repairs. The dashboard adds a shortcut only for stock users.
The native invoice action accepts a selection belonging to one commercial client
and one company. Every order must be confirmed and currently invoiceable. Client
and company must agree with its repair. The action passes distinct sale.order ids
to sale.advance.payment.inv and requests native consolidated billing. Odoo retains
its grouping keys, permissions, draft-invoice warnings, quantities and taxes.

## Queue lifecycle (18.0.1.1.0)
`wex_portal_billing_tracked` preserves enrollment independently of the stored,
computed `wex_portal_billing_pending` and `wex_billing_tracking_state` fields.
The latter records pending / completed invoicing / cancelled or under revision /
manual withdrawal / never enrolled. No invoice or payment state is written here.

- Completed native order invoicing hides the repair even with draft invoices.
  At least one non-cancelled customer invoice on a regular sale line must exist;
  down payments alone do not close tracking. Partial invoicing stays visible.
- Cancelling the sale order hides the repair. A cancellation latch keeps it hidden
  while the same order is edited in draft; reconfirmation clears that latch.
- Linked native order/invoice dependencies recompute visibility when quantities,
  invoice cancellation or deletion change the native invoicing result. No cron or
  custom invoice-creation callback is required. Changes from Sales also apply.
- The red row action uses native confirmation. It deactivates tracking and records
  date, user and a chatter note without unlinking business documents. Manual
  withdrawals do not reopen automatically, including via repair completion.
- The existing Add action explicitly reactivates tracking. Cancelled or already
  fully invoiced orders still stay outside the pending view after reactivation.
- Repairs never enrolled are never automatically enrolled by order/invoice changes.

The sale-order write extension runs only after native state changes succeed and
only updates the cancellation latch of tracked repairs linked to that same order
and company. The narrow sudo allows native sales users to update this internal
metadata without granting repair access. Manual actions enforce stock access and
repair write record rules. Computed stored fields use ORM dependency recomputation.

## Migration
The pre-migration copies the previous pending boolean to the new tracking field
before replacing pending with a computed field. Historical unmarked repairs remain
untracked. Cancelled orders already in the old queue get a cancellation latch.
The migration writes only administrative repair fields, never accounting records.

## Tests
Tests exercise the real finish workflow, combined glue dialog, inclusion,
portal denial, missing quotations, native grouped invoice creation and the
customer-reference snapshot. Validate installation against the full local stack
on an isolated database before updating the working database.
