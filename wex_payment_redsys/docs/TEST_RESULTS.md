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

## External acceptance pending at the original local test date

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

## Refund extension — 2026-11-01

30 tests passed, zero failures/errors in redsys_refunds_verified.log (same isolated
database). Includes 20 existing tests and 10 refund tests. HTTP bank responses
and timeout are simulated. No actual refund has been sent to Redsys. See
REFUNDS.md for external acceptance and transactional test limits.

## Consolidación de aceptación del usuario — 2026-11-01

Evidencia: capturas y confirmaciones aportadas por el usuario en esta conversación.
El usuario ejecutó las operaciones en su instancia operativa de Odoo contra el
sandbox de Redsys. No son operaciones monetarias reales ni actuaciones del agente
sobre producción. La ausencia de llamadas bancarias descrita arriba solo se refiere
a los tests automatizados locales de cada fecha.

| Caso | Resultado acreditado |
|---|---|
| Cotización con token sin login | Proveedor visible tras publicarlo; pago aceptado y pedido confirmado |
| HTTPS y terminal SHA256 | Petición y notificaciones aceptadas en test tras ajuste de proxy |
| Pago rechazado | Error visible y sin pago vinculado, confirmado por el usuario |
| Pago cancelado | Cancelación visible y sin pago vinculado, confirmado por el usuario |
| Cierre tras autorización sin Continuar | Pedido confirmado y pago generado posteriormente |
| Facturación de pedido previamente pagado | Factura vinculada al cobro existente sin nuevo cobro |
| Factura independiente | Pagada con transacción y pago nativos |
| Devolución total | Pago saliente enlazado al original y devolución autorizada visible en Canales test |

### Pendientes conservados
- Parcial y devolución del restante, incluido límite acumulado, contra Redsys test.
- Reintento exitoso acreditado sobre el mismo documento rechazado/cancelado.
- Reenvío bancario de notificación: solo validación automatizada de duplicados.
- Visualización/resolución del bloque de verificación para cobros antiguos:
  vista activa y grupo comprobados; un nuevo cobro permitió probar devoluciones,
  pero no demuestra resuelto el acceso al bloque en pagos históricos.
- Cortes reales de proceso, concurrencia multinodo y matriz multiempresa completa.
- Compatibilidad completa con los nuevos estándares técnicos y análisis de seguridad
  formal; esta actualización documental no equivale a una auditoría del código.
- Aprobación bancaria, credenciales/algoritmo del terminal real, cobro/devolución
  reales y liquidación bancaria. No se declara habilitado el pase a real.

No se almacenan aquí capturas con datos personales, tokens de acceso ni secretos.
