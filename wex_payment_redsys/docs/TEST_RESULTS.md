# Test results — 2026-10-18

Environment: local Odoo 18.0.20260220, isolated database
`wex_redsys_test_20261018`, separate filestore under `C:/odoo18/test/redsys_runtime`.
Installed account_payment, sale and wex_payment_redsys. No existing business DB
was modified. No connection to the Redsys bank sandbox was made.

## Result

20 tests passed, 0 failures, 0 errors. Final log:
`C:/odoo18/test/redsys_tests9.log`.

| Coverage | Result |
|---|---|
| Independent SHA256/TripleDES fixed signature vector | Pass |
| Unique numeric references | Pass |
| Valid signed success and repeated callback | Pass |
| Forged signature rejected even with Odoo test_enable | Pass |
| Signed amount, currency, merchant, terminal and type mismatch | Pass |
| Decline without authorization code | Pass |
| 0100 excluded from authorized response range | Pass |
| Late decline does not regress completed transaction | Pass |
| Malformed Base64/JSON and duplicate JSON keys | Pass |
| No tokenization, direct, zero, negative or non-EUR payments | Pass |
| Secret inaccessible to invoicing operator in the same company | Pass |
| Redirect form renders; signed payload absent from native rendering logs | Pass |
| Native invoice payment, reconciliation and repeated post-processing | Pass |
| Extra card metadata is not persisted | Pass |
| HTTP native invoice token route -> signed callback -> native payment | Pass |
| Invalid native invoice token denied | Pass |
| HTTP forged POST denied; GET webhook denied | Pass |
| Browser return with signed query does not confirm transaction | Pass |
| HTTP native quotation token -> callback -> native sales confirmation | Pass |

The last two document flows use Odoo's real HTTP controllers with simulated
Redsys messages, then the native _post_process method. Native cron scheduling
is triggered by successful callbacks; unattended scheduler timing and bank retries
were not tested. No concurrency stress or full multi-company matrix was executed.

## External acceptance still pending

Public HTTPS/proxy/database routing; terminal acceptance of SHA256; accepted and
declined bank test cards; Canales notification delivery; browser behavior from a
real mobile device; accounting journal configuration in the habitual test DB.
No production readiness or bank approval is implied by these local results.

## Review

No core/OCA modifications. No new business models, payment states, balance
calculations, invoice-state writes, card fields, token creation, custom JS or cron.
Fields protected in ORM, callback signature verified before state mutation,
notifications never logged, native post-processing retained. External financial
effects are outside automated tests. Rollback: disable/unpublish the provider.
