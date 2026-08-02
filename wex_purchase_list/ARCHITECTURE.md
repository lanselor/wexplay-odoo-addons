# Wex Purchase List Architecture

## Objetivo real del módulo

`wex_purchase_list` existe para centralizar necesidades internas de compra antes de emitir RFQ, sin usar el sistema de reabastecimiento estándar de Odoo como flujo principal.

El módulo no sustituye el reabastecimiento nativo. Mantiene un flujo paralelo, más rápido y manual, inspirado en una antigua hoja de Google Sheets usada en SAT.

## Qué hace hoy

- Muestra una lista interna de compra basada en `wex_purchase_list.line`.
- Usa una vista operativa propia `wex_operational_list` como entrada principal para compras y reservas.
- Permite añadir productos a esa lista desde:
  - la ficha de producto
  - una reparación, a partir de `stock.move`
  - una cotización, a partir de `sale.order.line`
- Permite registrar:
  - quién añadió el producto
  - producto
  - proveedor
  - URL del proveedor
  - reparación asociada si nace desde SAT
  - estado interno del pedido
  - si la línea es una reserva
  - si el cliente ya fue avisado
  - precio informado al cliente
  - RFQ/PO y línea de compra generadas
- Permite agrupar visualmente reservas y seguimiento mediante `reservation_board_section`.
- Permite marcar al cliente como avisado desde lista, reservas y formulario cuando el repuesto ya está recibido.
- Permite abrir rápidamente el enlace del proveedor y WhatsApp del cliente cuando el origen lo soporta.
- Permite crear RFQ agrupadas por proveedor y compañía a partir de líneas en estado `to_purchase`.

## Qué no hace

- No intenta reemplazar el planificador/reabastecimiento nativo de Odoo.
- No reutiliza RFQ borrador existentes.
- No resuelve todavía bien todos los casos futuros de recepción parcial o flujos complejos de compra.
- No tiene hoy una arquitectura claramente separada entre:
  - lista interna de compra
  - utilidades de producto
  - cálculo de precios y margen

## Modelos y responsabilidades

### `wex_purchase_list.line`

Modelo principal del módulo.

Responsabilidades actuales:
- almacenar la necesidad interna de compra
- mantener estados internos
- calcular señales operativas de reserva, retraso y tablero
- enlazar orígenes (`repair`, `sale`, `product`)
- centralizar la creación de líneas con `add_from_origin()`
- registrar avisos al cliente y su trazabilidad mínima
- generar RFQ con `action_create_rfqs()`

Métodos relevantes:
- `add_from_origin()`
- `action_create_rfqs()`
- `action_mark_customer_notified()`
- `action_open_customer_whatsapp()`
- `action_mark_as_received()`

### Vista operativa `wex_purchase_list_operational`

Archivos:
- [purchase_list_operational_action.js](/C:/odoo18/addons-wexplay/wex_purchase_list/static/src/js/purchase_list_operational_action.js)
- [purchase_list_operational_action.xml](/C:/odoo18/addons-wexplay/wex_purchase_list/static/src/xml/purchase_list_operational_action.xml)
- [purchase_list.css](/C:/odoo18/addons-wexplay/wex_purchase_list/static/src/css/purchase_list.css)

Responsabilidades actuales:
- renderizar la lista como tablero operativo más cercano a hoja interna que a kanban estándar
- permitir selección múltiple y creación agrupada de RFQ
- conservar temporalmente la selección al abrir y volver de una ficha, sin cambiar el clic normal de edición de la fila
- permitir seleccionar todas las líneas visibles del filtro actual para la compra diaria
- ofrecer una acción individual de apertura de URL por línea, amplia y separada del clic que abre la ficha
- marcar reservas como avisadas sin salir del tablero
- soportar agrupaciones visuales por proveedor, cliente, estado o bloque de reservas

### Vista operativa de Reservas

La acción de Reservas usa una vista XML distinta que reutiliza el renderizador base con una presentación específica.

Responsabilidades:
- mostrar un HERO de ancho completo con `Con retraso`, `Esperando llegada`, `Pendientes de aviso` y `Ya avisadas`
- priorizar automáticamente el primer bloque con reservas y mostrar solo sus líneas para evitar agrupaciones verticales largas
- ofrecer WhatsApp cuando exista cliente y `Marcar avisado` solo en reservas recibidas aún no avisadas
- recargar el tablero tras marcar un aviso para que la reserva se desplace a `Ya avisadas`
- no ofrecer selección múltiple ni creación de RFQ: Reservas se centra en seguimiento y aviso individual

### Extensiones de `repair.order` y `stock.move`

Archivo: [repair_order.py](/C:/odoo18/addons-wexplay/wex_purchase_list/models/repair_order.py)

Responsabilidades actuales:
- smart button de líneas de compra desde la reparación
- acción para añadir una pieza (`stock.move`) a la lista
- trazabilidad con `purchase_list_line_id` en `stock.move`

### Extensiones de `sale.order` y `sale.order.line`

Archivo: [sale_order.py](/C:/odoo18/addons-wexplay/wex_purchase_list/models/sale_order.py)

Responsabilidades actuales:
- smart button de líneas de compra desde la venta
- acción para añadir una línea de venta a la lista
- trazabilidad con `purchase_list_line_id` en `sale.order.line`
- política `Marcar como reserva` por cotización comercial, activa por defecto
- sincronización de esa política con líneas de compra aún no avisadas

Reglas:
- las ventas independientes añaden sus productos como reserva por defecto
- las cotizaciones SAT no exponen ni pueden modificar esta política; sus piezas usan `stock.move.wex_is_reservation`
- la política solo se puede cambiar en estado borrador o enviada
- el cambio puede retirar avisos futuros de líneas activas, pero no altera un aviso ya registrado

### Extensión de `product.template` en `product.py`

Archivo: [product.py](/C:/odoo18/addons-wexplay/wex_purchase_list/models/product.py)

Responsabilidades actuales:
- campo `wex_vendor_url`
- acción rápida para añadir una unidad a la lista desde la ficha del producto

### Extensión de `product.template` en `product_template.py`

Archivo: [product_template.py](/C:/odoo18/addons-wexplay/wex_purchase_list/models/product_template.py)

Responsabilidades actuales:
- cálculo auxiliar de PVP con IVA
- cálculo auxiliar de margen
- sugerencia de precio

Nota:
- esta parte está resuelta en Python mediante `compute`, `inverse`, `onchange` y acción explícita para aplicar sugerencia
- el redondeo comercial se realiza siempre hacia arriba al siguiente múltiplo de 5
- no forma parte del núcleo estable de la lista de compra y no debería condicionar el resto del diseño del addon

### Extensión de `stock.picking`

Archivo: [stock_picking.py](/C:/odoo18/addons-wexplay/wex_purchase_list/models/stock_picking.py)

Responsabilidad actual:
- al validar una recepción ligada a compra, marcar líneas de la lista como `received` cuando detecta que la línea de compra está totalmente recibida

## Estados actuales de `wex_purchase_list.line`

La documentación debe reflejar el comportamiento real actual:

- `draft_wait_customer`
  - se ha dado precio al cliente, pero aún no hay confirmación
- `to_purchase`
  - ya debe comprarse
- `ordered`
  - comportamiento actual del código: la línea pasa a `ordered` al crear la RFQ desde la lista
  - esto no coincide con la intención futura de negocio, pero hoy es el comportamiento real
- `received`
  - se intenta marcar desde la validación de recepción de compra
- `cancelled`
  - cancelación manual o cancelación del flujo que dio origen a la necesidad

## Reglas actuales por origen

### Origen `sale.order.line`

- si la línea de venta ya tiene `purchase_list_line_id`, no se puede volver a añadir
- no hace merge con otra línea existente

### Origen `stock.move`

- si el `stock.move` ya tiene `purchase_list_line_id` activa, no se puede volver a añadir
- si existe una línea activa con misma `repair_id` + mismo `product_id`, suma cantidad

### Origen `product.template`

- requiere una única variante
- crea siempre una línea nueva
- no hace merge actualmente

## Seguridad y visibilidad esperada por negocio

Negocio ha definido este comportamiento esperado:

- la lista debe separarse por compañía
- los administradores pueden ver entre compañías
- los usuarios normales deben poder editar líneas ajenas, al menos por ahora
- solo managers deben generar RFQ

Nota:
- el estado real de seguridad actual no está todavía alineado del todo con esta definición y debe revisarse en una fase posterior

## Deuda viva más importante

- `action_create_rfqs()` marca `ordered` al crear la RFQ, no al confirmar la compra
- la parte de pricing/margen en producto está en el módulo por conveniencia, aunque ya no depende de JS ni de recargas de página
- hay solape de responsabilidades entre compra interna SAT y utilidades de pricing
- el bloque de pricing sigue viviendo en este módulo aunque no pertenece al flujo principal de compra interna
- hay que revisar seguridad sobre `stock.move`
- hay que revisar reglas multi-company para alinearlas con el comportamiento esperado
- la vista operativa ya es pieza central del módulo y conviene documentar mejor sus filtros, agrupaciones y límites para evitar que la UX evolucione sin trazabilidad
