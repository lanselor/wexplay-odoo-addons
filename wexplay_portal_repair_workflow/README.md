# Wexplay Portal Repair Workflow

Modulo puente entre `wexplay_portal` y `wexplay_repair_workflow`.

Permite que el cliente B2B revise y acepte o rechace el presupuesto SAT desde
la propia reparacion del portal, manteniendo la cotizacion `sale.order`
vinculada como documento comercial real.

## Alcance v1

- Extension de la barra contextual base para mostrar `Revisar presupuesto`
  cuando procede.
- Ruta `/my/repairs/<id>/budget` con resumen minimalista del presupuesto.
- Aceptacion desde portal:
  - confirma la cotizacion vinculada si esta en borrador o enviada
  - marca el presupuesto SAT como aceptado
- Rechazo desde portal:
  - cancela la cotizacion vinculada si esta en borrador o enviada
  - marca el presupuesto SAT como rechazado
- Registro backend:
  - guarda eventos de presupuesto visto, aceptado y rechazado
  - deja aceptaciones y rechazos como pendientes de gestion interna
  - permite abrir el SAT o la cotizacion desde `Reparaciones > Portal clientes`

## Lo que no hace aun

- No pide motivo de rechazo.
- No abre conversacion ni notifica automaticamente al tecnico.
- No reemplaza el portal nativo de cotizaciones/facturas.
- No usa `schedule_date` como prioridad automatica de avisos.

Las decisiones y deuda tecnica estan documentadas en `ARCHITECTURE.md`.
