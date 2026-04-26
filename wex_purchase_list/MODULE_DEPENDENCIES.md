# Wex Purchase List Module Dependencies

## Dependencias declaradas

### `product`

Uso real:
- extensión de `product.template`
- acción para añadir a la lista desde producto
- `product.product` como producto de la línea de compra

### `purchase`

Uso real:
- creación de `purchase.order`
- creación de `purchase.order.line`
- enlace de trazabilidad con RFQ/PO

### `repair`

Uso real:
- smart button en `repair.order`
- uso de `repair_id`
- alta desde `stock.move` asociado a reparación

### `sale`

Uso real:
- smart button en `sale.order`
- alta desde `sale.order.line`

### `stock`

Uso real:
- origen desde `stock.move`
- actualización a `received` desde `stock.picking`

### `wex_whatsapp_chatter`

Uso real:
- botón WhatsApp en la ficha de la línea de compra/reserva
- apertura del asistente `whatsapp.compose.wizard`
- registro del envío en el chatter del origen funcional cuando existe

Decisión:
- es dependencia estricta porque la acción de aviso al cliente se ofrece directamente desde la vista del módulo
- el botón abre WhatsApp usando como contexto `repair.order`, `sale.order` o `res.partner` según el origen disponible

## Dependencias redundantes o a limpiar

### `base`

Situación actual:
- no está declarado explícitamente en el manifest

Conclusión:
- sigue siendo dependencia base implícita de Odoo

## Dependencias funcionales no expresadas como addon aparte

No hay integración obligatoria con librerías Python externas.

El módulo depende funcionalmente de:
- proveedores configurados en el producto (`seller_ids`)
- flujo estándar de compra de Odoo
- flujo estándar de recepción de compra

Si esos datos faltan:
- no podrá crear correctamente líneas o RFQ

## Archivos con responsabilidad estructural relevante

### [purchase_list_line_views.xml](/C:/odoo18/addons-wexplay/wex_purchase_list/views/purchase_list_line_views.xml)

Declara:
- vistas principales
- acción principal
- menú principal

### [menu.xml](/C:/odoo18/addons-wexplay/wex_purchase_list/views/menu.xml)

Situación actual:
- vuelve a declarar la misma acción y menú ya definidos en `purchase_list_line_views.xml`

Conclusión:
- genera una estructura menos honesta y más difícil de mantener
- conviene unificarlo en una fase posterior

## Acoplamientos a vigilar

- `stock.move.purchase_list_line_id`
- `sale.order.line.purchase_list_line_id`
- estados internos de `wex_purchase_list.line`
- validación de recepción en `stock.picking.button_validate()`

Estos puntos forman parte del flujo real y cualquier cambio debe revisarse con cuidado porque afectan trazabilidad y sincronización de estado.
