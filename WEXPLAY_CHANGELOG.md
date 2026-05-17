# Wexplay Changelog

## 2026-05-10

### wex_teardown

- Añadido bloque visible `Reacondicionamiento` en producto para productos de despiece.
- Añadidos campos de huella de despiece en `product.template`: componente, part number y modelo SAT.
- Limitada la búsqueda de coincidencias a productos reacondicionados.
- Añadido botón `Buscar coincidencias` al flujo de piezas.
- Añadidos niveles de coincidencia y color visual en listas:
  `exact`, `partial`, `model`, `none`.
- Mejorada la heurística local de coincidencias con normalización ligera de nombres y soporte mejorado para diferencias pequeñas en el modelo.
- Documentado el enfoque escalable de matcher interno ahora y servicio externo futuro.
- Replanteada la pestaña `Piezas` como fase de revisión física.
- Añadidas dos listas en piezas: piezas pendientes/aptas y piezas no aptas o no recuperadas.
- Eliminada la edición inline de piezas en el flujo principal; la edición completa pasa al formulario de línea.
- Movida la selección de plantilla a la pestaña `Dispositivo`.
- Separada la decisión de producto (`crear nuevo`, `usar existente`, `descartar`) hacia la fase de coincidencias.
- `list_price` queda como precio principal sin IVA; `pvp_tax_included` pasa a auxiliar calculado con impuestos nativos de Odoo.
- Se evita crear configuración fiscal paralela para despieces.
- El control de calidad mueve líneas no aptas/no recuperadas fuera del flujo normal sin borrarlas.
- Traducidas etiquetas visibles principales de las vistas del módulo al castellano.
- Actualizada la arquitectura del módulo con las nuevas decisiones de flujo.
