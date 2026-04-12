# Wex Knowledge Dependencies

## Hard addon dependencies

- `mail`
  Required by `mail.thread` and `mail.activity.mixin` in `wex.knowledge.article`.
- `web`
  Required for client actions, OWL components and backend assets.
- `web_editor`
  Required for the article HTML editor.
- `product`
  Required for `product.template` integration and related article access.
- `purchase`
  Required for `purchase.order` integration.
- `repair`
  Required for `repair.order` integration.
- `sale`
  Required for `sale.order` integration.
- `stock`
  Required for `stock.picking` integration.

## Likely redundant dependency

- `base`
  Standard platform dependency. It is usually implicit and does not need to be declared here.

## Business-model touchpoints

The module relies on these integrations being installed because it extends their forms and adds stat buttons:
- `repair.view_repair_order_form`
- `purchase.purchase_order_form`
- `sale.view_order_form`
- `stock.view_picking_form`
- `product.product_template_only_form_view`

## Asset dependencies

Backend assets include:
- OWL client actions
- icon picker field widget
- QWeb templates for those widgets
- SCSS for dashboard, explorer and article workspace

## Current dependency risks

- the module is frontend-heavy, so visual breakage can appear without affecting installation
- responsive behavior is a real maintenance concern even when the module loads correctly
- the article model currently acts as both domain model and data serializer for the custom client actions
