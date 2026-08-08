# Wex Vendor Bill OCR Module Dependencies

## Dependencias declaradas

### `account`

Uso real:
- creación y validación funcional de `account.move` tipo factura de proveedor
- detección de duplicados por proveedor y referencia
- adjuntado final del PDF sobre la factura creada

### `purchase`

Uso real:
- punto de entrada desde `purchase.order`
- creación nativa de factura mediante `action_create_invoice()`
- uso de proveedor, importes y facturas asociadas como contexto de validación

### `stock`

Uso real:
- validación de recepciones entrantes pendientes
- uso de `stock.move`, `stock.move.line`, `stock.lot`
- captura de seriales para productos con tracking por serie

## Dependencias Python no expresadas como addon

El módulo depende funcionalmente de librerías del servidor Odoo:

- `pypdf` o `PyPDF2`
- `pytesseract`
- `pdf2image`

Consecuencia:
- si faltan, el módulo no puede completar todo el flujo OCR
- el job deja el error trazado en base de datos en lugar de fallar silenciosamente

## Dependencias funcionales implícitas

El flujo también depende de:

- compras confirmadas
- adjuntos PDF válidos
- datos correctos de proveedor en la compra
- recepciones pendientes coherentes cuando la compra aún no está recibida
- configuración de productos con tracking por serie cuando proceda

Si esos datos faltan o no cuadran:
- el módulo debe parar en revisión o en error
- no debe inventar datos ni forzar una factura inconsistente

## Acoplamientos a vigilar

- `purchase.order.invoice_ids`
- `purchase.order.picking_ids`
- `stock.picking.button_validate()`
- `stock.immediate.transfer`
- `stock.backorder.confirmation`
- `account.move.ref`
- `ir.attachment` como soporte documental del PDF original

Estos puntos forman parte del flujo real y cualquier cambio en Odoo base o en módulos Wexplay que alteren compras, recepciones o creación de facturas puede impactar directamente aquí.

## Decisiones de dependencia

- no se crea un modelo paralelo de factura OCR
- la factura final sigue siendo el `account.move` nativo
- `stock` no es una dependencia accidental: es parte del objetivo de negocio porque la recepción y la factura deben poder cerrarse en un mismo flujo operativo controlado
