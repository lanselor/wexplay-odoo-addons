# Wexplay Product Print - Arquitectura

`wexplay_product_print` mantiene las etiquetas y la interfaz de impresión de `product.template`. Reutiliza el router, perfiles, asignaciones y trazas de `wex_print_core`.

## Etiquetas disponibles

| Documento | Reporte | Tamaño | Uso |
|---|---|---:|---|
| Brother | `product_label` | 42 x 29 mm | Flujo existente validado con Brother QL-710W. |
| Zebra | `product_label_zebra` | 76 x 25 mm | Etiqueta comercial nueva. |

La Zebra muestra nombre, PVP IVA incluido, código Code128 y referencia interna de Odoo. La referencia (`default_code`) sustituye al identificador incremental que se usaba en PrestaShop. No se usa el ID técnico de Odoo como dato comercial.

## Flujo Zebra

1. Desde el producto, abrir **Impresión** y elegir **Etiqueta Zebra 76 x 25**.
2. El servidor exige que exista referencia interna.
3. El router solo permite la ruta de resolución nueva para este documento. Una asignación de Zebra debe estar configurada y activada; así no se envía por error a la Brother configurada en el flujo legacy.
4. QZ recibe las dos dimensiones del paperformat y entrega el PDF a la impresora configurada.

La acción **Etiqueta Brother 42 x 29** mantiene el comportamiento anterior y su fallback legacy.

## Configuración necesaria

Crear en Wex Print un dispositivo Zebra con el nombre exacto que expone QZ Tray, un perfil y una asignación para `Product Label Zebra 76x25`. Activar `Pilot new resolution` mientras el modo global sea Hybrid.