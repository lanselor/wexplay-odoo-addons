# Wex WhatsApp Chatter

Modulo Wexplay para preparar mensajes de WhatsApp desde Odoo 18 y abrir WhatsApp Web/App mediante enlaces `wa.me`.

## Objetivo funcional

Permitir que usuarios internos preparen mensajes a clientes desde el chatter o desde un asistente, usando plantillas reutilizables y variables seguras, sin integrar todavia una API oficial de WhatsApp ni confirmar el envio real del mensaje.

El modulo registra en el chatter que el mensaje fue preparado desde Odoo. Esta nota no significa que el usuario haya pulsado enviar dentro de WhatsApp.

## Alcance actual

- Boton de WhatsApp en chatter.
- Asistente `whatsapp.compose.wizard`.
- Plantillas `whatsapp.template`.
- Clasificacion de plantillas por modelo, grupo funcional y secuencia.
- Filtros rapidos locales bajo el selector de plantilla, sin recargar el wizard.
- Variables seguras tipo `${object.name}`, `${partner.name}`, `${company.name}` y `${user.name}`.
- Alias funcionales para SAT y documentos:
  - `${portal_url}` para portal nativo de Odoo.
  - `${dispositivo}` para tipo, marca y modelo del dispositivo SAT.
  - `${importe}` para total del documento o Total SAT si existe.
  - `${referencia_cliente}` para referencia cliente en `repair.order`.
  - `${notasreparacion}` para notas de reparacion nativas de Odoo Repair.
- Apertura de WhatsApp mediante `https://wa.me/...`.
- Registro visual del mensaje preparado en el chatter del documento origen.
- Previsualizacion tipo WhatsApp antes de abrir el enlace.
- Bloqueo si quedan variables sin resolver.
- Insercion controlada de enlaces de portal nativo filtrados por cliente.
- Soporte funcional para:
  - `sale.order`
  - `account.move`
  - `repair.order`
  - `res.partner`

## Enlaces de portal

El modulo base solo gestiona enlaces nativos de Odoo:

- documento actual si es `sale.order` o `account.move`,
- cotizacion/pedido del cliente,
- factura del cliente.

Los documentos seleccionables se filtran por el cliente del wizard y se vuelven a validar en Python antes de insertar el enlace.

El portal B2B privado de reparaciones no vive en este modulo. Se integra mediante el modulo puente opcional `wexplay_portal_whatsapp`, que anade `${enlaceportalB2B}`.

## Limitaciones conocidas

- No usa la API oficial de WhatsApp.
- No confirma si el mensaje se envio finalmente.
- El wizard sigue concentrando bastante logica, aunque ya esta dividido en helpers claros.
- La ayuda de variables vive en XML y debe mantenerse sincronizada con el render Python.
- `whatsapp.template.render_body()` y `whatsapp.compose.wizard._render_text()` no deben divergir conceptualmente.
- El selector de plantillas replica de forma aislada el template Many2One nativo de Odoo; debe revisarse al actualizar Odoo.
- Los grupos de plantillas se mantienen en Python y en el widget JavaScript; cualquier grupo nuevo debe actualizar ambas definiciones.
- Sin API oficial no hay confirmacion tecnica de entrega, lectura ni envio real.

## Verificacion basica

1. Actualizar el modulo `wex_whatsapp_chatter`.
2. Abrir un documento soportado con chatter.
3. Pulsar WhatsApp.
4. Seleccionar o revisar destinatario, telefono, plantilla y cuerpo.
5. Usar los filtros rapidos bajo Plantilla si se necesita acotar el desplegable; comprobar que no se recarga la modal.
6. Si aplica, insertar enlace de portal nativo desde la pestana Portal.
7. Confirmar que la previsualizacion muestra el contenido esperado.
8. Pulsar Abrir WhatsApp.
9. Confirmar que se abre WhatsApp y que Odoo deja una nota en el chatter.

## Verificacion de variables SAT

1. Crear una plantilla para `repair.order`.
2. Incluir `${dispositivo}`, `${importe}`, `${referencia_cliente}` y `${notasreparacion}`.
3. Abrir WhatsApp desde una reparacion con datos en esos campos.
4. Confirmar que el wizard sustituye las variables.
5. Confirmar que `${notasreparacion}` se muestra como texto limpio aunque el campo nativo sea HTML.
