# Wexplay Portal WhatsApp

Modulo puente opcional entre `wex_whatsapp_chatter` y `wexplay_portal`.

## Objetivo

Anadir al wizard de WhatsApp la posibilidad de insertar un enlace privado B2B a la reparacion SAT visible en el portal Wexplay.

Este modulo evita que `wex_whatsapp_chatter` dependa directamente de `wexplay_portal`.

## Regla funcional

El enlace de reparacion B2B solo puede insertarse si:

- el wizard se abre desde una `repair.order`,
- la reparacion pertenece al cliente seleccionado,
- el cliente tiene un usuario portal activo,
- el cliente pertenece al grupo portal nativo de Odoo mediante dicho usuario.

Si no se cumple, el wizard muestra el estado y bloquea la insercion del enlace.

## Variables

Este modulo anade el alias:

- `${enlaceportalB2B}`: enlace privado B2B de la reparacion en el portal Wexplay.

El alias `${portal_url}` queda reservado para enlaces nativos de Odoo gestionados por `wex_whatsapp_chatter`.
