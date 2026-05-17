# MRW Shipping Connector

Generic Odoo 18 Community module for MRW shipping integration.

This module is intentionally not Wexplay-specific. It is designed as a reusable
MRW connector using Odoo's native delivery-carrier flow.

Current architectural direction: standard Odoo carrier integration:

- carrier configuration: `delivery.carrier`
- operational document: `stock.picking`
- delivery integration: `stock_delivery`

The earlier standalone-only direction is obsolete, but `MRW Shipments` remains
useful and supported as a manual shipment/test screen and as technical audit for
pickings generated through Odoo's native delivery flow.

## Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md): Odoo module architecture and data model.
- [REFACTOR_PLAN.md](REFACTOR_PLAN.md): phased plan for moving to native
  `delivery.carrier` / `stock_delivery`.
- [ODOO_DELIVERY_CONTRACTS.md](ODOO_DELIVERY_CONTRACTS.md): inspected Odoo 18
  carrier and picking method contracts.
- [MRW_API_FINDINGS.md](MRW_API_FINDINGS.md): MRW API evidence extracted from the
  legacy PrestaShop module.
- [MRW_PRESTASHOP_GUIDE_NOTES.md](MRW_PRESTASHOP_GUIDE_NOTES.md): operational
  notes extracted from MRW's official PrestaShop installation guide.
- [DECISION_LOG.md](DECISION_LOG.md): validated decisions and open questions.
- [IMPLEMENTATION_CHECKLIST.md](IMPLEMENTATION_CHECKLIST.md): phased build plan.
- [PROJECT_PENDING.md](PROJECT_PENDING.md): global pending items across MRW,
  inventory, RMA, and SAT flows.
- [QUICKSTART.md](QUICKSTART.md): quick installation and TEST validation guide.
- [PRODUCTION.md](PRODUCTION.md): production go-live guardrails.
- [MANUAL_CONFIGURACION_ES.md](MANUAL_CONFIGURACION_ES.md): manual de
  configuración en castellano.
- [MANUAL_USO_MRW_ES.md](MANUAL_USO_MRW_ES.md): manual de uso del flujo manual
  MRW en castellano.

## Technical Name

`mrw_shipping_connector`

Reasoning:

- Generic enough for possible publication.
- Does not include customer or project-specific naming.
- Clear domain: MRW shipping.
- Leaves room for future glue modules such as `mrw_shipping_stock`.

## Target Odoo Integration

The connector must extend:

- `delivery.carrier` with `delivery_type = "mrw"`
- standard Odoo carrier hooks such as `mrw_send_shipping(pickings)`
- `stock.picking` through native `stock_delivery` behavior

Each MRW shipping method should be configured as an Odoo carrier record, for
example:

- MRW Bag 19
- MRW Urgente 19
- MRW 14H

Manual MRW shipments remain valid:

```text
MRW Shipments -> MRW API
```

Native Odoo shipments use:

```text
stock.picking -> delivery.carrier(mrw) -> MRW API
```

In both cases the connector should reuse the same MRW SOAP client, mapper,
label handling, and logging.

Manual MRW shipments also support two operation directions:

- `Entrega al cliente`: WSDL `TransmEnvio` with `DatosEntrega` as the customer
  address.
- `Recogida en cliente`: WSDL `TransmEnvio` with `DatosRecogida` as the customer
  address and `DatosEntrega` as the configured company address.

Customer pickups are supported in two ways:

- manual MRW records from `MRW Shipments`
- Wexplay SAT pickup operations through `wexplay_repair_delivery`

In both cases an optional incoming `stock.picking` can be created so Odoo
expects the item physically from the customer.

Current native picking status:

- MRW delivery carriers can be configured.
- A done delivery order can call Odoo's standard `Send to Shipper` action.
- The connector creates a linked `MRW Shipment` audit record.
- MRW `NumeroEnvio` is returned as Odoo's tracking reference.
- Public MRW tracking URL is exposed through Odoo tracking hooks and can be
  consumed from linked Wexplay SAT flows.
- If configured, the MRW label is requested and attached to the picking.
- MRW cancellation is exposed from the delivery order and keeps Odoo coherent
  if MRW rejects the cancellation.
- International operations exist behind an explicit configuration switch and
  still require live TEST validation with a non-Spain destination.
- The configuration screen includes a non-destructive diagnostic action that
  checks credentials, default services, and WSDL reachability/operations.

## Internal Model Namespace

`mrw.shipping.*`

Internal/audit models may remain:

- `mrw.shipping.config`
- `mrw.shipping.service`
- `mrw.shipping.shipment`
- `mrw.shipping.package`
- `mrw.shipping.log`

## Target Scope

Initial scope:

- Configurable MRW credentials and WSDL URLs.
- MRW delivery carriers based on Odoo `delivery.carrier`.
- Non-destructive WSDL connection test from MRW configurations.
- Non-destructive WSDL inspection to list declared SOAP operations.
- MRW request preview/debug tools adapted to picking/carrier records.
- Configurable MRW services preloaded from the legacy PrestaShop service
  catalog.
- Shipment creation from `stock.picking`.
- Manual national customer pickup requests from `MRW Shipments`.
- Linked incoming picking creation for manual customer pickups.
- Wexplay SAT pickup bridge through `wexplay_repair_delivery`.
- Label storage as `ir.attachment`.
- Public MRW historical tracking link.
- Technical logs with sanitized SOAP request/response payloads.
- Explicit production-call guardrail.

Out of scope for the first implementation:

- `sale.order` integration.
- Automatic RMA/SAT/repair creation from a validated incoming pickup.
- QZ Tray direct printing.
- Credential validation, because no auth-only MRW operation has been confirmed.
- Live rating API, because no MRW rating operation has been confirmed.
- Exact MRW cost calculation, because real invoice cost may depend on
  account-specific billing variables such as mileage.
- Tracking SOAP integration, because only the public historical tracking URL is
  currently evidenced and implemented.
- Any dependency on Wex logistics modules.

## References

- Odoo 18 coding guidelines:
  https://www.odoo.com/documentation/18.0/contributing/development/coding_guidelines.html
- OCA module maturity guidance:
  https://odoo-community.org/page/module-maturity-levels
