# Wexplay Portal WhatsApp

Modulo puente opcional entre `wex_whatsapp_chatter` y `wexplay_portal`.

## Objetivo

Anadir al wizard de WhatsApp la posibilidad de insertar un enlace privado B2B a la reparacion SAT visible en el portal Wexplay.

Este modulo evita que `wex_whatsapp_chatter` dependa directamente de `wexplay_portal`.

## Dependencias

- `wex_whatsapp_chatter`
- `wexplay_portal`
- `wexplay_repair_workflow`

La dependencia con el portal B2B y con el workflow SAT de presupuesto queda aislada aqui. El modulo base de WhatsApp debe poder instalarse y funcionar sin `wexplay_portal`.

## Regla funcional

El enlace de reparacion B2B solo puede insertarse si:

- el wizard se abre desde una `repair.order`,
- la reparacion pertenece al cliente seleccionado,
- el cliente tiene un usuario portal activo,
- el cliente pertenece al grupo portal nativo de Odoo mediante dicho usuario,
- el presupuesto ya ha sido iniciado,
- la reparacion esta en `Espera cliente`,
- la cotizacion vinculada ya esta creada.

Si no se cumple, el wizard muestra el estado y bloquea la insercion del enlace.

## Variables

Este modulo anade el alias:

- `${enlaceportalB2B}`: enlace privado B2B de la reparacion en el portal Wexplay.

El alias `${portal_url}` queda reservado para enlaces nativos de Odoo gestionados por `wex_whatsapp_chatter`.

## Comportamiento esperado

- Al abrir el wizard desde una `repair.order`, el tipo de enlace por defecto es B2B si este modulo esta instalado.
- El enlace generado apunta a la ficha privada de la reparacion en `/my/repairs/<id>`.
- Si el cliente no tiene portal activo, el wizard muestra estado visual y no permite insertar el enlace.
- Si el presupuesto no esta listo para decision del cliente, el wizard informa de cada condicion incumplida y no inserta el enlace.
- Si la reparacion no pertenece al cliente seleccionado, la insercion queda bloqueada.
- Cambiar a un enlace nativo de Odoo no debe modificar un enlace B2B ya insertado en el cuerpo del mensaje.

## Verificacion funcional

1. Instalar o actualizar `wex_whatsapp_chatter` y `wexplay_portal_whatsapp`.
2. Abrir una reparacion de un cliente con usuario portal activo.
3. Abrir el wizard de WhatsApp desde el chatter.
4. Confirmar que aparece el estado `Portal B2B activo`.
5. Usar `${enlaceportalB2B}` en el cuerpo y pulsar insertar enlace.
6. Confirmar que se sustituye solo esa etiqueta.
7. Anadir tambien `${portal_url}`, cambiar a cotizacion/factura nativa e insertar enlace.
8. Confirmar que el enlace B2B ya insertado no cambia.
