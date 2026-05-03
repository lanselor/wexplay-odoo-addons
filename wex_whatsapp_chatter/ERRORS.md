# Errores y aprendizajes - Wex WhatsApp Chatter

Este archivo recoge errores reales detectados durante desarrollo, pruebas o validacion del modulo.

Su objetivo no es listar deuda teorica, sino conservar aprendizajes practicos para evitar repetir fallos.

## Formato recomendado

```text
## YYYY-MM-DD - Titulo breve

Contexto:

Sintoma:

Causa:

Correccion:

Validacion:

Aprendizaje:
```

## Errores registrados

## 2026-05-02 - Modelos WhatsApp soportados no estaban centralizados

Contexto:

Durante Fase 1 se reviso la disponibilidad del modulo desde Contactos y el comportamiento del boton de WhatsApp en chatter.

Sintoma:

`res.partner` estaba incluido en la seleccion del wizard, pero el modulo no tenia una regla central clara que definiese los modelos soportados ni una proteccion explicita en el boton JS.

Causa:

La lista de modelos soportados vivia de forma implicita en varias piezas: seleccion del wizard, dominios de plantilla y contexto enviado desde chatter. Eso hacia mas facil que Contactos quedase tratado de forma incompleta o que el wizard recibiese modelos no soportados.

Correccion:

Se centralizo la lista de modelos soportados en Python y se reflejo la misma lista en el boton de chatter. Se incluyo `res.partner` explicitamente como modelo soportado.

Validacion:

Pendiente de validacion funcional en Odoo: abrir Contactos, entrar en un contacto con chatter, pulsar WhatsApp y confirmar que el wizard carga con modelo `res.partner`, contacto y telefono.

Aprendizaje:

Las integraciones de chatter no deben aceptar cualquier `threadModel` por defecto. Si el modulo solo soporta ciertos modelos, esa decision debe estar documentada y protegida en Python y en la UI.

## 2026-05-02 - Cambio de origen de telefono no actualizaba el numero

Contexto:

Durante Fase 2 se reviso el comportamiento del asistente al alternar entre `mobile`, `phone` y `custom`.

Sintoma:

Al cambiar el campo Origen Telefono entre movil, telefono fijo y personalizado, el numero mostrado no siempre cambiaba correctamente. Ademas, al cambiar de contacto podia sobrescribirse un numero manual.

Causa:

Solo existia onchange para `partner_id`. No habia onchange especifico para `phone_source`, y la logica de seleccion de telefono estaba incrustada directamente en `_onchange_partner`.

Correccion:

Se anadieron helpers para calcular el origen y el numero por contacto. Se creo un onchange especifico de `phone_source`. `custom` conserva el numero manual y no lo sobrescribe automaticamente.

Validacion:

Pendiente de validacion funcional en Odoo: abrir el wizard, seleccionar un contacto con movil y telefono, alternar entre `mobile`, `phone` y `custom`, escribir un numero manual y confirmar que no se pisa inesperadamente.

Aprendizaje:

Los campos de seleccion que cambian el significado de otro campo deben tener onchange propio. No basta con recalcular solo cuando cambia el contacto.

## 2026-05-02 - Variables de ayuda copiaban un caracter invisible

Contexto:

El panel informativo de plantillas mostraba ejemplos como `${dispositivo}` usando un caracter invisible entre `$` y `{` para evitar que la vista OWL se rompiese.

Sintoma:

Visualmente parecia `${dispositivo}`, pero al copiarlo al cuerpo del mensaje se copiaba tambien el caracter invisible. El render del wizard no reconocia la variable hasta borrar manualmente ese caracter.

Causa:

Se uso `&#8203;` como separador invisible dentro del ejemplo (`$&#8203;{...}`). Eso solucionaba el problema visual/OWL, pero introducia un caracter real en el portapapeles.

Correccion:

Se sustituyo por `&#36;{...}`. El XML ya no contiene literalmente `${...}`, pero el navegador renderiza y copia `${...}` sin caracteres intermedios.

Validacion:

El XML de `whatsapp_template_views.xml` parsea correctamente y ya no quedan ocurrencias de `&#8203;` en los ejemplos.

Aprendizaje:

No usar caracteres invisibles en textos que el usuario debe copiar. Para ejemplos sensibles en XML/QWeb/OWL, preferir entidades HTML que rendericen el caracter real sin alterar el texto copiado.

## 2026-05-02 - OWL evaluaba ejemplos `${...}` como expresiones JS

Contexto:

Tras sustituir el caracter invisible por `&#36;{...}`, la vista de plantillas seguia mostrando ejemplos copiables de variables para WhatsApp.

Sintoma:

La vista rompia con `ReferenceError: dispositivo is not defined` al abrir el formulario. OWL interpretaba `${dispositivo}` como una expresion de template literal durante la compilacion.

Causa:

Aunque el XML no contenia literalmente el simbolo `$`, la entidad `&#36;` se resolvia antes o durante el proceso de compilacion y OWL acababa viendo el patron `${...}` completo.

Correccion:

Se partieron los ejemplos en dos nodos visibles dentro de `<code>`: `<span>$</span>{campo}`. Asi OWL no ve el patron `${...}` como texto continuo en el template, pero el navegador deberia mostrar y copiar `${campo}` sin caracteres invisibles.

Validacion:

Pendiente de validacion funcional en Odoo: abrir Plantillas de WhatsApp y confirmar que la vista carga sin OwlError y que copiar un ejemplo lo pega como `${campo}`.

Aprendizaje:

En vistas OWL, evitar que el template contenga `${...}` como texto continuo, incluso si el `$` viene de una entidad HTML. Para textos copiables, partir el patron en nodos DOM visibles.

## 2026-05-02 - Selector de enlace portal permitia documentos de otros clientes

Contexto:

El wizard de WhatsApp permitia seleccionar cotizaciones y facturas desde el bloque de enlace de portal.

Sintoma:

El usuario podia seleccionar una cotizacion o factura de cualquier cliente y enviarla por WhatsApp al cliente seleccionado en el wizard.

Causa:

Los campos `sale_order_id` y `account_move_id` no estaban filtrados ni validados por el cliente seleccionado. Ademas, el bloque mezclaba portal nativo de Odoo y portal B2B Wexplay como si fueran el mismo tipo de enlace.

Correccion:

Se anadio un tipo explicito de enlace, filtros por cliente en la vista y validacion Python por `commercial_partner_id`. La integracion B2B SAT se movio a un modulo puente opcional `wexplay_portal_whatsapp`.

Validacion:

Pendiente de validacion funcional en Odoo: confirmar que solo aparecen documentos del cliente, que no se puede insertar un documento ajeno y que el enlace B2B SAT solo aparece si el modulo puente esta instalado.

Aprendizaje:

Los dominios visuales ayudan, pero cualquier seleccion de documentos enviados al cliente debe validarse tambien en servidor. Los portales tokenizados nativos y el portal B2B privado no deben mezclarse en el modulo base.

## 2026-05-03 - Variables mal escritas podian pasar desapercibidas

Contexto:

Las plantillas permiten variables como `${partner.name}` o `${object.name}`. Si una variable se escribia mal, el usuario podia no detectarlo hasta revisar manualmente el texto.

Sintoma:

Una variable desconocida podia quedar en el mensaje final o ser dificil de detectar visualmente antes de abrir WhatsApp.

Causa:

El wizard no tenia una comprobacion final especifica para restos `${...}` antes de abrir WhatsApp.

Correccion:

Las variables desconocidas se conservan como `${...}` durante el render y `action_open_whatsapp()` bloquea la apertura si detecta placeholders sin resolver.

Validacion:

Pendiente de validacion funcional en Odoo: crear una plantilla con `${variable_inexistente}`, abrir el wizard y confirmar que el boton Abrir WhatsApp muestra un error claro.

Aprendizaje:

En comunicaciones al cliente es preferible bloquear por exceso ante variables dudosas. No deben borrarse silenciosamente variables desconocidas.

## 2026-05-03 - Ambiguedad entre portal nativo y portal B2B

Contexto:

El wizard puede insertar enlaces de portal nativo de Odoo y, mediante modulo puente, enlaces privados del portal B2B Wexplay.

Sintoma:

Usar una etiqueta generica tipo `${enlaceportal}` podia llevar a confundir enlaces tokenizados nativos con enlaces privados B2B.

Causa:

La palabra "portal" describe dos flujos distintos: portal nativo Odoo para documentos y portal B2B Wexplay para reparaciones.

Correccion:

Se mantiene `${portal_url}` para enlaces nativos de Odoo y se reserva `${enlaceportalB2B}` para el modulo puente `wexplay_portal_whatsapp`.

Validacion:

Pendiente de validacion funcional en Odoo: comprobar que el boton Insertar enlace reemplaza `${portal_url}` en enlaces nativos y `${enlaceportalB2B}` en reparaciones B2B.

Aprendizaje:

Las variables copiables por usuarios deben nombrar el concepto funcional exacto que representan, especialmente cuando dos integraciones usan palabras parecidas.

## 2026-05-03 - Placeholder B2B podia contaminarse con enlace nativo

Contexto:

El wizard permite insertar `${portal_url}` para enlaces nativos de Odoo y `${enlaceportalB2B}` para enlaces privados del portal B2B Wexplay.

Sintoma:

Si primero se insertaba un enlace B2B y despues se cambiaba el selector a una cotizacion/factura nativa, el enlace B2B ya insertado podia cambiarse por el enlace tokenizado nativo. Tambien se resolvia `${portal_url}` en el mismo flujo.

Causa:

Ambas etiquetas dependian del mismo campo tecnico `portal_url`, que cambia segun `portal_link_type`. Ademas, el onchange de `sale_order_id` y `account_move_id` re-aplicaba la plantilla completa y podia pisar contenido ya editado o enlaces ya insertados.

Correccion:

`${portal_url}` solo se resuelve cuando el tipo de enlace activo es nativo. `${enlaceportalB2B}` solo se resuelve cuando el tipo activo es B2B. Seleccionar cotizacion o factura ya no re-renderiza automaticamente el cuerpo del mensaje.

Validacion:

Pendiente de validacion funcional en Odoo: crear un mensaje con `${enlaceportalB2B}` y `${portal_url}`, insertar primero B2B, cambiar a cotizacion, insertar enlace nativo y confirmar que el enlace B2B existente no se modifica.

Aprendizaje:

Las variables que representan integraciones distintas deben estar acotadas por tipo funcional, aunque compartan almacenamiento tecnico temporal. Cambiar documentos auxiliares no debe re-renderizar el mensaje editable del usuario.
