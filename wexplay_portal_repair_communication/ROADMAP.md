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

## Fase actual

Pulido fino + endurecimiento.

La base funcional ya esta viva. Las siguientes iteraciones deben priorizar
estabilidad, claridad operativa y tests reales antes de meter complejidad nueva.

## Funcionalidades pendientes

### Pendientes prioritarias

- ejecutar y sanear la suite real de tests del modulo
- revisar y limpiar logs de diagnostico temporales
- ultimo pase de UX en portal, especialmente en movil
- validar mejor comportamiento en entornos de produccion y multiusuario

### Pendientes funcionales

- adjuntos en conversacion cliente-tecnico
- respuestas rapidas o plantillas operativas para tecnico
- SLA o reaviso automatico cuando un mensaje cliente queda sin responder
- indicadores mas ricos de no leido o pendiente por SAT
- cierre funcional de conversacion sin cerrar necesariamente el SAT

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
- automatizaciones complejas de SLA
- replanteamiento completo del sistema de mensajeria de Odoo
