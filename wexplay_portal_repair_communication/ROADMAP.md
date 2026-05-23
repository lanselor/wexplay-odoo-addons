# Roadmap tecnico - Wexplay Portal Repair Communication

## Fases completadas

### Fase 1 - Base documental y frontera modular

Completado.

- modulo propio `wexplay_portal_repair_communication`
- ownership documental de la conversacion fijado
- separacion explicita entre chatter interno y conversacion SAT-cliente
- unidad funcional fijada: un hilo por `repair.order`

### Fase 2 - Modelo funcional v1

Completado.

- modelo de conversacion SAT
- modelo de mensajes de conversacion
- estado operativo de respuesta
- proyeccion a superficies portal y backend sin duplicar la verdad funcional

### Fase 3 - Portal cliente v1

Completado con alcance conservador.

- pagina `Conversacion` en portal
- popup de chat portal
- historico del SAT
- composer simple de mensaje
- respeto de seguridad por `commercial_partner_id`
- desactivacion de escritura cuando no corresponde

### Fase 4 - Backend tecnico v1

Completado.

- superficie separada en `repair.order`
- chat real del tecnico en Odoo
- bloque contextual `Resumen SAT`
- acciones `Abrir SAT`, `Abrir cliente` y `Crear tarea`

### Fase 5 - Endurecimiento funcional inicial

Completado parcialmente.

- reasignacion de responsable estabilizada
- fallback y degradacion basica si falla Discuss
- base de tests creada
- varios errores funcionales ya documentados y corregidos

### Fase 6 - Endurecimiento, SLA y mejoras operativas (2026-05)

Completado.

Ronda de auditoria completa (8 bugs detectados y corregidos):

- guard multi-tab erroneo en `operator_chat_bridge.js` corregido (BUG-1)
- fallo silencioso si `thread` no se resuelve en el bridge JS (BUG-2)
- llamada doble a `_sync_operator_channel_members` eliminada (BUG-3)
- cache de sidebar SAT sin discriminar canal corregida (BUG-4)
- `@api.depends("id")` eliminado (prohibido en Odoo 18) (BUG-5)
- limite de longitud de mensajes portal anadido (BUG-6)
- campo `x_portal_conversation_html` con `sanitize=False` eliminado (BUG-7)
- polling portal protegido contra errores de red (BUG-8)

Mejoras funcionales y operativas:

- SLA de 1 hora de tiempo laborable (L-V 10-14 y 16-20, Europe/Madrid)
- notificacion al tecnico por `message_notify` cuando vence el SLA
- creacion automatica de actividad en `repair.order` al vencer el SLA
- cron `ir.cron` cada 15 minutos para chequeo de SLA
- debounce de notificaciones: primera mensaje del cliente notifica; los
  siguientes solo se proyectan al canal sin spam de avisos
- confirmacion de lectura (`technician_last_read_at`): el portal muestra
  `Visto` cuando el tecnico ha abierto el chat tras el ultimo mensaje del cliente
- bandeja de entrada enriquecida con columnas SLA y lectura, marcado en rojo
  cuando `sla_breached`
- wizard `Responder` eliminado del header del formulario de conversacion;
  accion primaria es `Abrir chat tecnico`
- codigo muerto `x_portal_conversation_html` y sus metodos eliminados de
  `repair.order`

## Fase actual

Estabilizacion en produccion.

Las mejoras de la Fase 6 estan vivas. La prioridad ahora es:

- confirmar que el SLA se comporta correctamente en produccion con horarios reales
- ejecutar y sanear la suite real de tests del modulo

## Funcionalidades pendientes

### Pendientes prioritarias

- ejecutar y sanear la suite real de tests del modulo
- revisar y limpiar logs de diagnostico temporales
- ultimo pase de UX en portal, especialmente en movil
- validar comportamiento SLA en produccion con horarios reales (festivos, etc.)

### Pendientes funcionales

- adjuntos en conversacion cliente-tecnico
- respuestas rapidas o plantillas operativas para tecnico
- cierre funcional de conversacion sin cerrar necesariamente el SAT
- festivos configurables en el calculo de tiempo laborable SLA

### Pendientes tecnicas

- tiempo real por bus/websocket en portal si en el futuro se justifica
- ampliar tests HTTP y de seguridad portal
- revisar cuidadosamente el acoplamiento con parches Owl de `mail.ChatWindow`

### Pendientes de producto/UX

- seguir refinando la estetica del popup portal
- decidir si el boton `Hablar con el tecnico` ya es version final o necesita
  otra iteracion visual
- estudiar si el popup portal debe mostrar mas contexto del SAT o mantener la
  version ligera actual

## Fuera de alcance por ahora

- integracion nueva con WhatsApp como canal de esta conversacion
- replanteamiento completo del sistema de mensajeria de Odoo
