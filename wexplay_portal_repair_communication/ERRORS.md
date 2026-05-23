# Errores y aprendizajes - Wexplay Portal Repair Communication

Este archivo registra errores reales detectados durante desarrollo,
pruebas o validacion funcional del modulo.

Objetivo:

- evitar repetir errores ya detectados
- dejar claro que se rompio y por que
- documentar la correccion aplicada
- registrar como verificar que no vuelve a ocurrir

## 2026-05-20 - Template Owl con `t-elif` vacio

- contexto: extension OWL de `mail.Chatter`
- sintoma: `Failed to compile template "mail.Chatter": Unexpected token ')'`
- causa: un `t-elif` vacio genero `else if ()` en el codigo compilado
- correccion: sustituirlo por una condicion real y mover handlers delicados a
  metodos JS explicitos
- prueba de validacion: recompilar assets y abrir una reparacion con chatter
- aprendizaje o regla preventiva: no dejar ramas `t-elif` vacias en parches OWL

## 2026-05-20 - RPC a metodo privado desde frontend

- contexto: carga de conversacion SAT en backend
- sintoma: `Private methods (...) cannot be called remotely`
- causa: el patch JS llamaba por RPC a un metodo privado del modelo
- correccion: crear un metodo publico para el RPC y mantener el helper privado
  como implementacion interna
- prueba de validacion: abrir la conversacion portal desde backend sin error de
  acceso
- aprendizaje o regla preventiva: cualquier dato servido a Owl por `orm.call`
  debe exponerse mediante metodos publicos

## 2026-05-20 - Reasignacion de responsable rompiendo `discuss.channel.member`

- contexto: cambio de `user_id` en `repair.order` con chat SAT ya vivo
- sintoma: popup `El registro no existe o se elimino (discuss.channel.member)`
- causa: se eliminaba un member del canal durante el mismo `web_save`, mientras
  el frontend todavia lo tenia referenciado
- correccion: dejar de borrar members en caliente y archivar/silenciar al
  tecnico saliente dentro del mismo canal
- prueba de validacion: cambiar responsable sin error y comprobar que el tecnico
  antiguo deja de recibir mensajes nuevos
- aprendizaje o regla preventiva: en canales vivos de Discuss, preferir
  desactivar/archivar members frente a `unlink()` inmediato si la UI sigue
  montada

## 2026-05-20 - Import de tests rompiendo la carga del modulo

- contexto: endurecimiento y suite de tests del modulo
- sintoma: el registry no cargaba por `ImportError` al actualizar el modulo
- causa: se importaban tests desde el `__init__` del addon y ademas se usaba una
  clase base de tests no disponible en este Odoo 18 concreto
- correccion: quitar el import de tests del `__init__` raiz y adaptar la clase
  base a la API real del framework
- prueba de validacion: actualizar el modulo sin que caiga el registry
- aprendizaje o regla preventiva: no importar tests desde el arranque normal del
  addon salvo necesidad muy justificada

## 2026-05-20 - Inestabilidad por iteracion AJAX del popup portal

- contexto: intento de mejorar inmediatez del popup portal
- sintoma: la ventana no se reabria bien, los mensajes tardaban mas y la
  sensacion general empeoro
- causa: la iteracion AJAX anadio demasiada logica nueva sobre un flujo que ya
  era estable con submit clasico y polling
- correccion: rollback a la version estable con submit clasico + polling
- prueba de validacion: reabrir popup, enviar y recibir mensajes con el flujo
  anterior
- aprendizaje o regla preventiva: en el popup portal, introducir mejoras de UX
  de forma incremental y reversible

## 2026-05-20 - Colision con `partitionedActions` en `ChatWindow`

- contexto: ocultacion de llamadas y videollamadas en chats SAT del tecnico
- sintoma: `Cannot set property partitionedActions of #<ChatWindow> which has only a getter`
- causa: se creo un getter con el mismo nombre que el `t-set` usado por el
  template base de Owl
- correccion: sustituir el getter por un metodo con nombre propio y hacer que el
  `t-set` llame a ese metodo
- prueba de validacion: abrir el chat SAT sin error Owl y comprobar que desaparecen
  las acciones RTC
- aprendizaje o regla preventiva: al parchear componentes Owl base, evitar
  redefinir nombres usados por `t-set` o por el propio estado del template

---

## Auditoria 2026-05 — Errores detectados y corregidos en la ronda de endurecimiento

### BUG-1 — Guard multi-tab erroneo en `operator_chat_bridge.js`

- contexto: apertura automatica del chat tecnico al llegar mensaje portal
- sintoma: en produccion (multiples tabs Odoo) la ventana de chat no se abre;
  en test funciona el 100% de las veces porque solo hay un tab abierto
- causa: la condicion `!isMainTab && !isVisibleTab` evaluaba incorrectamente
  cuando el tab principal del WebSocket estaba en segundo plano
- correccion: sustituir por `document.visibilityState !== "visible"` como unica
  condicion de guarda; eliminar `multi_tab` de las dependencias del servicio
- prueba de validacion: abrir dos tabs de Odoo, poner el tab principal en
  segundo plano, enviar mensaje desde portal, verificar que se abre el chat en
  el tab visible
- aprendizaje: para decidir si abrir el chat, lo relevante es si el tab es
  visible por el usuario, no si es el sostenedor del WebSocket

### BUG-2 — Fallo silencioso si `thread` no se resuelve en el bridge

- contexto: `operator_chat_bridge.js` llamando a `Thread.getOrFetch()`
- sintoma: error JS no capturado si el canal ha sido eliminado o no es
  accesible, rompiendo la promesa completa
- correccion: comprobar si `thread` es null tras el await y hacer `return` con
  `console.warn` antes de llamar a `thread.open()`
- prueba de validacion: ejecutar el bridge con un `channel_id` inexistente y
  verificar que no hay uncaught promise rejection

### BUG-3 — `_sync_operator_channel_members` duplicado en proyeccion de mensajes

- contexto: `_post_message_to_operator_channel` en `portal_repair_conversation.py`
- sintoma: la sincronizacion de members se ejecutaba dos veces (una al abrir el
  canal y otra al proyectar cada mensaje), lo que podia crear members duplicados
  o lanzar errores de constraint en Discuss bajo carga
- correccion: eliminar la llamada redundante a `_sync_operator_channel_members`
  dentro de `_post_message_to_operator_channel`
- prueba de validacion: proyectar varios mensajes seguidos y verificar que no se
  duplican los members del canal

### BUG-4 — Cache de `wexPortalRepairSidebar` sin discriminar canal

- contexto: patch OWL de `ChatWindow` que carga el contexto SAT lateral
- sintoma: si el tecnico abria primero un canal sin SAT, el resultado `enabled=false`
  se cacheaba y no se recargaba al cambiar a un canal con SAT real
- correccion: anadir `_wexSidebarCheckedChannelId` al estado del componente y
  comparar el id del canal antes de usar el resultado en cache
- prueba de validacion: abrir chat sin SAT, luego abrir chat SAT real, verificar
  que el panel SAT aparece correctamente

### BUG-5 — `@api.depends("id")` prohibido en Odoo 18

- contexto: campo computed `_compute_portal_conversation_fields` en `repair.order`
- sintoma: `NotImplementedError: Compute method cannot depend on field 'id'.`
  al arrancar el servidor; el modulo no cargaba
- correccion: eliminar el decorador `@api.depends("id")`. Para campos no
  almacenados en Odoo 18, la ausencia del decorador implica recomputacion en
  cada acceso, que es el comportamiento correcto
- aprendizaje: en Odoo 18 no usar `@api.depends("id")` en ningun campo computado

### BUG-6 — Longitud de mensajes portal sin limite

- contexto: controlador `portal.py` que recibe el cuerpo del mensaje
- sintoma: un cliente malintencionado o un error de UI podia enviar mensajes de
  tamano arbitrario, sobrecargando la base de datos y el log del servidor
- correccion: anadir constante `_MAX_MESSAGE_LENGTH = 5000` y truncar el body
  antes de pasarlo al modelo con `body[:_MAX_MESSAGE_LENGTH]`
- prueba de validacion: enviar mensaje de 10000 caracteres y verificar que se
  guarda truncado a 5000

### BUG-7 — `x_portal_conversation_html` con `sanitize=False` sin justificacion

- contexto: campo `Html` en `repair.order` que renderizaba la conversacion
- sintoma: riesgo de XSS si el contenido del campo llegaba a una plantilla sin
  el escape adecuado; ademas el campo no estaba referenciado en ninguna vista
- correccion: eliminar el campo completamente. El backend ya usa el metodo RPC
  `get_portal_repair_conversation_values()` via OWL, haciendo el campo obsoleto
- aprendizaje: `sanitize=False` en campos `Html` solo es admisible si el
  contenido viene exclusivamente de codigo Python controlado, nunca de entrada
  de usuario o datos no auditados

### BUG-8 — Timeout de polling en portal no protegido contra errores de red

- contexto: `portal_repair_conversation_portal.js`, intervalo de polling a 2500ms
- sintoma: un error de red puntual podia romper el ciclo de polling y dejar la
  pagina sin actualizar hasta recargar manualmente
- correccion: envolver la llamada fetch dentro del intervalo en try/catch para
  que un fallo puntual no destruya el intervalo completo

---

## Errores durante la implementacion de mejoras — 2026-05

### ERR-IMP-1 — Campo `numbercall` eliminado en Odoo 18

- contexto: creacion del cron `ir_cron_sla.xml` para el chequeo SLA
- sintoma: `ValueError: Invalid field 'numbercall' on model 'ir.cron'`
  al instalar el modulo tras anadir el cron
- causa: el campo `numbercall` fue eliminado del modelo `ir.cron` en Odoo 18;
  en versiones anteriores se usaba para limitar el numero de ejecuciones
- correccion: eliminar la linea `<field name="numbercall">-1</field>` del XML
- aprendizaje: al crear crons en Odoo 18, no incluir `numbercall`; los crons
  son infinitos por defecto

### ERR-IMP-2 — `@api.depends("id")` prohibido (reproduccion durante mejoras)

- contexto: anadido durante la adicion de campos SLA al modelo de conversacion
- sintoma: el servidor no arrancaba con `NotImplementedError`
- causa: idem BUG-5; se repitio el error al decorar el nuevo campo computado
  `_compute_sla_breached` con `@api.depends("id")`
- correccion: mismo patron — quitar el decorador o usar un campo real como
  dependencia (`sla_deadline`, `sla_notified_at`)
- aprendizaje: en Odoo 18, `@api.depends("id")` no es una forma valida de
  forzar recomputacion; usar el campo real del que depende el resultado

### ERR-PROD-1 — Apertura del chat rota en escenarios multi-tab reales

- contexto: mensajes cliente -> tecnico tras el cambio del bridge JS para usar
  solo `document.visibilityState`
- sintoma: el mensaje entra correctamente en backend y en la conversacion SAT,
  pero el chat no se abre al tecnico cuando trabaja con varias pestanas de Odoo
- causa: el evento del bus puede llegar a la pestana que sostiene la sesion
  principal/WebSocket, mientras la pestana visible del tecnico es otra; al
  quitar el relay entre pestanas, la pestana visible no recibia la orden de
  apertura
- correccion: mantener la apertura segura por visibilidad y reenviar la orden
  a otras pestanas mediante `localStorage` + evento `storage`, de forma que la
  pestana visible pueda abrir el canal aunque no sea la que recibe el bus
- prueba de validacion: abrir dos pestanas Odoo, dejar la principal en segundo
  plano, enviar mensaje desde portal y verificar que la pestana visible abre el
  chat SAT
- aprendizaje: en flujos Discuss multi-tab, no basta con decidir "si esta
  visible"; tambien hay que garantizar que la pestana visible reciba el evento
