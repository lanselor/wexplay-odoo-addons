# Implementation Checklist - MRW Shipping Connector

This checklist supersedes the old standalone-workspace checklist.

The connector must follow Odoo's native delivery architecture:

- `delivery.carrier`
- `stock.picking`
- `stock_delivery`

Do not implement against `wex_logistics_core`, `wex_logistics_repair`, or any
custom logistics abstraction.

## Phase 0 - Reset And Discovery

- Mark obsolete standalone architecture in documentation. Done.
- Preserve manual `MRW Shipments` as a supported direct MRW/test flow. Done.
- Remove logistics-core review from active docs. Done.
- Inspect local Odoo 18 source for:
  - `delivery.carrier` method signatures.
  - `stock_delivery` fields on `stock.picking`.
  - native tracking fields.
  - native label behavior.
  - examples of built-in carrier connectors.

Acceptance:

- Exact native contracts are documented before code changes. Done in
  `ODOO_DELIVERY_CONTRACTS.md`.
- No guessed return structures.

## Phase 1 - Dependencies And Carrier Extension

- Update manifest dependencies to `delivery` and `stock_delivery`. Done.
- Extend `delivery.carrier`. Done.
- Add `delivery_type = "mrw"`. Done.
- Add/select MRW configuration from carrier. Done.
- Add/select MRW service from carrier. Done.
- Keep service codes out of Python conditionals.

Acceptance:

- MRW appears as a native Odoo delivery carrier type.
- Users can create carriers such as MRW Bag 19 or MRW Urgente 19.
- No custom Wex logistics dependency exists.

## Phase 2 - Preserve Configuration And API Evidence

- Keep `mrw.shipping.config` for MRW credentials/endpoints.
- Keep or simplify `mrw.shipping.service` as MRW service-code catalog.
- Preload the service catalog found in the legacy PrestaShop module. Done.
- Keep `mrw.shipping.log` for sanitized SOAP logs.
- Keep current WSDL inspection/test tools if still useful.

Acceptance:

- Credentials remain protected.
- Logs remain sanitized.
- Service codes remain configurable.

## Phase 3 - Adapt Mapper To Pickings

- Refactor mapper input from `mrw.shipping.shipment` to:
  - `stock.picking`
  - `delivery.carrier`
  - `mrw.shipping.config`
  - package/weight data
- Keep direct `mrw.shipping.shipment` input for manual shipments.
- Preserve confirmed SOAP structures.
- Preserve phone/date/service-code rules already validated.

Acceptance:

- Unit tests validate picking-to-MRW payloads offline.
- Existing confirmed MRW XML names do not regress.

## Phase 4 - Send Shipping From Picking

Implement:

```python
mrw_send_shipping(pickings)
```

Acceptance:

- TEST picking can create an MRW national shipment. Done for the first native path.
- MRW `NumeroEnvio` is stored on/native to the picking. Done through `tracking_number`.
- MRW `NumeroSolicitud` is stored in an MRW field or audit record. Done on linked shipment.
- Non-outgoing pickings are rejected before any SOAP call. Done.
- Manual `MRW Shipments` still works.
- Technical logs are written.
- Production remains guarded.

## Phase 5 - Label Storage

- Decide whether label retrieval happens inside `mrw_send_shipping` or through
  a separate picking action.
- Store generated label PDF as `ir.attachment`. Done.
- Link label to the picking and/or audit record. Done.
- Add albaran actions to retry, open, and download the MRW label without
  opening the technical shipment record. Done.
- Continue masking `EtiquetaFile` in logs.

Acceptance:

- TEST label retrieval from a picking works.
- Open/download label UX is available from the native picking flow.
- If MRW creation succeeds but automatic label retrieval fails, the shipment
  stays linked and the label can be retried. Done.

## Phase 5.1 - Picking UX And Preflight Validation

- Show linked MRW status, request number, effective date, label, and last error
  on the delivery order. Done.
- Keep the MRW shipment smart button for technical/audit drill-down. Done.
- Validate outgoing picking type before API calls. Done.
- Validate destination address before API calls. Done.
- Validate recipient phone before API calls. Done.
- Validate MRW service type against national/international destination before
  API calls. Done.
- Keep positive weight validation before API calls. Done.

## Phase 6 - Tracking Link

Implement:

```python
mrw_get_tracking_link(picking)
```

Acceptance:

- Public historical MRW tracking URL is implemented from confirmed legacy
  evidence. Done.
- Tracking links can be consumed from native Odoo pickings and linked
  Wexplay SAT flows. Done.
- Tracking SOAP enrichment remains pending until validated by MRW.

## Phase 7 - Cancellation

Implement:

```python
mrw_cancel_shipment(pickings)
```

Acceptance:

- Uses confirmed `CancelarEnvio` structure.
- Only reaches cancelled state when MRW returns `Estado = 1`.
- Rejection messages preserve coherent Odoo state and are logged.
- Delivery orders expose explicit MRW cancellation preview/request actions. Done.
- If MRW rejects cancellation, Odoo keeps the tracking reference because the
  carrier method raises before native cleanup. Done.

## Phase 7.1 - International Guardrail

- Keep `TransmEnvioInternacional` and `EtiquetaEnvioInternacional` mapping
  available from the inspected WSDL and existing mapper. Done.
- Add a configuration switch to explicitly enable international SOAP calls.
  Done.
- Block international sends while the switch is disabled. Done.
- Validate the international TEST flow with a real non-Spain destination before
  considering the feature production-ready. Pending.

## Phase 7.2 - Customer Pickup / Reverse Logistics

- Add operation direction on manual MRW shipments:
  - `Entrega al cliente`
  - `Recogida en cliente`
- Map customer pickup using confirmed `TransmEnvioRequest` fields:
  - `DatosRecogida` = customer address
  - `DatosEntrega` = company address
  - `DatosServicio` = national service data
- Keep customer pickup national-only until MRW validates other flows.
- Allow manual customer pickup without inventory movement. Done.
- Allow optional incoming `stock.picking` creation from customer pickup. Done.
- Link the incoming picking back to the MRW shipment. Done.

Acceptance:

- MRW pickup can be requested and labelled from `MRW Shipments`. Done.
- Optional incoming picking can be created and validated. Done.
- Validating the incoming picking only receives stock; it does not create,
  update, or link an RMA/SAT/repair record. Not implemented.
- The RMA/SAT bridge must be designed separately before implementation.

## Phase 8 - Refine Manual/Audit UX

- Keep standalone MRW shipment menus because they are useful for manual
  operations and technical audit. Done by business decision.
- Keep `mrw.shipping.shipment` only as technical/audit record if useful.
- Remove obsolete standalone actions from user-facing menus.
- Add log smart buttons for administrators from shipment and picking. Done.
- Add diagnostics and clearer visual grouping on MRW shipment/configuration
  screens. Done.
- Reduce header clutter by moving secondary actions out of the shipment header.
  Done.
- Polish dynamic labels for pickup fields so "Destinatario" reads as customer
  pickup address in reverse logistics. Pending.

Acceptance:

- Main user workflow is native Odoo delivery.
- No parallel logistics workspace remains visible as the primary flow.

## Phase 9 - Production Guardrails And Documentation

- Keep production SOAP calls blocked unless explicitly enabled on the MRW
  configuration. Done.
- Document TEST quickstart. Done.
- Document production go-live guardrails. Done.
- Keep live rating out until confirmed by MRW evidence. Done.
- Public tracking is now in scope because confirmed MRW historical URL evidence
  was found and implemented. Done.

## Testing strategy

Initial tests should focus on:

- Carrier validation.
- Picking-to-MRW request mapping.
- Response normalization.
- Payload sanitization.
- Label direct-PDF/base64 detection.
- Cancellation rejection handling.

Avoid tests that require live MRW until the offline logic is stable.

## Pre-implementation reminders

- Do not introduce Wexplay-specific names in this module.
- Do not depend on custom Wexplay modules.
- Do not create a parallel logistics core.
- Use native `delivery.carrier` / `stock_delivery`.
- Do not add service-code conditionals in business logic.
- Do not log secrets.
- Do not invent MRW operations.
