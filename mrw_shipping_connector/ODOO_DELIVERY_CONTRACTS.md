# Odoo 18 Delivery Contracts

Inspection date: 2026-05-06.

Local Odoo source inspected:

```text
C:\Program Files\Odoo 18.0.20260220\server\odoo\addons\delivery
C:\Program Files\Odoo 18.0.20260220\server\odoo\addons\stock_delivery
```

## `delivery.carrier`

Source:

```text
C:\Program Files\Odoo 18.0.20260220\server\odoo\addons\delivery\models\delivery_carrier.py
```

Odoo documents the provider extension pattern directly in the model:

```python
delivery_type = fields.Selection(...)
<provider>_rate_shipment(order)
<provider>_send_shipping(pickings)
<provider>_get_tracking_link(picking)
<provider>_cancel_shipment(pickings)
_<provider>_get_default_custom_package_code()
```

For MRW, the provider key should be:

```text
mrw
```

Therefore the target methods are:

```python
mrw_rate_shipment(order)
mrw_send_shipping(pickings)
mrw_get_tracking_link(picking)
mrw_cancel_shipment(pickings)
_mrw_get_default_custom_package_code()
```

## `rate_shipment(order)`

Source method:

```python
delivery.carrier.rate_shipment(order)
```

Expected provider return shape:

```python
{
    "success": bool,
    "price": float,
    "error_message": str | False,
    "warning_message": str | False,
}
```

Odoo then applies taxes, margins, free-shipping rules, and adds:

```python
"carrier_price"
```

MRW note:

- No MRW rating operation has been confirmed.
- `mrw_rate_shipment(order)` must not invent a live MRW rate call.
- First implementation should return a configured/static carrier price or a
  clear non-live result according to standard Odoo behavior.

## `stock_delivery.delivery.carrier.send_shipping(pickings)`

Source:

```text
C:\Program Files\Odoo 18.0.20260220\server\odoo\addons\stock_delivery\models\delivery_carrier.py
```

Signature:

```python
def send_shipping(self, pickings):
```

Dispatch:

```python
getattr(self, "%s_send_shipping" % self.delivery_type)(pickings)
```

Expected provider return shape:

```python
[
    {
        "exact_price": price,
        "tracking_number": number,
    },
]
```

The list must contain one dictionary per picking.

Odoo comments say labels/currency/success/error/warnings are not formalized in
this return contract. Therefore MRW labels should be stored explicitly as
`ir.attachment` linked to the picking and/or `mrw.shipping.shipment`.

## `stock.picking` Delivery Fields

Source:

```text
C:\Program Files\Odoo 18.0.20260220\server\odoo\addons\stock_delivery\models\stock_picking.py
```

Fields added by `stock_delivery`:

```python
carrier_price = fields.Float(...)
delivery_type = fields.Selection(related="carrier_id.delivery_type")
carrier_id = fields.Many2one("delivery.carrier", ...)
weight = fields.Float(compute="_cal_weight", store=True)
carrier_tracking_ref = fields.Char(copy=False)
carrier_tracking_url = fields.Char(compute="_compute_carrier_tracking_url")
weight_uom_name = fields.Char(...)
is_return_picking = fields.Boolean(...)
return_label_ids = fields.One2many("ir.attachment", compute="_compute_return_label")
destination_country_code = fields.Char(related="partner_id.country_id.code")
```

Important native fields for MRW:

- `carrier_id`: selected MRW delivery carrier.
- `delivery_type`: should be `mrw`.
- `carrier_tracking_ref`: should store MRW `NumeroEnvio`.
- `carrier_tracking_url`: computed through carrier `get_tracking_link`.
- `weight`: computed picking weight.

## Sending From Picking

Source method:

```python
stock.picking.send_to_shipper()
```

Relevant behavior:

```python
res = self.carrier_id.send_shipping(self)[0]
self.carrier_price = ...
if res["tracking_number"]:
    ... set carrier_tracking_ref ...
self.message_post(...)
self._add_delivery_cost_to_so()
```

Implications for MRW:

- `mrw_send_shipping(pickings)` must return a tracking number when MRW returns
  `NumeroEnvio`.
- Odoo will place that value into `carrier_tracking_ref`.
- MRW-specific fields such as `NumeroSolicitud`, effective pickup date, raw
  response, and label attachment need MRW-specific fields or the
  `mrw.shipping.shipment` audit record.

## Automatic Send Timing

In `_send_confirmation_email`, Odoo calls `send_to_shipper()` when:

```python
pick.carrier_id
pick.carrier_id.integration_level == "rate_and_ship"
pick.picking_type_code != "incoming"
not pick.carrier_tracking_ref
pick.picking_type_id.print_label
```

The stock delivery form also exposes a manual `Send to Shipper` button when the
picking is done, has a non-fixed provider, and no tracking reference.

Implication:

- MRW integration must be safe when called from standard Odoo validation flows.
- Production safeguards must be checked inside the carrier/send logic, not only
  in custom MRW buttons.

## Tracking Link

Source method:

```python
delivery.carrier.get_tracking_link(picking)
```

Dispatch:

```python
mrw_get_tracking_link(picking)
```

Expected return:

```python
str | False
```

Odoo computes:

```python
stock.picking.carrier_tracking_url
```

MRW note:

- No public tracking URL/API has been confirmed.
- First implementation should return `False` unless a confirmed URL pattern is
  later provided.

## Cancellation

Source methods:

```python
delivery.carrier.cancel_shipment(pickings)
stock.picking.cancel_shipment()
```

`stock.picking.cancel_shipment()` does:

```python
picking.carrier_id.cancel_shipment(self)
picking.message_post(...)
picking.carrier_tracking_ref = False
```

Implication:

- If MRW rejects cancellation, `mrw_cancel_shipment(pickings)` must raise a
  `UserError` before Odoo clears `carrier_tracking_ref`.
- If MRW confirms cancellation with `Estado = 1`, Odoo can safely clear the
  tracking ref through the native flow.

## Labels

Odoo's core `send_shipping` return contract does not define a label payload.

Native return labels use attachments whose names start with:

```python
carrier.get_return_label_prefix()
```

Shipping labels have a helper prefix:

```python
carrier._get_delivery_label_prefix()
```

MRW should store outbound labels as `ir.attachment` on `stock.picking`, with a
name based on:

```python
carrier._get_delivery_label_prefix()
```

or a clearly MRW-specific filename such as:

```text
LabelShipping-mrw-<NumeroEnvio>.pdf
```

The current `mrw.shipping.shipment.label_attachment_id` can also point to the
same attachment.

## Manual MRW Shipments

The native Odoo carrier contracts do not replace the existing manual MRW test
flow. The correct hybrid design is:

```text
Manual:
mrw.shipping.shipment -> MRW SOAP

Native Odoo:
stock.picking -> delivery.carrier(mrw) -> mrw.shipping.shipment audit -> MRW SOAP
```

Manual records have no `picking_id`. Picking-generated records have `picking_id`
and `carrier_id`.

