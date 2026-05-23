# Wexplay Portal Repair Communication - Architecture

## Objetivo

`wexplay_portal_repair_communication` crea y gobierna un canal prioritario de
comunicacion entre cliente empresa y tecnico SAT, ligado de forma directa a una
`repair.order`.

La meta no es construir un chat generico ni exponer el chatter de Odoo al
portal. La meta es resolver un problema operativo real:

- mensajes de clientes sin responder
- conversaciones dispersas entre WhatsApp, llamadas y conversaciones verbales
- falta de trazabilidad ligada al SAT real
- falta de ownership claro sobre quien debe atender la comunicacion

## Decision principal

La unidad de conversacion es el SAT.

Regla consolidada:

- existe un unico hilo funcional por `repair.order`
- si el cliente vuelve a escribir dias o semanas despues sobre el mismo SAT, la
  conversacion sigue en el mismo hilo
- el historial se renderiza con separadores por fecha
- el chatter estandar de Odoo no es la fuente de verdad de esta conversacion

## Fuente de verdad

La verdad funcional vive en:

- `wex.portal.repair.conversation`
- `wex.portal.repair.message`

Discuss y el portal son solo superficies de proyeccion.

Regla de oro:

- una sola fuente de verdad funcional
- varias superficies de visualizacion
- ninguna de esas superficies debe gobernar la logica de negocio

## Que SI es este modulo

Este modulo:

- modela la conversacion SAT-cliente
- decide quien debe recibir la comunicacion
- mantiene el estado operativo de respuesta pendiente o atendida
- proyecta la conversacion en portal, backend SAT y ventana de chat tecnico
- mantiene un historico unico por SAT
- crea una capa contextual de SAT dentro del chat tecnico

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
- mostrar la burbuja y el popup contextual para escribir al tecnico
- respetar las reglas de acceso ya existentes por `commercial_partner_id`

No debe convertirse en el dueno de la conversacion.

### `wexplay_repair`

`wexplay_repair` sigue siendo la base SAT.

Solo debe:

- mostrar superficies de lectura y acceso a la conversacion dentro de la ficha
  SAT
- conservar su chatter nativo con funcion interna

No debe absorber la logica de comunicacion.

### `wexplay_repair_warranty`

Este modulo define el criterio de SAT activo para esta comunicacion.

Regla acordada:

- el cliente puede escribir si el SAT sigue operativo
- si el SAT ya no esta activo, la escritura depende de si la garantia sigue
  vigente
- en SAT no finalizado nunca debe mostrarse `Fuera de garantia`; en ese caso el
  contexto del chat tecnico debe mostrar `No aplicable`

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

- si cambia el responsable del SAT, el hilo no cambia
- las nuevas notificaciones deben pasar al nuevo responsable
- el tecnico saliente no debe seguir recibiendo mensajes nuevos
- el fallback debe resolverse en Python con criterio unico

## Estado de la conversacion

La conversacion necesita estado operativo propio, separado del estado SAT.

Estados funcionales actuales:

- `pending_customer_reply`: el ultimo mensaje relevante es del cliente
- `answered`: el ultimo mensaje relevante es del tecnico
- `no_response_needed`: marcado interno para casos en que no hace falta seguir
  insistiendo

La conversacion se considera atendida cuando esta en:

- `answered`
- `no_response_needed`

Si el cliente vuelve a escribir, regresa a `pending_customer_reply`.

## Modelo funcional implementado

### Conversacion SAT

Responsabilidades:

- referencia a `repair.order`
- responsable actual
- estado de conversacion
- fechas de ultima interaccion cliente/tecnico
- vinculacion opcional al canal operador de Discuss

### Mensajes de conversacion

Responsabilidades:

- pertenecer a la conversacion SAT
- guardar autor, contenido y fecha
- distinguir origen portal, tecnico y sistema
- definir si el mensaje es visible para cliente
- proyectarse en las distintas superficies sin duplicar la verdad funcional

## Superficies de UI

### Portal cliente

La conversacion se accede desde la ficha SAT.

Superficies actuales:

- pagina `Conversacion` dentro de la ficha SAT
- burbuja flotante contextual en la parte inferior derecha
- popup de chat portal que reutiliza el mismo hilo SAT

La conversacion portal:

- no es generica
- no representa soporte global
- esta ligada al SAT abierto por el usuario
- muestra el historico completo visible al cliente
- usa polling ligero para refrescarse sin recarga manual

### Ficha SAT en backend

La ficha de `repair.order` mantiene el chatter nativo de Odoo.

Ademas existe una superficie especifica del modulo para:

- separar visualmente chatter Odoo y conversacion SAT-cliente
- mostrar el historico de la conversacion SAT-cliente
- alternar entre chatter normal y conversacion portal

Regla importante:

- no es otro chatter de Odoo
- es una vista funcional especifica de la conversacion SAT

### Ventana de conversacion del tecnico

Cuando entra un mensaje del cliente, al tecnico le llega una conversacion real
en la interfaz de chat de Odoo.

Ese chat tiene contexto adicional estable:

- cliente
- numero de reparacion
- dispositivo
- IMEI o serie
- responsable
- total SAT
- estado de presupuesto
- estado de garantia
- averia reportada
- notas SAT limpias

Acciones actuales del resumen SAT:

- abrir SAT
- abrir cliente
- crear actividad pendiente

Las acciones de llamada, videollamada y ajustes RTC se ocultan solo en estos
chats SAT portal. La logica vive en el patch del `ChatWindow` y se puede
revertir quitando los ids filtrados.

## Persistencia y proyeccion

La conversacion no debe vivir duplicada en:

- portal
- ventana de chat
- ficha SAT

Debe vivir en el modulo y proyectarse despues donde convenga.

## Notificacion y urgencia

### Implementado

Cuando entra el primer mensaje del cliente en un ciclo nuevo (debounce activo):

- se registra en la conversacion SAT
- se marca estado `pending_customer_reply`
- se calcula el deadline SLA y se escribe en `sla_deadline`
- se proyecta al canal del tecnico
- se abre el chat al responsable
- se notifica al responsable via `message_notify`
- si falla Discuss, el mensaje sigue guardado como verdad funcional

Si el cliente envia mensajes adicionales sin que el tecnico haya respondido:

- se siguen proyectando al canal (tecnico los ve en el chat)
- **no** se vuelven a enviar notificaciones ni se reabre el chat (debounce)
- el `sla_deadline` se recalcula siempre desde el ultimo mensaje cliente

Cuando el tecnico responde:

- el SLA se resetea (`sla_deadline = False`, `sla_notified_at = False`)
- el estado pasa a `answered`

El cron SLA (`ir.cron` cada 15 minutos) detecta conversaciones con SLA vencido y:

- registra `sla_notified_at`
- notifica al responsable via `message_notify`
- intenta abrir el canal del tecnico via bus
- crea una actividad `mail.activity` en `repair.order` de tipo "todo"

### Pendiente

- tiempo real por bus/websocket en portal si en el futuro se justifica

## Debounce de notificaciones

El estado de la conversacion se captura ANTES del write ORM para distinguir
si el mensaje es el primero del cliente en un ciclo de respuesta pendiente o
un mensaje adicional:

```python
was_already_pending = conversation.state == "pending_customer_reply"
skip_open_chat = was_already_pending
conversation.write(update_vals)
if not was_already_pending:
    message._safe_notify_responsible_about_portal_message()
message._safe_post_to_operator_channel(skip_open=skip_open_chat)
```

`skip_open=True` hace que `_post_message_to_operator_channel` proyecte el
mensaje al canal pero no llame a `_open_operator_channel_for_user`.

Regla: el mensaje siempre llega al canal. Solo se suprimen el `message_notify`
y la apertura forzada del chat cuando ya hay un ciclo pendiente activo.

## SLA de tiempo laborable

El modulo implementa un calculo de tiempo laborable para el deadline SLA.

Constantes de modulo:

```python
_SLA_MINUTES = 60
_SLA_TZ = "Europe/Madrid"
_SLA_WINDOWS = [(time(10, 0), time(14, 0)), (time(16, 0), time(20, 0))]
_SLA_DAYS = {0, 1, 2, 3, 4}  # lunes-viernes
```

La funcion `_add_business_minutes(start_utc_naive, minutes)`:

1. convierte UTC naive a Europe/Madrid
2. si el instante esta fuera de horario o es fin de semana, avanza al inicio
   del siguiente tramo laborable
3. consume minutos avanzando por tramos, cambiando de dia cuando el tramo
   actual se agota
4. devuelve el resultado en UTC naive

El deadline se escribe siempre que el cliente envia un mensaje (incluso si
ya estaba pendiente), de modo que el SLA representa siempre el tiempo
laborable desde el ultimo mensaje del cliente.

## Confirmacion de lectura

El campo `technician_last_read_at` en `wex.portal.repair.conversation` se
actualiza cada vez que el tecnico:

- llama a `action_open_operator_chat()` (abrir desde backend)
- llama a `get_operator_chat_thread_data()` (carga OWL del contexto SAT)

El portal solo muestra la etiqueta `Visto` cuando:

- `technician_last_read_at` existe
- es posterior o igual al `last_customer_message_at`

Esto evita mostrar un "Visto" falso si el tecnico abrio el chat antes del
ultimo mensaje del cliente.

## Seguridad y visibilidad

### Cliente portal

El cliente puede ver:

- la conversacion completa mantenida con el tecnico sobre su SAT autorizado

El cliente no debe ver:

- chatter bruto
- followers
- notas internas del chatter
- relaciones indirectas peligrosas

### Usuarios internos

Los usuarios internos autorizados pueden ver la conversacion.

El responsable del SAT es quien debe atenderla operativamente.

### Regla portal

La seguridad debe vivir en:

- ACL
- record rules
- dominios de acceso por `commercial_partner_id`
- controladores que busquen siempre dentro del dominio visible

## Guard multi-tab en el bridge JS

El servicio `operator_chat_bridge.js` abre la ventana de chat del tecnico
cuando llega un evento de bus. El guard correcto es:

```js
if (document.visibilityState !== "visible") { return; }
```

La condicion anterior usaba `!isMainTab && !isVisibleTab`, lo que provocaba
que en produccion (varios tabs abiertos) el tab que tenia el WebSocket activo
(main tab) podia estar en segundo plano y la llamada a `thread.open()` llegaba
a una pestaña no visible. En test el error no se reproducla porque solo habia
un tab abierto.

Regla: para decidir si hay que abrir el chat al tecnico, la unica condicion
relevante es si el tab actual esta visible, no si es el tab principal.

## Riesgos a vigilar

- mezclar de nuevo la conversacion SAT con el chatter tecnico
- hacer depender demasiado la solucion de Discuss como fuente de verdad
- dejar el routing ambiguo entre `res.users` y `hr.employee`
- exponer datos sensibles en portal o en el lateral de conversacion
- generar varias conversaciones para el mismo SAT en lugar de un hilo unico
- introducir mejoras de tiempo real que rompan la estabilidad del popup portal
- no respetar el debounce y volver a notificar al tecnico en cada mensaje del cliente
- ampliar los horarios laborables del SLA sin actualizar la constante `_SLA_WINDOWS`
