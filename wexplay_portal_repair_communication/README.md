# Wexplay Portal Repair Communication

Modulo de comunicacion SAT B2B ligado a `repair.order`.

## Objetivo

Centralizar en Odoo la comunicacion entre cliente empresa y tecnico SAT,
evitando que el canal principal viva en WhatsApp u otras conversaciones
dispersas sin responsable claro, sin trazabilidad y sin contexto del SAT real.

Este modulo no pretende exponer el chatter bruto de Odoo ni sustituir Discuss
como tecnologia. Su responsabilidad es crear un hilo funcional por SAT, con
trazabilidad propia, reglas de visibilidad, notificacion operativa al tecnico y
superficies adaptadas a portal y backend.

## Estado funcional actual

Actualmente el modulo ya implementa:

- un unico hilo funcional de conversacion por `repair.order`
- historico de mensajes propio y separado del chatter estandar
- escritura del cliente desde portal cuando el SAT sigue activo o la garantia
  sigue vigente
- pagina `Conversacion` dentro de la ficha SAT del portal
- popup de chat en portal con polling estable
- conversacion real del tecnico usando la ventana nativa de chat de Odoo
- bloque contextual `Resumen SAT` dentro del chat del tecnico
- sincronizacion de respuestas tecnico -> conversacion funcional -> portal
- reasignacion de responsable manteniendo el mismo hilo SAT
- degradacion controlada si falla la proyeccion a Discuss
- SLA de 1 hora de tiempo laborable con notificacion al tecnico y creacion de
  actividad automatica cuando el cliente no recibe respuesta
- debounce de notificaciones: solo se notifica al tecnico con el primer mensaje
  del cliente; los mensajes siguientes llegan al canal sin spam de avisos
- confirmacion de lectura: el portal muestra cuando el tecnico ha abierto la
  conversacion por ultima vez
- bandeja de entrada enriquecida con columnas de SLA y lectura, y marcado en
  rojo cuando se supera el limite

## Idea funcional

- un unico hilo de conversacion por `repair.order`
- el historial pertenece al SAT, no al tecnico
- el tecnico recibe la comunicacion como conversacion normal en Odoo
- la reparacion muestra una superficie especifica para consultar el historico de
  la conversacion SAT-cliente
- el portal cliente muestra la conversacion del SAT concreto

## Dependencias

- `mail`
- `hr`
- `portal`
- `website`
- `wexplay_portal`
- `wexplay_repair`
- `wexplay_portal_repair_workflow`
- `wexplay_repair_warranty`

## Alcance actual

Incluido:

- mensajes portal <-> tecnico
- estado operativo de conversacion
- popup de chat portal
- vista completa de conversacion en portal
- chat tecnico en backend
- contexto SAT dentro del chat tecnico
- boton para crear actividad desde el contexto del chat tecnico
- SLA automatico con horario laborable configurable en codigo
- debounce de notificaciones en cadena
- confirmacion de lectura ("Visto") en portal
- bandeja de entrada con estados y SLA visibles

Todavia no incluido:

- adjuntos cliente-tecnico
- tiempo real por bus/websocket en portal
- respuestas rapidas o plantillas operativas
- integracion nueva con WhatsApp como canal de esta conversacion

## Criterio de arquitectura

`wexplay_portal_repair_communication` es el modulo dueno de la conversacion.

`wexplay_portal` y `wexplay_repair` solo deben proyectar esa conversacion en
sus respectivas superficies de UI, sin apropiarse de la logica funcional.
