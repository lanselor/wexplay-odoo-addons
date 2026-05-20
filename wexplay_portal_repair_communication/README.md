# Wexplay Portal Repair Communication

Modulo de comunicacion SAT B2B ligado a `repair.order`.

## Objetivo

Centralizar en Odoo la comunicacion entre cliente empresa y tecnico SAT,
evitando que el canal principal viva en WhatsApp u otras conversaciones
dispersas sin responsable claro.

Este modulo no pretende exponer el chatter bruto de Odoo ni sustituir Discuss
como tecnologia. Su responsabilidad es crear un hilo funcional por SAT, con
trazabilidad propia, notificacion operativa al tecnico y superficies de
visualizacion adaptadas a portal y backend.

## Idea funcional

- un unico hilo de conversacion por `repair.order`
- el historial pertenece al SAT, no al tecnico
- el tecnico recibe la comunicacion como conversacion normal en Odoo
- la reparacion muestra un bloque especifico para consultar el historico de la
  conversacion SAT-cliente
- el portal cliente muestra la conversacion del SAT concreto

## Dependencias

- `mail`
- `hr`
- `portal`
- `website`
- `wexplay_portal`
- `wexplay_repair`
- `wexplay_repair_warranty`

## Limites de esta fase

- sin adjuntos definidos todavia
- sin reavisos automaticos por tiempo sin respuesta
- sin acciones rapidas V2 desde el lateral del chat
- sin integracion nueva con WhatsApp en esta primera iteracion

## Criterio de arquitectura

`wexplay_portal_repair_communication` es el modulo dueno de la conversacion.

`wexplay_portal` y `wexplay_repair` solo deben proyectar esa conversacion en
sus respectivas superficies de UI, sin apropiarse de la logica funcional.
