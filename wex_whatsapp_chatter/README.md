# Wex WhatsApp Chatter

Modulo Wexplay para preparar mensajes de WhatsApp desde Odoo 18 y abrir WhatsApp Web/App mediante enlaces `wa.me`.

## Objetivo funcional

Permitir que usuarios internos preparen mensajes a clientes desde el chatter o desde un asistente, usando plantillas reutilizables y variables seguras, sin integrar todavia una API oficial de WhatsApp ni confirmar el envio real del mensaje.

El modulo registra en el chatter que el mensaje fue preparado desde Odoo. Esta nota no significa que el usuario haya pulsado enviar dentro de WhatsApp.

## Alcance actual

- Boton de WhatsApp en chatter.
- Asistente `whatsapp.compose.wizard`.
- Plantillas `whatsapp.template`.
- Variables simples tipo `${object.name}`, `${partner.name}`, `${company.name}` y `${user.name}`.
- Apertura de WhatsApp mediante `https://wa.me/...`.
- Registro visual del mensaje preparado en el chatter del documento origen.
- Soporte funcional previsto para:
  - `sale.order`
  - `account.move`
  - `repair.order`
  - `res.partner`

## Limitaciones conocidas

- No usa la API oficial de WhatsApp.
- No confirma si el mensaje se envio finalmente.
- El wizard concentra demasiadas responsabilidades y debe separarse en fases posteriores.
- La ayuda de variables vive actualmente en XML y debe alinearse con el render real.
- Contactos debe validarse en Fase 1 como origen visible y soportado desde el chatter.
- El cambio entre `mobile`, `phone` y `custom` tiene un bug pendiente de Fase 2.

## Verificacion basica

1. Actualizar el modulo `wex_whatsapp_chatter`.
2. Abrir un documento soportado con chatter.
3. Pulsar WhatsApp.
4. Seleccionar o revisar destinatario, telefono, plantilla y cuerpo.
5. Pulsar Abrir WhatsApp.
6. Confirmar que se abre WhatsApp y que Odoo deja una nota en el chatter.
