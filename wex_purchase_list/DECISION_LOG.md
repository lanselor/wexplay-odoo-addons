# Wex Purchase List Decision Log

## Decisión: mantener una lista de compra paralela al reabastecimiento de Odoo

Estado:
- activa

Motivo:
- el sistema de reabastecimiento nativo se considera demasiado complejo para la operativa diaria del equipo
- se necesita una forma rápida y manual de registrar necesidades de compra

Consecuencia:
- el módulo convive con Odoo estándar, pero no lo sustituye

## Decisión: replicar la lógica operativa de una antigua Google Sheet

Estado:
- activa

Motivo:
- antes del módulo se trabajaba con una hoja compartida
- negocio necesitaba mantener campos y señales operativas similares:
  - reserva
  - cliente avisado
  - precio informado al cliente
  - estados visuales sencillos

Consecuencia:
- el modelo actual refleja más una hoja operativa interna que un flujo de compra puramente estándar

## Decisión: centralizar la creación de líneas en `add_from_origin()`

Estado:
- activa

Motivo:
- evitar duplicar lógica entre producto, venta y SAT

Consecuencia:
- es el principal punto de verdad del módulo
- también es uno de los puntos de deuda más importantes porque ya mezcla demasiadas responsabilidades

## Decisión: crear una RFQ nueva por proveedor

Estado:
- activa

Motivo:
- es el comportamiento actual esperado por negocio
- no se pretende reutilizar RFQ borrador existentes

Consecuencia:
- el flujo actual es simple y predecible
- si en el futuro se quiere reutilizar borradores, habrá que rediseñar la lógica de agrupación

## Decisión: documentar `ordered` según comportamiento actual, no según intención futura

Estado:
- activa

Motivo:
- negocio ha pedido documentación honesta del estado actual

Comportamiento actual:
- `ordered` se asigna al crear la RFQ desde la lista

Nota:
- la intención futura sería que `ordered` represente compra confirmada al proveedor, pero hoy no funciona así

## Decisión: mantener `wex_vendor_url`

Estado:
- activa

Motivo:
- el equipo necesita abrir manualmente los enlaces del proveedor para realizar pedidos

Consecuencia:
- `wex_vendor_url` es funcionalidad real del módulo y no debe tratarse como residuo accidental

## Decisión: dejar la parte de pricing/margen documentada como deuda viva

Estado:
- activa con deuda

Motivo:
- se añadió intencionadamente para ayudar a calcular precios desde producto
- hoy no funciona correctamente

Consecuencia:
- no debe documentarse como parte sólida del flujo principal
- debe quedar marcada para corrección futura
- mientras no se corrija, no debe usarse como referencia de arquitectura para crecer el módulo
