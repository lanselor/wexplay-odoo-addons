# Arquitectura - Wex WhatsApp Chatter

## Responsabilidades

`wex_whatsapp_chatter` debe ser un modulo ligero de comunicacion asistida por WhatsApp. Su responsabilidad es preparar mensajes, abrir WhatsApp y dejar trazabilidad interna en chatter.

No debe convertirse en:

- motor de mensajeria multicanal,
- sustituto de `mail.template`,
- integracion oficial de WhatsApp Business,
- repositorio de reglas SAT, ventas o facturacion.

El modulo base no debe depender de `wexplay_portal`. Cualquier enlace privado B2B especifico de Wexplay Portal debe vivir en un modulo puente opcional.

## Modelos

### `whatsapp.template`

Define plantillas reutilizables por modelo funcional.

Responsabilidades:

- nombre,
- compania opcional,
- modelo al que aplica,
- grupo funcional de filtrado,
- orden de aparicion,
- cuerpo del mensaje.

La seleccion de modelo es deliberadamente explicita para evitar plantillas ambiguas o usadas en documentos incorrectos.

### `whatsapp.compose.wizard`

Asistente transitorio para preparar y abrir el mensaje.

Responsabilidades actuales:

- resolver documento origen,
- resolver contacto,
- seleccionar origen de telefono,
- renderizar plantilla,
- calcular enlace portal cuando aplica,
- normalizar telefono,
- abrir WhatsApp,
- registrar nota en chatter.

Deuda reconocida: el wizard concentra demasiada logica. En fases posteriores debe dividirse en helpers pequenos y con nombres semanticos.

Separacion interna actual:

- `_prepare_origin_defaults()`: prepara valores desde el documento origen del chatter.
- `_get_target_record()`: resuelve el registro funcional sobre el que trabaja el wizard.
- `_get_default_phone_source()` y `_get_phone_number_for_source()`: concentran la seleccion de telefono.
- `_get_portal_link_url()` y `_get_portal_link_status()`: concentran la preparacion y validacion de enlaces de portal.
- `_get_render_context()` y `_render_placeholder()`: concentran el render seguro de variables.
- `_check_no_unresolved_placeholders()`: bloquea el envio si quedan variables `${...}` sin resolver.
- `_prepare_whatsapp_open_note_body()`: prepara el cuerpo HTML de la nota en chatter.
- `_prepare_whatsapp_url()`: prepara el enlace final de WhatsApp.

## Enlaces de portal

`wex_whatsapp_chatter` solo gestiona enlaces nativos de Odoo:

- documento actual si es `sale.order` o `account.move`,
- cotizacion/pedido del cliente,
- factura del cliente.

Las cotizaciones y facturas deben filtrarse y validarse por el cliente seleccionado en el wizard. No basta con el dominio visual: la validacion Python debe impedir insertar documentos de otro cliente.

El enlace privado B2B de reparaciones no pertenece al modulo base. Vive en `wexplay_portal_whatsapp`, que depende de:

- `wex_whatsapp_chatter`,
- `wexplay_portal`.

Las variables de portal deben resolverse solo dentro de su tipo funcional:

- `${portal_url}` solo representa enlaces nativos de Odoo.
- `${enlaceportalB2B}` solo representa enlaces privados B2B aportados por `wexplay_portal_whatsapp`.

Cambiar el documento auxiliar del bloque de enlace no debe re-renderizar el cuerpo editable del mensaje, para no pisar texto manual ni enlaces ya insertados.

## Modelos soportados

El modulo debe tratar como soportados:

- `sale.order`
- `account.move`
- `repair.order`
- `res.partner`

Si el boton aparece en modelos no soportados, el comportamiento debe degradar de forma clara y no abrir un wizard inconsistente.

La lista de modelos soportados debe mantenerse centralizada en Python y reflejada en el filtro del boton de chatter. `res.partner` forma parte del alcance funcional y debe estar disponible desde Contactos.

## Seguridad

Grupos actuales:

- `group_whatsapp_user`: puede usar plantillas y wizard.
- `group_whatsapp_template_manager`: puede crear, editar y eliminar plantillas.

Las plantillas tienen regla multi-company:

- globales si `company_id` esta vacio,
- visibles si `company_id` pertenece a las companias permitidas del usuario.

## Render de plantillas

El render actual del wizard usa un sustituidor seguro basado en rutas de campos y no evalua codigo arbitrario.

Variables soportadas por concepto:

- `${object.*}`: documento origen.
- `${partner.*}`: contacto seleccionado.
- `${company.*}`: compania del wizard.
- `${user.*}`: usuario actual.
- `${portal_url}`: enlace del portal nativo de Odoo cuando aplica.
- `${importe}`: importe del documento; en SAT usa `x_sat_total_amount` si existe.
- `${dispositivo}`: helper especial para modelos SAT con dispositivo.
- `${referencia_cliente}`: alias legible para `repair.order.x_customer_reference`.
- `${notasreparacion}`: alias legible para `repair.order.internal_notes`, convertido de HTML a texto plano para WhatsApp.

El enlace B2B privado no forma parte del modulo base. El alias `${enlaceportalB2B}` vive en `wexplay_portal_whatsapp`.

Deuda reconocida:

- `whatsapp.template.render_body()` y `whatsapp.compose.wizard._render_text()` no deben divergir conceptualmente.
- La documentacion de variables en la vista debe coincidir con lo que Python renderiza realmente.
- El mapa de grupos admitidos vive en Python y los botones con sus iconos viven en JavaScript. Al crear un grupo nuevo deben actualizarse ambos lados y anadirse una prueba de regresion.

La entrada visual de MRW en el selector pertenece a este mapa JavaScript,
aunque el modelo y el grupo `mrw_shipping` se aportan desde el puente opcional
`mrw_shipping_whatsapp`. Esta referencia no crea una dependencia hacia MRW:
sin el puente, el modelo no puede seleccionarse en el wizard.

Rendimiento:

- Las rutas de variables siguen limitadas a seis niveles.
- Si una ruta devuelve una relacion multiple, el renderer solo recorre y muestra los primeros cinco registros. No debe ampliarse ese limite sin medir el impacto sobre plantillas reales.

## Integracion con SAT

El modulo tiene reglas defensivas para evitar plantillas cruzadas cuando el origen es `repair.order`.

Esa decision es funcionalmente valida, pero debe mantenerse dentro de Python y documentarse. No debe depender solo de dominios XML.

## Trazabilidad

Al pulsar Abrir WhatsApp se publica una nota en el chatter del documento origen.

La nota significa:

- mensaje preparado desde Odoo,
- usuario que preparo el mensaje,
- destinatario y telefono usados,
- plantilla usada si existe.
- etiqueta visual `WhatsApp preparado` para localizarla mejor en el historial.

La nota no significa:

- mensaje enviado,
- mensaje recibido,
- confirmacion de lectura,
- comunicacion certificada.

## UX del wizard

El campo `rendered_body` sigue siendo el texto editable que se enviara a WhatsApp.

### Selector de plantillas y filtros rapidos

El selector principal de plantilla usa el widget OWL
`wex_whatsapp_template_picker`. Los filtros rapidos se mantienen solo en el
cliente mientras el wizard esta abierto y se anaden al dominio de cada busqueda
de plantillas. No escriben el wizard ni lo reabren. La regla multi-company de
plantillas sigue aplicandose en servidor mediante record rules.

Deuda tecnica reconocida:

- El widget replica el template interno `web.Many2OneField` de Odoo para poder
  anadir los filtros sin modificar el selector global. Se eligio este
  aislamiento despues de comprobar que una herencia directa afectaba a todos
  los campos Many2One y podia romper su ciclo de vida OWL.
- Al actualizar Odoo, revisar este widget frente al template nativo y validar
  seleccion, busqueda, `Buscar mas...`, apertura del registro y los filtros.
- Si Odoo ofrece un punto de extension local suficiente en una version futura,
  sustituir la copia por una composicion del campo nativo.
- `write()` del wizard mantiene validacion por registro para conservar las
  guardas de contexto SAT. El flujo normal usa un solo wizard; si en el futuro
  se anaden operaciones en lote, debe refactorizarse para validar y escribir
  en batch antes de reutilizarlo fuera de este asistente.

Decisiones cerradas:

- Las notas de chatter solo se crean al preparar WhatsApp o al registrar un
  intento anomalo de cambio de contexto. Crear un wizard normal de SAT no debe
  dejar una nota de "modelo normalizado".
- `rendered_body` no es obligatorio a nivel ORM para permitir interacciones de
  UI antes de seleccionar una plantilla. `action_open_whatsapp()` conserva la
  validacion final de mensaje no vacio.
- No existe una configuracion de favoritas o acceso rapido mientras no tenga
  un consumidor funcional. La organizacion de plantillas se hace por grupo y
  secuencia.

El wizard muestra una previsualizacion visual tipo burbuja para revisar:

- saltos de linea,
- longitud aproximada,
- variables ya sustituidas,
- posibles restos visibles antes de abrir WhatsApp.
- formato WhatsApp basico: `*negrita*`, `_cursiva_`, `~tachado~` y ```monospace```.

Antes de abrir WhatsApp, el servidor bloquea el flujo si detecta variables `${...}` sin resolver.

## Registro de errores y aprendizajes

El modulo debe mantener un archivo `ERRORS.md` con errores reales detectados durante desarrollo, pruebas o validacion funcional.

Objetivo:

- evitar repetir errores ya detectados,
- dejar claro que se rompio y por que,
- documentar la correccion aplicada,
- registrar como verificar que no vuelve a ocurrir.

Cada vez que se detecte un error relevante, antes de darlo por cerrado debe anadirse una entrada breve en `ERRORS.md`.

Una entrada debe incluir:

- fecha,
- contexto,
- sintoma,
- causa,
- correccion,
- prueba de validacion,
- aprendizaje o regla preventiva.
