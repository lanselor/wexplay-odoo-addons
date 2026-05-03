# Wexplay Portal Repair Workflow - Architecture

## Objetivo

`wexplay_portal_repair_workflow` es un modulo puente. Extiende una parte
concreta del portal SAT con capacidades del workflow de presupuesto, sin crear
dependencia directa entre `wexplay_portal` y `wexplay_repair_workflow`.

## Decision principal

El cliente acepta o rechaza el presupuesto desde la reparacion que esta viendo,
no desde una cotizacion aislada que tenga que localizar por su cuenta.

La cotizacion vinculada sigue siendo el documento comercial real:

- `repair.order.sale_order_id` es el vinculo funcional
- `sale.order` se confirma al aceptar
- `sale.order` se cancela al rechazar si aun esta en borrador/enviada
- `repair.order.x_budget_stage` sigue siendo el estado SAT operativo

## Responsabilidades

### `models/repair_order.py`

- Decide si el presupuesto puede revisarse desde portal.
- Prepara el resumen economico y operativo.
- Ejecuta aceptacion/rechazo delegando en `sale.order` y workflow SAT.
- Registra eventos internos de portal tras acciones relevantes.

### `models/portal_repair_event.py`

- Guarda actividad portal SAT persistente para control interno.
- Distingue trazabilidad informativa de eventos que requieren gestion.
- Permite marcar eventos como pendiente, en gestion, hecho o sin accion.

### `controllers/portal.py`

- Expone la vista resumen.
- Recibe acciones POST de aceptar/rechazar.
- Busca siempre reparaciones dentro del dominio portal existente.
- Registra la visualizacion de la vista resumen del presupuesto.

### `views/portal_repair_event_views.xml`

- Anade una vista backend `Actividad portal SAT`.
- Permite abrir el SAT o la cotizacion vinculada desde el evento.
- Muestra `schedule_date` solo como contexto operativo, no como prioridad.

### `views/portal_repair_workflow_templates.xml`

- Extiende la barra contextual sticky de `wexplay_portal`.
- Define la vista resumen del presupuesto.
- Define modales de confirmacion.

## UX

La ficha SAT principal ya contiene mucha informacion. Por eso la aceptacion no
se anade como otro bloque pesado dentro de la ficha.

Flujo:

1. El cliente entra en la ficha SAT.
2. La barra contextual base mantiene visible SAT, referencia, estado y dispositivo.
3. Este modulo anade a esa barra la accion `Revisar presupuesto` cuando procede.
4. La vista resumen responde a una pregunta: aceptar o rechazar reparar ese
   dispositivo por ese importe.

## Reglas de negocio v1

- Solo puede actuar un usuario portal con acceso a la reparacion por partner
  comercial.
- Solo se acepta/rechaza si `x_budget_stage == waiting_customer`.
- Solo se actua sobre cotizaciones en `draft` o `sent`.
- Si la cotizacion ya esta en `sale`, el presupuesto se trata como ya aceptado.
- Si la cotizacion esta cancelada, se bloquea la accion.
- Rechazar presupuesto no cancela automaticamente la reparacion.
- Ver un presupuesto queda registrado como trazabilidad ya atendida.
- Aceptar o rechazar un presupuesto crea trabajo interno pendiente de revisar.
- `schedule_date` se muestra como dato de contexto porque actualmente no es una
  fecha fiable para priorizar alertas.

## Deuda tecnica pendiente

- Registrar mensaje en chatter de la reparacion cuando el cliente acepte o
  rechace desde portal.
- Evaluar conversacion/notificacion con tecnico o responsable asociado al SAT.
- Anadir motivo opcional de rechazo.
- Ampliar la trazabilidad con snapshots mas completos si se necesita auditar
  importes, estados previos o contenido exacto mostrado al cliente.
- Evaluar recordatorios automaticos para aceptaciones pendientes de gestion
  durante varios dias.
