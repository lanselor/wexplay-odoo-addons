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
