# Project Pending Items - MRW Shipping Connector

This document tracks global pending work across the MRW connector and adjacent
Odoo flows. It must be kept separate from MRW API evidence: items here may be
product decisions, integration work, or operational validation still pending.

## Implemented Baseline

- MRW SOAP connection and WSDL inspection.
- MRW credentials/configuration records.
- MRW service catalog records.
- Manual MRW shipments.
- Native `delivery.carrier` integration for outgoing `stock.picking`.
- National shipment creation with `TransmEnvio`.
- Label retrieval and PDF attachment.
- Sanitized technical SOAP logs.
- MRW cancellation request using `CancelarEnvio`, with state preserved when MRW
  rejects cancellation.
- Manual national customer pickup:
  - customer address mapped to `DatosRecogida`;
  - company address mapped to `DatosEntrega`;
  - same MRW states, logs, label handling, and cancellation actions as outbound
    shipments.
- Optional incoming `stock.picking` creation from manual customer pickup.
- Wexplay repair pickup bridge through `wexplay_repair_delivery`:
  - repair shipping operations can create MRW customer pickups;
  - pickup MRW shipments can be linked back to SAT operations and optional
    incoming pickings;
  - generic MRW SOAP logic remains inside `mrw_shipping_connector`.

## Pending Global Work

### 1. RMA / SAT Link From Incoming Pickups

Status: not implemented.

Current behavior:

- A manual customer pickup can create a linked incoming picking.
- When that incoming picking is validated, Odoo receives the product into stock.

Missing behavior:

- No automatic RMA record is created.
- No repair order is created or linked.
- No existing repair/RMA flow consumes the incoming picking.
- No workflow decides whether the received item should go to repair, warranty,
  replacement, refund, scrap, or resale.

Decision needed:

- Define the target RMA/SAT model and flow before implementing this bridge.
- Keep this outside the generic MRW connector if the result is Wexplay-specific.

### 2. Customer Pickup From Additional Native Odoo Flows

Status: partially implemented.

Current behavior:

- Customer pickups can be created manually from `MRW Shipments`.
- Wexplay SAT repairs can create MRW customer pickups through
  `wexplay_repair_delivery`.

Missing behavior:

- No generic native button from return pickings, sale orders, or helpdesk
  objects creates MRW pickups.
- The existing native bridge is Wexplay-specific, not a generic Odoo feature of
  this connector.

Decision needed:

- Decide whether to generalize pickup automation beyond the existing
  `wexplay_repair_delivery` bridge.
- Recommended next generic candidate: incoming return/RMA picking, not a custom
  logistics core inside this addon.

### 3. International Pickup Validation

Status: not implemented.

Current behavior:

- Customer pickup is limited to national shipments.

Missing behavior:

- International pickup request structure has not been validated with MRW.
- No TEST case exists with a non-Spain pickup/delivery flow.

Decision needed:

- Validate with MRW before enabling.

### 4. `TransmEnvioEC` / `TransmitirEnvioEC`

Status: not implemented.

Current behavior:

- The WSDL exposes both operations.
- The connector does not use them.

Reason:

- The legacy PrestaShop module did not provide enough evidence that these are
  the correct operations for customer pickup/RMA.
- Customer pickup currently uses confirmed `TransmEnvioRequest` fields:
  `DatosRecogida`, `DatosEntrega`, and `DatosServicio`.

Decision needed:

- Only implement EC operations after receiving documentation or a confirmed MRW
  TEST request/response.

### 5. Tracking Enrichment

Status: partially implemented.

Current behavior:

- MRW shipment number is stored and exposed as tracking reference.
- Public historical MRW tracking URL is implemented and reused from Odoo
  pickings, MRW shipment records, and Wexplay SAT shipping operations.

Missing behavior:

- No tracking SOAP consumption is implemented.
- No proof-of-delivery or tracking-event timeline is shown inside Odoo.
- International tracking behavior has not been validated.

Decision needed:

- Keep the public historical URL as the production baseline.
- Only add tracking SOAP features after MRW documentation or TEST validation.

### 6. Live Rating / Cost Calculation

Status: not implemented.

Current behavior:

- Odoo uses configured delivery product pricing.

Missing behavior:

- No MRW rating API is implemented.
- Real MRW invoice cost may depend on account-specific billing variables such
  as mileage.

Decision needed:

- Keep configured prices or implement a reconciliation/reporting flow once real
  invoice data is available.

### 7. Production Readiness

Status: partially implemented.

Current behavior:

- Production calls are blocked unless explicitly enabled in MRW configuration.
- Connector diagnostics exist for credentials/default services/WSDL reachability.
- Native Odoo send, label retrieval, cancellation request, and public tracking
  are implemented.

Missing behavior:

- Real production validation with live MRW traffic.
- Real production cancellation behavior validation.
- Operational runbook for failed label retrieval, MRW rejection, and date
  changes observed after expedition.

### 8. UX Polish

Status: partially implemented.

Pending polish:

- Dynamic labels for customer pickup fields. Example: show "Cliente de recogida"
  instead of "Destinatario" when operation type is `Recogida en cliente`.
- Better filters for manual pickups with/without incoming picking.
- Optional dashboard for shipments requiring operational attention.
- Further optional consolidation of lower-priority shipment actions if future
  screen density becomes a problem again.

### 9. Automated Tests

Status: partially implemented.

Pending tests:

- Incoming picking creation from customer pickup in a real Odoo test run.
- Full mocked `delivery.carrier` send flow with label retrieval.
- Rejection cases for pickup with missing company address.
- Regression tests for sanitized pickup SOAP payloads.

## Pending Integration Notes

These are the integrations explicitly still pending around this mature baseline:

- Generic RMA/returns bridge from incoming pickups outside Wexplay SAT.
- Generic customer-pickup entry points from other native Odoo documents.
- International shipment/pickup live validation before production use.
- Tracking SOAP / POD enrichment beyond the public MRW historical link.
- Live MRW rating or reconciliation against carrier invoices.

## Explicit Non-Goals For This Connector

- Do not add dependency on `wex_logistics_core`.
- Do not add dependency on `wex_logistics_repair`.
- Do not create a custom logistics core inside the MRW connector.
- Do not implement MRW endpoints that are not evidenced by code, WSDL, or
  confirmed MRW documentation.
