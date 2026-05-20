# Wexplay Portal Repair Communication - Architecture

## Objetivo

`wexplay_portal_repair_communication` crea un canal prioritario de comunicacion
entre cliente empresa y tecnico SAT, ligado de forma directa a una
`repair.order`.

La meta no es construir un chat generico ni exponer el chatter de Odoo al
portal. La meta es resolver un problema operativo:

- mensajes de clientes sin responder
- conversaciones dispersas entre WhatsApp, llamadas y conversaciones verbales
- falta de trazabilidad ligada al SAT real
- falta de ownership claro sobre quien debe atender la comunicacion

## Decision principal

La unidad de conversacion es el SAT.

Regla v1:

- existe un unico hilo funcional por `repair.order`
- si el cliente vuelve a escribir dias o semanas despues sobre el mismo SAT, la
  conversacion sigue en el mismo hilo
- el render del historico debe separar visualmente por fecha con bloques como
  `Hoy` o fecha visible

## Que SI es este modulo

Este modulo:

- modela la conversacion SAT-cliente
- decide quien debe recibir la comunicacion
- mantiene el estado operativo de respuesta pendiente o atendida
- proyecta la conversacion en portal, backend SAT y superficie de chat del
  tecnico
- mantiene un historico unico por SAT

## Que NO es este modulo

Este modulo no:

- reemplaza el chatter nativo de Odoo
- convierte Discuss en la fuente de verdad funcional
- crea un chat generico de soporte sin SAT asociado
- mezcla logs, followers o notas internas del chatter con la conversacion del
  cliente
- redefine el portal B2B general fuera del contexto SAT

## Relacion con otros modulos

### `wexplay_portal`

`wexplay_portal` sigue siendo la capa portal base.

Solo debe:

- exponer la conversacion del SAT en el portal autenticado
- mostrar la burbuja contextual para escribir al tecnico
- respetar las reglas de acceso ya existentes por `commercial_partner_id`

No debe convertirse en el dueno de la conversacion.

### `wexplay_repair`

`wexplay_repair` sigue siendo la base SAT.

Solo debe:

- mostrar una superficie de lectura operativa de la conversacion dentro de la
  ficha SAT
- conservar su chatter nativo con funcion interna

No debe absorber la logica de comunicacion.

### `wexplay_repair_warranty`

Este modulo define el criterio de SAT activo para esta comunicacion.

Regla acordada:

- el cliente puede escribir mientras el SAT siga dentro del periodo de garantia
- fuera de garantia, la conversacion pasa a solo lectura del lado portal

### `mail` y conversaciones Odoo

La infraestructura de mensajeria de Odoo se reutiliza como superficie de
conversacion para el tecnico.

Pero la verdad funcional de la conversacion pertenece a
`wexplay_portal_repair_communication`.

## Ownership y routing

La conversacion pertenece al SAT, no al tecnico.

El tecnico responsable es solo la persona que debe atenderla en ese momento.

### Cadena de destino

1. `repair.order.user_id`
2. Gerente del empleado relacionado con el responsable
3. Usuario `Administrador`

### Reglas

- si cambia el responsable del SAT, las nuevas notificaciones deben pasar al
  nuevo responsable
- el historico no cambia de hilo ni se separa por tecnico
- el fallback no debe quedar hardcodeado en una vista o en JS; debe resolverse
  en Python con criterio unico

## Estado de la conversacion

La conversacion necesita estado operativo propio, separado del estado SAT.

Estados funcionales v1:

- `pending_customer_reply`: el ultimo mensaje relevante es del cliente
- `answered`: el ultimo mensaje relevante es del tecnico
- `no_response_needed`: el tecnico marco explicitamente que no hace falta
  contestar

La conversacion se considera atendida cuando esta en:

- `answered`
- `no_response_needed`

Si el cliente vuelve a escribir, regresa a `pending_customer_reply`.

## Modelo funcional esperado

La arquitectura v1 debe orientarse a:

### Conversacion SAT

Responsabilidades:

- referencia a `repair.order`
- responsable actual
- estado de conversacion
- fechas de ultima interaccion cliente/tecnico
- trazabilidad de marcado `No es necesaria contestacion`

### Mensajes de conversacion

Responsabilidades:

- pertenecer a la conversacion SAT
- guardar autor, contenido y fecha
- distinguir origen portal/backend/sistema
- definir si el mensaje es visible para cliente
- proyectarse en las distintas superficies sin duplicar la verdad funcional

## Superficies de UI

## Portal cliente

La conversacion se accede desde la ficha SAT.

Debe existir una burbuja flotante contextual en la parte inferior derecha que
invite a hablar con el tecnico sobre esa reparacion concreta.

La conversacion portal:

- no es generica
- no representa soporte global
- esta ligada al SAT abierto por el usuario
- muestra el historico completo de la conversacion visible al cliente

## Ficha SAT en backend

La ficha de `repair.order` mantiene el chatter nativo de Odoo.

Ademas, en la parte inferior de la zona de mensajes debe existir una segunda
superficie propia del modulo, tipo panel, notebook, footer o bloque filtrable.

Su objetivo es:

- separar visualmente el chatter interno de Odoo
- mostrar de forma clara el historico de la conversacion SAT-cliente
- permitir al tecnico consultar la conversacion sin perderse entre logs y notas
  internas

Regla importante:

- no es otro chatter de Odoo
- es una vista funcional especifica de la conversacion SAT

## Ventana de conversacion del tecnico

Cuando entra un mensaje del cliente, al tecnico le debe llegar una conversacion
normal en la interfaz de chat de Odoo, como ocurre con mensajes internos entre
empleados.

Esta ventana debe tener contexto adicional estable:

- cliente
- numero de reparacion
- dispositivo: tipo, marca y modelo
- averia inicial
- notas de reparacion
- total SAT
- estado de presupuesto
- estado del flujo SAT

La presencia de este lateral es lo que convierte la conversacion en herramienta
operativa y no en mensajeria aislada.

Las acciones rapidas desde ese lateral pueden quedar como V2 si anadirlas en la
primera fase complica demasiado la implementacion.

## Menu interno

Dentro del area `Portal clientes` debe existir una vista interna de
`Conversaciones pendientes` para trabajo operativo.

Debe servir para localizar:

- mensajes pendientes
- conversaciones sin responder
- conversaciones asignadas por tecnico

## Visibilidad y seguridad

### Cliente portal

El cliente puede ver:

- la conversacion completa mantenida con el tecnico sobre su SAT autorizado

El cliente no debe ver:

- chatter bruto
- followers
- notas internas
- relaciones indirectas peligrosas

### Usuarios internos

Cualquier usuario del grupo tecnicos puede ver las conversaciones.

El responsable del SAT es quien debe atenderlas operativamente.

### Regla portal

La seguridad debe seguir viviendo en:

- ACL
- record rules
- dominios de acceso por `commercial_partner_id`
- controladores que busquen siempre dentro del dominio visible

## Persistencia y proyeccion

Regla de oro:

- una sola fuente de verdad funcional
- multiples puntos de visualizacion

La conversacion no debe vivir duplicada en:

- portal
- ventana de chat
- ficha SAT

Debe vivir en el modulo nuevo y proyectarse despues donde convenga.

## Notificacion y urgencia

## V1

Cuando entra mensaje del cliente:

- se registra en la conversacion SAT
- se marca estado pendiente
- se abre una conversacion al tecnico responsable
- se refuerza la visibilidad operativa de ese mensaje

## V2 obligatoria

Si el mensaje queda sin responder durante un tiempo definido:

- el sistema debe relanzar aviso
- el tecnico debe volver a recibir insistencia operativa

La unica manera de cerrar operativamente un mensaje de cliente sin responder es:

- responder
- marcar `No es necesaria contestacion`

## Limites actuales

Quedan fuera de esta primera definicion:

- adjuntos
- reglas finas de intercambio de ficheros cliente-tecnico
- integracion nueva con WhatsApp
- panel lateral con acciones operativas completas

## Riesgos a vigilar

- mezclar de nuevo la conversacion SAT con el chatter tecnico
- hacer depender demasiado la solucion de Discuss como fuente de verdad
- dejar el routing ambiguo entre `res.users` y `hr.employee`
- exponer datos sensibles en portal o en el lateral de conversacion
- generar varias conversaciones para el mismo SAT en lugar de un hilo unico
