# Refactor Plan - Native Odoo Delivery Carrier

## Goal

Refactor `mrw_shipping_connector` from a standalone-only MRW workspace into a
hybrid native Odoo delivery connector based on:

- `delivery.carrier`
- `stock.picking`
- `stock_delivery`

Manual MRW shipments remain supported through `MRW Shipments`.

## Current State

The current module has proven useful for API validation:

- WSDL connection and inspection work.
- `TransmEnvio` national TEST shipment creation works.
- `GetEtiquetaEnvio` national TEST label retrieval works.
- PDF label storage works.
- `CancelarEnvio` request structure is confirmed, with business-state rejection
  handled safely.

The current module shape is not the final architecture:

- manual `mrw.shipping.shipment` records are valid, but they must become one of
  two supported entry points, not the only flow;
- menus expose an MRW workspace before Odoo delivery is integrated;
- dependencies are still `base` and `contacts`;
- `delivery.carrier` is not extended yet.

Target flow:

```text
Manual shipment:
MRW Shipments -> MRW API

Odoo shipment:
stock.picking -> delivery.carrier(mrw) -> MRW Shipment audit -> MRW API
```

## Phase 1 - Discovery Before Code

Inspect local Odoo 18 source for:

- `delivery.carrier` method signatures and expected return dictionaries.
- `stock_delivery` fields on `stock.picking`.
- native storage of tracking references.
- native delivery label behavior.
- examples of built-in carriers in Odoo 18.

Deliverable:

- short implementation notes with exact method signatures and native fields.

Status:

- documented in `ODOO_DELIVERY_CONTRACTS.md`.

## Phase 2 - Manifest And Dependencies

Update the module to depend on:

```python
[
    "delivery",
    "stock_delivery",
]
```

Remove standalone-app positioning where appropriate.

Risk:

- view/menu/security changes may be needed because the module will no longer be
  a self-contained app.

## Phase 3 - Extend `delivery.carrier`

Create or update a model extension for `delivery.carrier`:

- add `mrw` to `delivery_type`;
- add MRW configuration relation;
- add MRW service relation or service code;
- add MRW label options if needed;
- add MRW production safeguard flag if needed.

Design choice to validate:

- keep `mrw.shipping.service` and select it from carrier, or store service code
  directly on carrier.

Recommendation:

- keep `mrw.shipping.service` for now, because it protects service-code
  documentation and lets users manage MRW services without code changes.

## Phase 4 - Adapt Mapper Input

Refactor mapper responsibilities:

- current mapper converts `mrw.shipping.shipment` into MRW SOAP payload;
- target mapper converts `stock.picking` + `delivery.carrier` + MRW config into
  MRW SOAP payload.

Keep the SOAP structures already validated.

Do not change confirmed MRW XML names unless new evidence requires it.

## Phase 5 - Implement Send From Picking

Implement:

```python
mrw_send_shipping(pickings)
```

Expected behavior:

- validate carrier/config/service;
- create or update a linked `mrw.shipping.shipment` snapshot;
- prepare MRW request through the existing MRW shipment mapper/client path;
- call MRW TEST/production according to safeguards;
- return `tracking_number` so Odoo writes `carrier_tracking_ref`;
- store MRW request number/effective date/label on the linked audit record;
- fetch/store label if the final flow chooses immediate label retrieval;
- write sanitized logs.

Initial implementation status:

- implemented first native path for done pickings via `mrw_send_shipping`;
- creates linked `mrw.shipping.shipment`;
- returns MRW `NumeroEnvio` as native tracking number;
- stores label attachment on picking when `mrw_label_on_send` is enabled;
- requires positive shipping weight.

Open decision:

- whether `send_shipping` should also fetch the label immediately or leave label
  retrieval as a separate picking action. Current validated flow supports both
  create and label retrieval.

## Phase 6 - Tracking Link

Implement:

```python
mrw_get_tracking_link(picking)
```

Current rule:

- private tracking only.
- no public MRW tracking API or URL has been confirmed.

Until confirmed, return no public URL or a conservative internal-only value
according to native Odoo expectations.

## Phase 7 - Cancellation

Implement:

```python
mrw_cancel_shipment(pickings)
```

Use confirmed MRW operation:

```text
CancelarEnvio
request/CancelaEnvio/NumeroEnvioOriginal
```

Rules:

- only call MRW when a shipment number exists;
- only mark as cancelled when MRW returns `Estado = 1`;
- if MRW returns `Estado = 0`, preserve coherent Odoo state and log the message;
- keep production cancellation behind an explicit safeguard.

## Phase 8 - UI Cleanup

Make the standard shipping UX live in:

- Inventory delivery orders;
- Odoo shipping methods/carriers;
- MRW carrier configuration fields.

Keep `MRW Shipments` for:

- direct MRW tests;
- manual shipments unrelated to other documents;
- technical/audit inspection for pickings.

The UI should clearly distinguish manual records from picking-generated records.

Keep technical logs available to administrators.

## Phase 9 - Tests

Add/update tests for:

- carrier field validation;
- mapper from picking to MRW request;
- response parsing;
- label storage;
- cancellation rejection handling;
- payload sanitization.

Live MRW tests must remain manual/controlled.

## Explicit Non-Goals

- No dependency on `wex_logistics_core`.
- No dependency on `wex_logistics_repair`.
- No bridge module to Wex logistics.
- No parallel logistics-provider model.
- No public tracking flow until confirmed.
- No invented MRW API operations.
