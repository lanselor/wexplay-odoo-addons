# Wex Vendor Bill OCR

Módulo experimental para acelerar la recepción administrativa de compras a partir de una factura PDF de proveedor.

## Alcance de esta fase

- subida manual de PDF desde `purchase.order`
- cola OCR persistente con estados y progreso
- extracción de texto embebido con fallback OCR
- revisión humana antes de aplicar
- validación de recepciones pendientes
- captura de seriales cuando haga falta
- creación de factura de proveedor nativa desde la compra
- copiado del PDF al `account.move` resultante

## Uso operativo resumido

1. Confirmar la compra.
2. Subir la factura PDF desde la compra.
3. Esperar a que el job pase a `review`.
4. Abrir el wizard de revisión.
5. Corregir número, fecha, importes o referencia si hace falta.
6. Completar seriales si el sistema los exige.
7. Confirmar para recibir y crear la factura.

## Límites actuales

- solo PDF
- no aplica automáticamente sin revisión
- no interpreta líneas completas de factura
- no está diseñado todavía para múltiples facturas parciales sobre la misma compra

## Documentación relacionada

- [ARCHITECTURE.md](/C:/odoo18/addons-wexplay/wex_vendor_bill_ocr/ARCHITECTURE.md)
- [MODULE_DEPENDENCIES.md](/C:/odoo18/addons-wexplay/wex_vendor_bill_ocr/MODULE_DEPENDENCIES.md)
