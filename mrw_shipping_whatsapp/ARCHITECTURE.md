# MRW Shipping WhatsApp

## Purpose

`mrw_shipping_whatsapp` is an optional bridge between `mrw_shipping_connector`,
the Wexplay WhatsApp chatter integration, and the SAT shipping operations.
It lets a user prepare a WhatsApp tracking message from an MRW shipment or
from its related repair shipping operation.

## Functional boundary

- The module only shares the MRW reference, shipment number, and tracking URL.
- It never attaches or exposes the shipping-label PDF through WhatsApp.
- It does not create a public URL for the label.
- Sending remains assisted through the existing WhatsApp compose wizard; this
  module does not call a WhatsApp API or implement automatic delivery.

## Dependencies

- `mrw_shipping_connector` is the source of the shipment and tracking data.
- `wex_whatsapp_chatter` provides templates and the compose wizard.
- `wexplay_repair_delivery` provides the SAT shipping-operation entry points.

The bridge is deliberately separate so the MRW connector and WhatsApp chatter
module stay independently installable and do not acquire reciprocal
dependencies.

## Template variables

For `mrw.shipping.shipment`, the compose wizard resolves:

- `${mrw_reference}`
- `${mrw_tracking_number}`
- `${mrw_tracking_url}`

Two starter templates are supplied: one for customer deliveries and another
for customer pickups. Both are tracking-only messages.

The WhatsApp compose selector exposes the `MRW` quick filter for MRW
shipments. Its visual filter map is declared with the other picker filters in
`wex_whatsapp_chatter`; the MRW model and `mrw_shipping` group remain defined
by this optional bridge. This keeps the picker mapping in its single runtime
location without making the WhatsApp module depend on MRW.
