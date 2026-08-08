# Architecture - MRW Shipping Connector

## Architectural Reset

Decision date: 2026-05-06.

The previous standalone logistics-workspace approach is obsolete.

The connector must now follow Odoo's native delivery architecture:

- carrier configuration: `delivery.carrier`
- operational shipment document: `stock.picking`
- delivery integration module: `stock_delivery`

The module must not depend on, bridge to, or design around:

- `wex_logistics_core`
- `wex_logistics_repair`
- `wex.logistics.request`
- `wex.logistics.provider`
- `wex.logistics.service`

Those modules are considered abandoned for this MRW connector.

## Purpose

`mrw_shipping_connector` is a generic Odoo 18 Community connector for MRW
shipments using Odoo's standard carrier flow.

The user-facing shipping method must be a `delivery.carrier` record such as:

- MRW Bag 19
- MRW Urgente 19
- MRW 14H

The user-facing shipping operation must happen from Odoo's normal delivery
flow on `stock.picking`, through `stock_delivery`.

The existing `mrw.shipping.shipment` model remains part of the design. It has a
hybrid role:

- manual MRW shipment screen for direct tests and shipments that do not come
  from sales, purchases, repairs, or pickings;
- technical/audit record when the shipment is generated from `stock.picking`.

It must not become a parallel logistics core. It is carrier-specific MRW
infrastructure and manual tooling.

## Odoo Compatibility

- Odoo 18 Community.
- On-premise installations.
- Standard Odoo Python stack.
- No Odoo Studio dependency.
- No Enterprise dependency.

## Addon Name

Technical addon name:

```text
mrw_shipping_connector
```

This remains valid because it is generic and not Wexplay-specific.

## Required Dependencies

Target dependencies after refactor:

```python
[
    "delivery",
    "stock_delivery",
]
```

`stock_delivery` brings the standard relation between delivery carriers and
pickings. `delivery` provides `delivery.carrier` and the carrier method pattern.

Do not add `sale` unless a later phase explicitly needs sale-order rating or
checkout behavior. `delivery` already defines rating hooks that can be harmless
or minimally implemented.

## Native Odoo Extension Points

The connector must extend `delivery.carrier`:

```text
delivery.carrier
  delivery_type = "mrw"
```

Confirmed Odoo carrier methods:

```python
mrw_rate_shipment(order)
mrw_send_shipping(pickings)
mrw_get_tracking_link(picking)
mrw_cancel_shipment(pickings)
```

Behavioral intent:

- `mrw_rate_shipment(order)`: no live MRW rating is confirmed. It should return
  configured/fallback behavior only, without inventing an MRW rate API.
- `mrw_send_shipping(pickings)`: create the MRW shipment from the picking data,
  store MRW shipment number/tracking on the picking, and fetch/store label if
  the chosen flow does so.
- `mrw_get_tracking_link(picking)`: return the confirmed MRW public historical
  tracking URL when an MRW shipment/tracking reference exists.
- `mrw_cancel_shipment(pickings)`: call `CancelarEnvio` only where supported and
  only after the usual TEST/production safeguards.

See `ODOO_DELIVERY_CONTRACTS.md` for the inspected Odoo 18 method signatures,
return structures, and stock delivery fields.

## Target Model Responsibilities

### `delivery.carrier`

Primary configuration for a shipping method.

MRW-specific fields should be added here or linked from here:

- MRW service code or service record.
- MRW configuration/account.
- default label format/options.
- flags for TEST/production behavior.
- optional MRW-specific delivery options when confirmed.

Each MRW service visible to users should normally be one `delivery.carrier`
record. Example: one carrier for Bag 19 and another carrier for Urgente 19.

### `mrw.shipping.config`

Stores MRW account credentials and endpoints.

This model can still provide value because credentials are not the same concept
as an Odoo carrier method. A company can have multiple MRW accounts/configs.

Target fields remain:

- company
- environment
- test WSDL URL
- production WSDL URL
- franchise code
- subscriber code
- department code
- user name
- password
- active/default flags

It should be selectable from `delivery.carrier`.

### `mrw.shipping.service`

Stores MRW API service codes if it continues to add value.

Alternative target design:

- keep `mrw.shipping.service` as a normalized MRW service-code catalog, and
  select it from `delivery.carrier`; or
- store the MRW service code directly on each MRW `delivery.carrier`.

Preferred first refactor: keep `mrw.shipping.service`, because it already
documents service codes and avoids scattering MRW codes in logic. The user still
configures actual shipping methods through `delivery.carrier`.

### `stock.picking`

Primary operational record.

MRW data should be visible from the picking, using native delivery fields where
possible:

- carrier/method: native `carrier_id`
- tracking reference: native carrier tracking field if available in Odoo 18
- MRW shipment number
- MRW request number
- effective MRW pickup date
- label attachment
- last MRW error/message

Before implementation, inspect Odoo 18's exact `stock_delivery` fields to avoid
duplicating native tracking/label fields.

### `mrw.shipping.shipment`

MRW-specific shipment record.

It remains user-facing for manual MRW shipments and becomes an audit record for
pickings.

### Customer Notifications

Customer communication belongs to `mrw.shipping.shipment`, because that record
is shared by manual MRW operations, native outgoing pickings, and SAT pickups.

The first implementation provides manual send and resend only. It uses native
`mail.template` records and stores every attempt in `mrw.shipping.notification`.
Two events are supported:

- shipment created: tracking number and public MRW tracking link;
- pickup label ready: only for customer pickups and with the private PDF label
  attached to the email.

No public label URL is created. Automatic sends and delivered-status emails are
deferred until their operational rules and a reliable MRW status source are
validated.

Manual use case:

```text
mrw.shipping.shipment
  -> MRW SOAP
  -> label / tracking / logs
```

Native Odoo use case:

```text
stock.picking
  -> delivery.carrier(mrw)
  -> mrw.shipping.shipment
  -> MRW SOAP
  -> label / tracking / logs
```

Manual customer pickup use case:

```text
mrw.shipping.shipment(movement_type="pickup")
  -> MRW SOAP TransmEnvio
  -> DatosRecogida = customer
  -> DatosEntrega = company
  -> optional incoming stock.picking
```

The optional incoming picking lets Odoo expect and receive the item from the
customer. This is inventory-level traceability only for the generic connector.
It does not by itself create, update, or link an RMA/SAT/repair record.

Wexplay-specific repair bridge currently implemented outside this generic
connector:

```text
repair.order
  -> wex.repair.shipping.operation(type="pickup")
  -> mrw.shipping.shipment(movement_type="pickup")
  -> MRW SOAP TransmEnvio
  -> optional incoming stock.picking
```

That bridge lives in `wexplay_repair_delivery`, which depends on this addon and
reuses the same `mrw.shipping.shipment`, mapper, label handling, and technical
logs. It also consumes the MRW public tracking link from the repair shipping
operation and from `repair.order`. The generic MRW connector remains carrier
infrastructure; repair-specific workflow ownership stays outside this module.

Additional target links:

- link to `stock.picking`
- link to `delivery.carrier`
- link to `mrw.shipping.config`
- MRW operation numbers
- sanitized request/response references
- label attachment reference
- last MRW state/error

Rules:

- if `picking_id` is empty, it is a manual MRW shipment;
- if `picking_id` is set, it is an audit/technical record for a native Odoo
  picking shipment;
- picking-generated MRW shipments must only be created from outgoing delivery
  orders, never from internal transfers or receipts;
- both paths must reuse the same MRW mapper/client/service code;
- pickup-generated incoming pickings are optional and must not be confused with
  the MRW SOAP request itself;
- RMA/SAT/repair integration from those incoming pickings is outside the
  current implemented connector scope.

SAT or service-order flows can still create MRW shipments through Odoo's native
route, but they must produce an outgoing delivery order to the customer. An
auxiliary sellable/consumable product may represent "delivery/collection" in
the commercial document, but the carrier call belongs to the outgoing picking,
not to an internal repair-location transfer.

Repair-specific exception already in place:

- `wexplay_repair_delivery` can create MRW customer pickups directly from a
  repair shipping operation without first requiring an outgoing picking,
  because the business event is a reverse pickup from the customer to Wexplay;
- when that repair flow also creates an incoming picking, it links the picking
  back to the same `mrw.shipping.shipment` record for audit continuity;
- this exception is intentionally implemented in the Wexplay glue module, not
  in the generic MRW connector.

### `mrw.shipping.package`

May be retained as technical package audit lines if native picking package data
is insufficient.

Before implementing, inspect how Odoo 18 exposes packages/weights on pickings
and avoid duplicating native package records unless the MRW SOAP structure needs
a stable snapshot.

### `mrw.shipping.log`

Keep as technical log/audit model.

Logs remain valuable for SOAP integrations. They must continue to sanitize:

- `Password`
- `UserName`
- `CodigoAbonado`
- `CodigoFranquicia`
- `EtiquetaFile`

## API Evidence Kept

The API findings remain valid:

- SOAP/XML through MRW SAGEC.
- TEST WSDL: `https://sagec-test.mrw.es/MRWEnvio.asmx?WSDL`
- PROD WSDL: `https://sagec.mrw.es/MRWEnvio.asmx?WSDL`
- AuthInfo SOAP header.
- `TransmEnvio` for national shipment creation.
- `GetEtiquetaEnvio` wrapper for national label requests.
- `CancelarEnvio` exists and is implemented only with safeguards.

The mapper must support two input paths:

- direct/manual `mrw.shipping.shipment` records;
- `stock.picking` snapshots converted into or linked to an
  `mrw.shipping.shipment`.

## Refactor Phases

### Phase A - Documentation And Current-State Freeze

- Mark the standalone-only architecture obsolete.
- Keep manual MRW shipments as a supported path.
- Remove abandoned logistics-core references.
- Keep current working SOAP code as evidence, not as final UX.
- Do not delete current models in this phase.

### Phase B - Inspect Native Odoo Delivery Contracts

Before code changes, inspect local Odoo 18 source for:

- `delivery.carrier` extension conventions.
- expected return shape of `*_rate_shipment`.
- expected return shape of `*_send_shipping`.
- `stock_delivery` fields on `stock.picking`.
- native label/tracking behavior.
- native cancel behavior.

No method signature should be guessed.

### Phase C - Carrier Model Integration

- Add dependency on `delivery` and `stock_delivery`.
- Extend `delivery.carrier`.
- Add `delivery_type = "mrw"`.
- Add MRW fields on carrier or relations to MRW config/service.
- Seed/update MRW carriers as data or let users create them.

### Phase D - Picking Send Flow

- Implement `mrw_send_shipping(pickings)`.
- Build MRW payload from `stock.picking`, partner, company, package/weight data,
  and selected MRW carrier service.
- Reject non-outgoing pickings before any SOAP call.
- Reuse existing `MRWMapper`/`MRWClient` after adapting their input layer.
- Store MRW response on picking and technical audit record.
- Store label attachment linked to picking.

### Phase E - Tracking And Label UX

- Use native Odoo fields/actions where possible.
- Add smart buttons only if native UX is insufficient.
- Keep generated labels as `ir.attachment`.
- Public MRW historical tracking is now exposed where a confirmed tracking
  reference exists.
- Tracking SOAP enrichment remains optional future work if MRW evidence improves.

### Phase F - Cancellation

- Wire `mrw_cancel_shipment(pickings)` to `CancelarEnvio`.
- Preserve current rule: only mark cancelled when MRW returns `Estado = 1`.
- If MRW returns `Estado = 0`, keep the picking coherent and log the MRW
  message.
- Production cancellation remains disabled until explicitly allowed.

### Phase G - Decommission/Refine Standalone UX

After native picking flow is validated:

- keep `MRW Shipments` available for manual shipments and technical audit;
- make clear in menus/views whether a record is manual or picking-generated;
- migrate any existing standalone test records only if needed;
- simplify security and views.

## Production Guardrails

Production calls must remain guarded until:

- TEST create shipment works from `stock.picking`;
- TEST label retrieval works from `stock.picking`;
- TEST multibulto is validated;
- TEST error cases are logged cleanly;
- MRW/franchise production validation process is explicitly accepted.

## Obsolete Decisions

The following previous decisions are superseded:

- independent MRW shipment workspace as the MVP direction;
- future bridge modules to Wex logistics modules;
- treating stock/sale/repair integration as optional later modules;
- creating a logistics core parallel to Odoo's carrier flow.

Not obsolete:

- keeping `MRW Shipments` as manual MRW shipment tooling;
- keeping `mrw.shipping.shipment` as carrier-specific audit/technical record.
