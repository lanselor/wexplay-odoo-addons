# Decision Log - MRW Shipping Connector

## 2026-05-03 - Generic module name

Decision:

Use `mrw_shipping_connector` as the technical addon name.

Reason:

- The module should be generic and potentially publishable.
- It must not include Wexplay-specific naming.
- The name clearly communicates MRW shipping integration.

Consequences:

- Model namespace should be `mrw.shipping.*`.
- Future customer-specific behavior must live in separate modules.

## 2026-05-03 - Independent MVP

Status: superseded on 2026-05-06.

Decision:

The MVP is independent and does not depend on `stock`, `sale`, or `repair`.

Reason:

- The first validation should happen without coupling to other Odoo business
  flows.
- Integrations can be added later once the MRW base flow is proven.

Consequences:

- Shipments are created manually from the MRW module.
- Future integration modules will bridge into `stock.picking`, sales, or repairs.

Superseding decision:

- The connector must use Odoo's native `delivery.carrier` and `stock_delivery`
  flow.
- Manual `mrw.shipping.shipment` records may remain only as technical/audit
  records or direct manual MRW shipments.
- No bridge to Wex logistics modules should be created.

## 2026-05-03 - Config model instead of only settings

Decision:

Use `mrw.shipping.config` as the main storage for MRW credentials and endpoints.

Reason:

- The design must support more than one configuration per company/branch in the
  future.
- `res.config.settings` is better as a shortcut, not as the source of truth for
  multiple configurations.

Consequences:

- Credentials are records with explicit access controls.
- A future settings screen may point to the default config.

## 2026-05-03 - Service catalog as Odoo data

Decision:

Use `mrw.shipping.service` records for MRW service codes.

Reason:

- No MRW API operation was found to fetch services.
- Service codes should not be hardcoded in Python logic.
- Users must be able to add or disable services from Odoo.

Initial records:

- `0230` - Bag 19 - national.
- `0205` - Urgente 19 Expedicion - national.
- `BOX25` - Ecobox 25 - international.

Consequences:

- The mapper sends `service_id.code` as `CodigoServicio`.
- Extra services can be added without code changes.

## 2026-05-03 - Logs store sanitized payloads

Decision:

Store full SOAP request/response payloads when available, but sanitized.

Reason:

- SOAP integrations need detailed troubleshooting during early validation.
- Secrets must never be persisted in logs.

Sanitized fields:

- `Password`
- `UserName`
- `CodigoAbonado`
- `CodigoFranquicia`

Consequences:

- Technical logs are restricted to administrators/managers.
- A helper such as `_sanitize_payload()` must exist before logs are written.

## 2026-05-03 - Flexible label payload handling

Decision:

Do not assume a single `EtiquetaFile` encoding in the design.

Reason:

- The legacy PHP module writes `EtiquetaFile` directly to a PDF file.
- Comments/variable names suggest base64, but no `base64_decode` call was found.

Consequences:

- Implementation must detect whether the payload is direct PDF or base64.
- Tests should cover both cases.

## 2026-05-03 - Cancellation disabled until API evidence

Decision:

Prepare internal states for cancellation, but do not implement external
cancellation until a real MRW API method is confirmed.

Reason:

- No cancellation method was found in the legacy module.
- Inventing a method would be unsafe.

Consequences:

- `cancel_pending` and `cancelled` can exist in the state machine.
- External cancellation action should be hidden or disabled initially.

## 2026-05-03 - Private tracking only

Decision:

Store MRW shipment number privately. Do not expose public tracking in the MVP.

Reason:

- No tracking SOAP operation was found.
- The current requirement is private tracking only.

Consequences:

- Store `mrw_shipment_number`.
- Public tracking URL can be added later if needed.

## 2026-05-03 - WSDL connection test

Decision:

Add a non-destructive connection test button on MRW configurations.

Reason:

- It is useful to verify that the Odoo server can reach the configured MRW WSDL.
- It does not create shipments, request labels, or send credentials.
- No confirmed MRW auth-only operation was found.

Consequences:

- The test fetches the selected WSDL URL and checks that the response looks like
  a WSDL document.
- A technical log is created with operation `test_connection`.
- A successful result does not prove that credentials are valid; it only proves
  endpoint reachability.

## 2026-05-03 - WSDL operation inspection

Decision:

Add a non-destructive WSDL inspection button on MRW configurations.

Reason:

- Before enabling credential or shipment tests, the connector should verify the
  operations declared by the live WSDL.
- It lets us confirm operation names such as `TransmEnvio`, `EtiquetaEnvio`,
  `TransmEnvioInternacional`, and `EtiquetaEnvioInternacional` from the endpoint
  itself.

Consequences:

- The inspection downloads and parses the configured WSDL.
- It stores the detected operation names on the configuration.
- It writes a technical log with operation `inspect_wsdl`.
- It still does not send credentials or execute business operations.

## 2026-05-04 - Offline request preview

Decision:

Add offline request preview actions on shipments before enabling real SOAP calls.

Reason:

- We need to validate the Odoo to MRW mapping against known PrestaShop evidence
  and WSDL operation names before sending any business operation to MRW.
- Previewing the payload is safer than jumping directly to `TransmEnvio`.

Consequences:

- `Preview MRW Request` prepares the payload for `TransmEnvio` or
  `TransmEnvioInternacional` depending on shipment type.
- `Preview Label Request` prepares the payload for `EtiquetaEnvio` or
  `EtiquetaEnvioInternacional`, but only when a shipment number exists.
- The generated preview is stored on the shipment and logged as technical data.
- No network call is made.

## 2026-05-07 - Manual customer pickup direction

Decision:

Support manual national customer pickup requests from `MRW Shipments`.

Reason:

- The MRW WSDL declares `DatosRecogida`, `DatosEntrega`, and `DatosServicio` in
  `TransmEnvioRequest`.
- The legacy PrestaShop module also used `DatosRecogida`, although only for
  changing the sender pickup address.
- The requested operational need is to collect at the customer address and
  deliver to the configured company address.

Consequences:

- `mrw.shipping.shipment` has a direction field: `Entrega al cliente` or
  `Recogida en cliente`.
- Customer pickup uses `TransmEnvio` with `DatosRecogida` = customer and
  `DatosEntrega` = company.
- Pickup is currently national-only.
- Manual pickups can create a linked incoming `stock.picking` so Odoo expects
  the product from the customer in inventory.
- `TransmEnvioEC` / `TransmitirEnvioEC` remain unimplemented until their real
  business meaning is confirmed with MRW.

## 2026-05-04 - TEST national MRW flow validated

Decision:

Enable and keep the controlled TEST-only national flow for `TransmEnvio` and
`EtiquetaEnvio`.

Evidence:

- `TransmEnvio` in TEST returned `Estado = 1`.
- MRW returned `NumeroSolicitud` and `NumeroEnvio`.
- MRW adjusted the pickup date in `Mensaje`; the connector stores that as
  `mrw_effective_shipping_date`.
- `EtiquetaEnvio` succeeded only after using the WSDL input wrapper
  `GetEtiquetaEnvio`.
- `EtiquetaFile` was returned and stored successfully as a PDF attachment.
- The generated PDF `01400F001137.pdf` was opened successfully by the user.

Consequences:

- National creation and label retrieval are validated in TEST.
- Production remains blocked until explicitly enabled later.
- Label logs must keep masking `EtiquetaFile`.
- Future label debugging should compare WSDL input element names, not only
  binding operation names.

## 2026-05-04 - Cancellation enabled only in TEST

Decision:

Add an offline `CancelarEnvio` preview and enable the real call only for TEST
configurations.

Evidence:

- The WSDL declares `CancelarEnvio`.
- The request schema contains `request/CancelaEnvio/NumeroEnvioOriginal`.
- The response schema extends the common MRW response and includes
  `NumeroSolicitud` and `NumeroEnvio`.

Reason:

- A real cancellation changes MRW state and should be validated first with an
  intentionally cancellable TEST shipment.

Consequences:

- Users can inspect the cancellation SOAP payload.
- `Request Cancellation` sends `CancelarEnvio` only in TEST.
- The shipment reaches `cancelled` only when MRW returns `Estado = 1`.
- If MRW returns `Estado = 0`, Odoo restores the previous shipment state and
  stores the MRW message as `last_error`.
- Production cancellation remains blocked until explicitly enabled later.

## 2026-05-04 - MRW PrestaShop guide reviewed

Decision:

Use the official PrestaShop installation guide as operational evidence only,
not as an API contract.

Evidence:

- The guide confirms SAGEC credentials: franchise, subscriber, optional
  department, user name, and password.
- It confirms TEST and PRO environments and recommends validating TEST
  shipments before requesting PRO activation.
- It confirms multiple subscribers, with only one default subscriber.
- It confirms configurable default national/international services and
  shipment-level overrides before MRW transmission.
- It confirms manual or automatic label generation and server-side label
  storage.
- It does not provide endpoint URLs, SOAP actions, request XML, response XML,
  service catalog API, tracking API, cancellation payload, or label encoding
  details.

Consequences:

- Keep using PHP source, WSDL inspection, and live TEST logs as the source of
  truth for API structures.
- Keep multiple configurations/subscribers in Odoo.
- Keep production calls blocked until an explicit go-live decision and MRW
  validation process are handled.
- Keep generated label PDFs attached and easy to export because MRW Field
  Support may request several labels before approving production use.

## 2026-05-06 - Native Odoo carrier architecture

Decision:

Refactor `mrw_shipping_connector` to follow Odoo's native shipping flow:

- `delivery.carrier` as the carrier/method configuration point.
- `stock.picking` as the operational shipment document.
- `stock_delivery` as the Odoo delivery-picking integration.

The connector must add `delivery_type = "mrw"` and implement the standard MRW
carrier methods:

- `mrw_rate_shipment(order)`
- `mrw_send_shipping(pickings)`
- `mrw_get_tracking_link(picking)`
- `mrw_cancel_shipment(pickings)` where applicable.

Reason:

- Odoo already has a carrier abstraction.
- Creating a parallel logistics core would duplicate native behavior and make
  the connector harder to maintain or publish.
- The final user flow should happen where Odoo users already manage shipping:
  delivery methods and delivery orders.

Consequences:

- `wex_logistics_core` and `wex_logistics_repair` are abandoned for this
  connector.
- `wex.logistics.request`, `wex.logistics.provider`, and
  `wex.logistics.service` must not be used.
- The old standalone MRW workspace is obsolete as the primary UX.
- Existing MRW SOAP client/mapper work remains valuable but must be adapted to
  `stock.picking` input.
- `mrw.shipping.shipment` should not be deleted. It remains useful for manual
  MRW shipments and becomes a technical/audit record linked to `stock.picking`
  and `delivery.carrier` when the shipment comes from Odoo's native flow.
- Before implementation, local Odoo 18 source must be inspected to confirm exact
  method signatures and return structures.

## 2026-05-06 - Odoo delivery contracts inspected

Decision:

Use the exact Odoo 18 `delivery` and `stock_delivery` contracts documented in
`ODOO_DELIVERY_CONTRACTS.md`.

Evidence:

- `delivery.carrier.rate_shipment(order)` dispatches to
  `<provider>_rate_shipment(order)`.
- `stock_delivery.delivery.carrier.send_shipping(pickings)` dispatches to
  `<provider>_send_shipping(pickings)`.
- `send_shipping` expects one result dictionary per picking with
  `exact_price` and `tracking_number`.
- `stock.picking.send_to_shipper()` writes returned `tracking_number` into
  `carrier_tracking_ref`.
- `stock.picking.carrier_tracking_url` is computed from
  `carrier_id.get_tracking_link(picking)`.
- `stock.picking.cancel_shipment()` calls carrier cancellation and then clears
  `carrier_tracking_ref`.

Consequences:

- MRW `NumeroEnvio` should be returned as `tracking_number`.
- MRW `NumeroSolicitud`, effective pickup date, label attachment, raw response,
  and MRW messages should live on MRW fields or the linked
  `mrw.shipping.shipment`.
- If MRW rejects cancellation, `mrw_cancel_shipment` must raise before Odoo
  clears `carrier_tracking_ref`.
- MRW shipping labels must be stored explicitly as `ir.attachment`; the native
  `send_shipping` result does not define label payload transport.

## 2026-05-06 - MRW carrier type added

Decision:

Add the first native Odoo carrier integration layer.

Changes:

- Module dependencies now include `delivery` and `stock_delivery`.
- `delivery.carrier.delivery_type` is extended with `mrw`.
- MRW carriers select an `mrw.shipping.config`.
- MRW carriers select an `mrw.shipping.service`.
- The delivery carrier form has an MRW page for carrier-specific settings.

Current limits:

- `mrw_send_shipping(pickings)` is intentionally blocked with a clear
  `UserError` until the picking-to-MRW mapping phase is implemented.
- `mrw_cancel_shipment(pickings)` is intentionally blocked until the linked
  picking/audit flow exists.
- `mrw_rate_shipment(order)` does not call MRW because no MRW rating API has
  been confirmed; it uses the configured delivery product price.

Consequences:

- Users can configure Odoo-native MRW delivery methods now.
- Manual TEST shipments through `MRW Shipments` remain the working path for real
  MRW API calls until the next phase.

## 2026-05-06 - First picking send path

Decision:

Wire the first native Odoo send path from `stock.picking` to the existing MRW
shipment logic.

Changes:

- `stock.picking` now has `mrw_shipment_id`.
- `mrw.shipping.shipment` now has:
  - `source`
  - `picking_id`
  - `carrier_id`
- `mrw_send_shipping(pickings)` creates or reuses a linked MRW shipment.
- The linked shipment is prepared, sent to MRW, and optionally labelled using
  the existing validated MRW client/mapper flow.
- MRW `NumeroEnvio` is returned as Odoo's `tracking_number`, so Odoo writes it
  into `stock.picking.carrier_tracking_ref`.
- Labels generated from picking flow are attached to the picking while still
  referenced by the MRW shipment record.

Rules:

- Manual `MRW Shipments` remains supported.
- Picking-created shipments are audit/technical records linked to their picking.
- Picking-created MRW shipments must be based on outgoing delivery orders only;
  internal transfers, including repair-location movements, are not valid MRW
  shipment sources.
- Production remains protected by the existing MRW config environment checks.
- A picking must have positive shipping weight before being sent to MRW.
- If MRW rejects shipment creation, the carrier method raises `UserError` so
  Odoo does not write a false tracking result.
- If MRW creates the shipment but label retrieval fails, Odoo keeps the MRW
  tracking number and logs/posts the label error so the label can be retried
  without losing the remote shipment reference.
- If MRW rejects cancellation, the carrier method raises `UserError` before
  Odoo clears an existing tracking reference.

## 2026-05-06 - Outgoing picking guardrail

Decision:

Reject MRW carrier sends from non-outgoing pickings before any SOAP call.

Reason:

- Odoo repair/SAT flows may generate internal transfers to repair locations.
- Those moves are operationally valid inside Odoo, but they are not a delivery
  to the customer and should not create an MRW expedition.
- The MRW API needs a real delivery destination; using an internal stock
  location would create confusing intermediate states.

Consequences:

- `mrw_send_shipping` only supports outgoing delivery orders.
- For SAT/service workflows, the commercial order must generate an outgoing
  delivery order if a real MRW shipment is required.
- Label retrieval failures after successful MRW creation no longer roll back
  the local tracking reference; they are kept as retryable errors.

## 2026-08-21 - Tracking SOAP validation isolated from shipment operations

Decision:

Add a first, manual MRW SOAP tracking path based on the publicly available
`SeguimientoNumeroEnvioMRWNacional` WSDL contract and the legacy PrestaShop
tracking module.

Rules:

- The tracking WSDL endpoint and opt-in switch live in `mrw.shipping.config`.
- A configuration action checks only WSDL reachability and the national
  tracking operation; it does not send credentials.
- A manual action on a shipment with an MRW number performs the real query.
- The query stores sanitized request/response logs and returned tracking data,
  but never changes the Odoo shipment state or notifies customers.
- International tracking, proof of delivery, scheduled polling, portal output,
  and delivery-state automation remain pending validation.

## 2026-08-21 - Preserve malformed tracking responses for diagnosis

Decision:

When MRW returns a tracking response that cannot be parsed as XML, retain its
sanitized raw content in the technical log together with the sanitized request.

Reason:

The live endpoint can return malformed XML. Without the response body, the
integration cannot distinguish a transient MRW response defect from an
unhandled response shape.

Consequences:

- The response remains available only through restricted technical logs.
- Passwords remain masked before any request is persisted.
- The error remains non-destructive; no Odoo shipment state is changed.

Reason:

The evidence confirms a national SOAP operation and response fields, but does
not yet establish stable mappings for all MRW states or the operational rules
needed for automatic business actions.
