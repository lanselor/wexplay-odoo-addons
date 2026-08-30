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
- Aisla en backend la ejecucion real del workflow comercial cuando el cliente
  acepta o rechaza desde portal, para no depender del entorno ORM del usuario
  portal durante cancelaciones, confirmaciones y recomputaciones de `sale.order`.

### `models/portal_repair_event.py`

- Guarda actividad portal SAT persistente para control interno.
- Distingue trazabilidad informativa de eventos que requieren gestion.
- Permite marcar eventos como pendiente, en gestion, hecho o sin accion.
- Incluye `report_downloaded` con la variante Wexplay o personalizada cuando
  `wexplay_portal_repair_reports` registra una descarga correcta.

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
- Si el workflow SAT marca `not_repairable`, el portal lo muestra como resultado
  tecnico no accionable por el cliente.
- Rechazar presupuesto no cancela automaticamente la reparacion.
- Ver un presupuesto queda registrado como trazabilidad ya atendida.
- Aceptar o rechazar un presupuesto crea trabajo interno pendiente de revisar.
- Descargar un informe es trazabilidad informativa: se registra solo tras
  renderizar el PDF y se marca como hecho automáticamente.
- `schedule_date` se muestra como dato de contexto porque actualmente no es una
  fecha fiable para priorizar alertas.

## Activity extension contract

The portal event factory accepts optional extra values in addition to its
common SAT context. This keeps `wexplay_portal_repair_workflow` as the
single activity/dashboard infrastructure while allowing a specialized portal
module to add a small event-specific value such as `report_variant`.

The workflow module does not generate reports or know report security rules.
Those remain in `wexplay_portal_repair_reports`; this module only stores and
shows the resulting activity in the Portal clientes dashboard, event list and
quick actions.

## Incidencia resuelta: rechazo portal con error 403

Se detecto un fallo intermitente al rechazar presupuestos SAT desde portal.

Casuistica observada:

- SAT en `waiting_customer`
- cotizacion vinculada en `draft`
- el portal permitia visualmente rechazar
- al ejecutar la accion, Odoo terminaba en `403` con `AccessError` sobre
  `sale.order.line`

La causa real no era un problema de visibilidad del boton ni una falta de
dominio sobre `repair.order`.

El problema aparecia durante el `flush` de la transaccion HTTP del usuario
portal. Aunque el acceso al SAT y al presupuesto estaba validado, el workflow
de rechazo acababa ejecutando logica comercial de `sale.order` que hacia que
Odoo leyera `sale.order.line` en el contexto del usuario portal.

Eso producia un `AccessError` legitimo sobre un modelo que no debe abrirse al
cliente portal.

### Decision tecnica aplicada

No se ampliaron ACL ni record rules del usuario portal sobre `sale.order.line`.

La accion portal sigue validando primero:

- acceso del usuario portal a la reparacion
- partner comercial autorizado
- estado SAT y estado de presupuesto
- disponibilidad real de la cotizacion para aceptar o rechazar

Solo despues de pasar esas validaciones, la ejecucion del workflow SAT/comercial
se lanza en una `Environment` aislada de backend y en un cursor separado. Asi:

- la validacion funcional sigue siendo del usuario real del portal
- la parte sensible de `sale.order` no depende del ORM del portal
- se evita abrir permisos innecesarios a usuarios externos
- se reduce el riesgo de estados intermedios incoherentes por errores en `flush`

Este criterio aplica tanto a aceptar como a rechazar presupuesto desde portal.

## Deuda tecnica pendiente

- Registrar mensaje en chatter de la reparacion cuando el cliente acepte o
  rechace desde portal.
- Evaluar conversacion/notificacion con tecnico o responsable asociado al SAT.
- Anadir motivo opcional de rechazo.
- La instrumentación de diagnóstico de presupuestos se mantiene desactivada
  por defecto y solo puede activarla un administrador desde Ajustes. Sus
  trazas reducidas se escriben en el log del servidor; no existe un parámetro
  URL ni una vista de depuración para usuarios portal.
- Evaluar recordatorios automaticos para aceptaciones pendientes de gestion
  durante varios dias.
