# Production Guardrails

Production calls are intentionally blocked by default.

The connector has two separate switches on `mrw.shipping.config`:

- `Entorno`: selects TEST or production endpoint.
- `Permitir llamadas reales de producción`: allows SOAP calls when the
  environment is production.

Both conditions are required for production SOAP calls.

## Before Enabling Production

Validate in TEST:

- WSDL connection.
- WSDL operation inspection.
- Configuration diagnostic action.
- National shipment creation.
- National label retrieval.
- Public tracking opening from picking / MRW shipment / SAT shipping operation.
- Cancellation rejection behavior.
- Address and phone validation.
- Multibulto if it will be used.
- International shipment and label if it will be used.

Recommended current production baseline:

- national outbound shipments
- national customer pickups
- label retrieval and retry
- public historical tracking link
- manual and SAT-assisted operational follow-up

## Known Production Limits

- No MRW live rating API has been confirmed.
- Only the public historical tracking URL is implemented; no tracking SOAP
  timeline or POD enrichment is available.
- Service catalog download is not available in the inspected API.
- MRW may reject cancellation depending on MRW's internal expedition state.
- International usage still requires explicit live validation before relying on
  it operationally.

## Operational Rule

Do not enable production calls just because the WSDL is reachable. WSDL
reachability proves endpoint availability, not credential validity or MRW
business approval.
