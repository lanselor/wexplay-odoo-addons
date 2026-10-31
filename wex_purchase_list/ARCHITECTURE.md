# Wex Purchase List Architecture

## Estado actual y aceptación — 01/11/2026

Versión `18.0.1.5.0`. El usuario confirma que el funcionamiento probado es correcto y acepta iniciar su uso diario. Queda abierta la observación de casos reales del taller; esta aceptación no implica que ya se hayan probado todos los proveedores, usuarios o escenarios en producción.

El resumen funcional consolidado está en `RELEASE_NOTES.md`; las decisiones se conservan en `DECISION_LOG.md`, los pasos de comprobación en `VALIDATION.md` y el registro transversal en `C:\odoo18\WEXPLAY_CHANGELOG.md`. Los apartados por fase y versión siguientes conservan la evolución histórica y no deben interpretarse como capacidades todavía pendientes si un apartado posterior ya las implementa.

## Motivos, nueva solicitud SAT y resolución excepcional — 18.0.1.5.0

- Las nuevas solicitudes de apartamiento requieren `return_reason`; `other` exige observaciones. Los campos históricos son anulables para conservar registros anteriores sin inventar motivos. El envío de una devolución antigua no exige completar el motivo ni una resolución.
- El asistente ofrece una nueva solicitud SAT opcional solo fuera de `done` y `delivered`. Crea un `stock.move` de tipo `add` nuevo y reutiliza `_add_from_stock_move(force_new_line=True)` con el proveedor original. Nunca reutiliza la pieza retirada ni fusiona la nueva solicitud de compra con otras necesidades o pedidos. La entrada habitual del módulo conserva su comportamiento de agrupación. El vínculo `wex_replacement_return_id` impide la fusión nativa accidental de la nueva pieza. El proceso completo vive en un savepoint y el asistente bloqueado conserva el resultado para evitar duplicados.
- `wex.return.resolution` es un historial auxiliar por cantidad, decisión, explicación y autor/fecha de creación. No sustituye al inventario: recuperación mediante `stock.picking`, desecho mediante `stock.scrap`. `wex.return.resolve` permite aplicar la decisión a una parte o a todas las unidades pendientes. La anotación `hold` no mueve existencias, no resta cantidades y no impide un envío posterior.
- Una recuperación conserva lote/serie y usa solo stock libre del origen exacto. El destino interno se selecciona explícitamente, con compañía y ubicación activas, fuera de devoluciones. El material recuperado queda disponible para el flujo normal y no se reasigna al SAT original.
- El desecho se prepara en borrador y se abre para validación nativa. No reserva capacidad de devolución ni bloquea el envío mientras sea borrador. Antes de validar, incluida la entrada directa `do_scrap`, se revalidan identidad, cantidades, reservas y stock libre. No se fuerza stock negativo ni se activa reaprovisionamiento.
- `remaining_quantity` descuenta envíos netos, recuperaciones netas y desechos realizados. `resolved` identifica un cierre sin envío; `closed`, un cierre mixto; `partial`, una gestión parcial. Una devolución inversa nativa del traslado de recuperación repone su cantidad pendiente sin borrar el historial.
- La recuperación libera la capacidad de apartamiento de su línea y recepción originales. El desecho conserva esa capacidad comprometida para no tratar las unidades destruidas como disponibles. Se conservan los bloqueos nativos para piezas usadas, facturadas o entregadas; no se añaden restricciones permanentes a los productos recuperados.
- Las resoluciones y movimientos comparten el bloqueo de línea/recepción/traza con el envío. Los acumulados almacenados y `resolution_revision` provocan reintento transaccional nativo ante concurrencia. ACL de responsables y regla global por compañía protegen el historial; las operaciones nativas mantienen sus propios permisos. La lectura elevada puntual de trazas protege validaciones de Inventario y solo actualiza su contador de concurrencia, nunca escribe stock con privilegios elevados.

Verificación: `test_return_exceptions.py`, `verify_return_resolution_concurrency.py` y `verify_return_view_modifiers.mjs`. El RMA con sustitución sigue como deuda técnica y no se implementa con esta nueva solicitud de compra.

## Deuda técnica: RMA con sustitución — 01/11/2026

El alcance actual prioriza devoluciones a proveedor, frecuentes en el taller. No existe un circuito completo de RMA con sustitución: no se gestiona la espera de un reemplazo, su vínculo con la devolución enviada, la identidad/lote/serie de la pieza sustituta ni su posterior asignación al SAT que la necesita. La recepción inversa nativa de una pieza no equivale a gestionar este circuito.

Se deja expresamente pendiente porque los RMA con sustitución son poco frecuentes y no formaban parte del diseño inicial. Una futura implementación deberá reutilizar documentos y movimientos nativos de Odoo, conservar la trazabilidad entre pieza enviada y sustituta, y evitar crear una compra ordinaria o recibir existencias automáticamente por el mero hecho de registrar el RMA.

## Coherencia visual de la devolución — 18.0.1.4.3

La modal reutiliza `wex_pl_form_title`, `wex_pl_form_kicker`, `wex_pl_form_panel` y `wex_pl_panel_title` del CSS de Lista de la compra. Comparte la tipografía de Lista y Reservas; las reglas de panel se amplían de forma explícita al formulario de devolución. `return_prepare.css` conserva solo ajustes de distribución, cantidad destacada y adaptación al ancho de la modal. No se aplica el contenedor de tabla ni los colores de estados de reservas a una devolución.

## Ventana de preparación de devolución — 18.0.1.4.1

La vista nativa destaca producto y proveedor, muestra los bloqueos antes de los campos operativos y agrupa cantidad/unidad, recepción y ubicaciones. La asignación usa todo el ancho y presenta el efecto de la retirada junto a su confirmación. Compra, fecha, unidades recibidas y paquete quedan en un desplegable nativo. Los selectores de movimiento de recepción y pieza SAT aparecen cuando existen varias opciones. El CSS queda limitado a esta ventana, sin añadir JavaScript ni alterar las reglas de devolución.

`_compute_origin_information()` prepara el resumen de cantidades con formato local y distingue SAT de venta para sus botones. El botón principal se denomina `Apartar para devolución`, reflejando el traslado interno que ejecuta.

## Cierre del desarrollo: Fase 4

La versión `18.0.1.4.0` cierra el circuito de devoluciones y su revisión. La guía operativa es `VALIDATION.md`.
La verificación incluye instalación limpia, actualización conservando ubicación e historial, suite del módulo y concurrencia con conexiones independientes.

El SAT se guarda como referencia histórica en la devolución, con integridad de compañía y restricción de borrado. La venta se obtiene del documento de origen, incluso cuando la primera pieza de un SAT con varias piezas ya se ha retirado. Una línea con trazabilidad no permite reasignar su SAT, venta o pieza de origen; las retiradas nativas siguen pudiendo limpiar sus relaciones al eliminar una línea o pieza.
El cambio de campo SAT relacionado a referencia histórica mantiene los valores almacenados en las versiones anteriores al actualizar.

Los avisos de llegada de `stock.picking.button_validate()` solo se calculan tras recepciones de proveedor realmente realizadas. La validación de un envío al proveedor no debe disparar avisos de recepción sobre otras líneas de la misma compra.

## Devoluciones a proveedor: Fase 1

La versión `18.0.1.1.0` introduce la configuración y la base de trazabilidad.
Esta primera fase no iniciaba traslados ni devoluciones. El apartado siguiente describe la Fase 2.

- `res.company.wex_return_location_id` selecciona la ubicación interna de cada compañía.
- La instalación y cada actualización inicializan solo las compañías sin selección. Las compañías nuevas reciben su ubicación al crearse.
- La ubicación predeterminada se crea bajo la raíz nativa de ubicaciones físicas, fuera del stock de cualquier almacén.
- La selección debe ser interna, activa, no ser de desecho y pertenecer a la compañía. No puede estar bajo el stock de un almacén ni bajo el origen de suministro de un tipo de operación SAT.
- La configuración está en Ajustes de Compras y dispone de un acceso `Lista de compra > Configuración` para administradores de ajustes.
- El aislamiento de la ubicación predeterminada excluye sus existencias de reservas realizadas desde el stock habitual. No modifica cantidades globales, rutas ni reglas de Odoo. Las siguientes fases deberán volver a comprobar la configuración y disponibilidad antes de cada operación, especialmente con rutas o ubicaciones personalizadas.

`wex.purchase.return` es un registro auxiliar de trazabilidad, no sustituye a `stock.picking` ni a `stock.move`.
Enlaza la línea interna, compra, recepción validada, SAT/venta de origen, cantidad en unidad base, referencia RMA y las futuras operaciones nativas.
La recepción debe pertenecer al mismo producto y línea de compra. La cantidad debe ser positiva y no superar esa recepción.
La línea interna no puede modificarse de forma que contradiga una trazabilidad ya registrada. La comprobación usa elevación únicamente para validar integridad, sin exponer registros al editor.
Los vínculos opcionales de traslado/devolución deben corresponder al producto y recepción originales.
Las cantidades comprometidas agregadas, reservas y concurrencia se resuelven desde la Fase 2.

Una regla global limita estos registros a las compañías seleccionadas, incluidos los managers. Los usuarios del módulo tienen lectura; los managers pueden crear y editar, sin permiso de borrado. Tampoco se permite duplicar estos registros.

La integración declara `purchase_stock` como dependencia nativa real para disponer de la relación entre compra y movimiento de recepción.

Una modificación de Python que añade modelos/campos requiere actualizar el módulo en cada base que lo tenga instalado. El reinicio del servicio por sí solo no migra el esquema.

## Devoluciones a proveedor: Fase 2

La versión `18.0.1.2.0` permite apartar unidades desde la vista operativa, la ficha/lista nativa de compra interna y las piezas del SAT. El tablero de envíos y la devolución al proveedor quedan para la Fase 3.

- `wex.return.prepare` selecciona una recepción nativa validada, su movimiento, cantidad en unidad base, ubicación física exacta y, cuando corresponda, lote/serie y paquete. Muestra el documento de origen y requiere confirmación para retirarlo o reducirlo.
- Las recepciones parciales son válidas por sus cantidades efectivamente recibidas; no se confía en el estado visual de la línea interna.
- `return_staging.py` centraliza la validación de capacidad, origen y ubicaciones. No se cambia el pedido de compra ni su recepción original.
- Las unidades ya devueltas por operaciones nativas y las solicitudes de trazabilidad activas se descuentan de la capacidad de la recepción. También se limita la cantidad por línea interna.
- La cantidad se reserva con las APIs nativas de inventario sobre ubicación/lote/paquete exactos, sin tomar stock de terceros ni liberar otras operaciones. El lote debe proceder de la recepción elegida y las series se apartan de una en una.
- Se utiliza el tipo interno nativo del almacén de origen (o del almacén de la recepción si el origen no tiene almacén). Debe estar activo; si no lo está, se solicita revisar la configuración de Inventario. El módulo no activa rutas ni cambia los flujos del almacén.
- El traslado se valida por `button_validate()`. Si Odoo exige otro asistente o una comprobación adicional, toda la solicitud se revierte y se informa al operador; no se omiten validaciones nativas.

### Documentos de origen

- Cotización en borrador/enviada: se reduce la cantidad o se elimina la línea si queda a cero.
- Venta confirmada: se reduce la cantidad conservando la línea y el estado del pedido. Las reglas de stock se ejecutan desde la escritura nativa de la venta.
- SAT: se reduce o elimina el `stock.move` pendiente mediante ORM. Odoo limpia/sincroniza la línea de venta asociada.
- Se bloquean los ajustes automáticos ante facturas no canceladas (incluidas borrador), movimientos realizados, piezas marcadas como utilizadas, ventas bloqueadas y líneas que agrupan otras piezas. No se reabre ni cancela el documento completo.
- Un vínculo histórico sin demanda no obliga a alterar el documento. Siguen aplicándose las restricciones de facturación y movimientos realizados, y se exige stock libre.
- La venta de origen se conserva en `wex.purchase.return.sale_order_id` aunque se retire la línea de una cotización.
- Una reserva apartada por completo que todavía no tenía aviso deja de solicitarlo. Los avisos ya registrados se conservan y no se permite registrar un aviso nuevo sobre unidades apartadas por completo.

### Transacción y permisos

El asistente y la línea/recepción se bloquean en base de datos antes de ejecutar la solicitud. Los acumulados almacenados `wex_return_quantity` y `stock.move.wex_return_committed_qty` actualizan las filas compartidas y permiten el reintento transaccional nativo ante concurrencia. La validación de capacidad consulta las trazas reales; los acumulados no sustituyen su fuente de verdad.

Toda la operación está protegida por un savepoint: si no se puede completar el traslado, se revierten también la retirada/reducción del origen y la trazabilidad. Repetir la misma solicitud completada devuelve su traslado, sin generar otro.

Solo los managers del módulo pueden iniciar el flujo. También necesitan los permisos nativos para operar en Inventario y modificar el documento de origen. No se usa `sudo()` para ajustar SAT/ventas ni para mover stock. Se mantienen las reglas globales de compañía de la Fase 1.

El estado de la trazabilidad se deriva de las operaciones nativas: sin traslado, traslado pendiente, pendiente de envío, devolución preparada, devuelto o cancelado. Una vez vinculado el traslado no se permite cambiar cantidad, recepción, compañía, lote u origen físico.

### Verificación

Las pruebas `test_return_staging.py` recorren traslado, capacidad, lotes/series, recepción parcial, ventas y SAT, bloqueo de facturas y entregas, stock ajeno, confirmación, reversión e idempotencia. `verify_return_concurrency.py` es una prueba explícita con dos conexiones independientes y reintentos nativos. Solo admite bases desechables `codex_purchase_*` y confirma sus datos de prueba; no se importa en la suite habitual.

## Devoluciones a proveedor: Fase 3

La versión `18.0.1.3.0` incorpora `Lista de compra > Devoluciones`. La entrada usa una lista nativa con selección múltiple, agrupación inicial por proveedor, filtros de pendientes/devueltas, búsqueda por RMA y acceso al origen y a los documentos de inventario.

### Preparación y RMA

- `wex.return.dispatch` presenta la selección y el número de documentos a crear, con un recordatorio no bloqueante sobre el registro externo con el proveedor.
- Se agrupa por recepción original y ubicación real registrada por el traslado. Una selección puede producir varios documentos, incluso de varios proveedores o compañías permitidas. No se mezclan recepciones en un documento paralelo.
- `wex.return.rma` asigna una misma referencia opcional a piezas de una misma compañía y proveedor comercial. También puede editarse el RMA individualmente desde la ficha de la pieza.
- La creación utiliza `stock.return.picking` y `stock.return.picking.line`. Solo se incluyen los movimientos seleccionados, para que el asistente nativo no desreserve otras líneas de la recepción.
- Si un movimiento de recepción seleccionado tiene operaciones dependientes pendientes, se exige resolverlas en Inventario antes de preparar la devolución. No se omite el comportamiento nativo de desreserva.
- La única adaptación de ubicación del asistente es el origen físico donde ya se apartaron las piezas. Se conservan el destino proveedor, tipo de devolución y vínculo con la recepción que determine Odoo. Un destino nativo que no sea proveedor requiere corregir configuración.
- Las reservas se completan al final sobre los documentos nuevos de ese lote, por lote/serie y ubicación exactos. Un error revierte todo el lote. No se valida el envío durante esta preparación.

### Validación, parciales e historial

Cada movimiento de salida lleva `stock.move.wex_vendor_return_id`. El campo participa en los criterios nativos de fusión para no perder la identidad de piezas/RMA distintos y se conserva al dividir movimientos y crear pendientes de entrega.
Se mantiene la recepción en `origin_returned_move_id` y se añade el traslado realizado como abastecimiento físico de la zona de devoluciones. Así el pendiente puede usar la disponibilidad nativa de esa zona.

El envío se confirma desde `stock.picking` con el botón nativo Validar. No se automatizan abonos ni facturas. Al completar el movimiento salen las unidades del inventario de la empresa.

- Se controlan cantidades preparadas, devueltas y pendientes por pieza. El estado `partial` indica una entrega parcial; los documentos pendientes siguen siendo los backorders nativos.
- Si se cancela un documento sin enviar o se cancela un pendiente parcial, las unidades no enviadas pueden prepararse otra vez. El primer documento se conserva y la ficha muestra todos los movimientos/documentos posteriores.
- La devolución inversa desde el proveedor respeta el destino interno nativo de Odoo, que puede ser el stock del almacén. Para volver a enviarla debe haber existencias del lote en la zona de devoluciones; el módulo no inventa un traslado de retorno a esa zona.
- Los intercambios nativos no heredan la identidad de la pieza devuelta cuando crean su movimiento de reemplazo.
- La pestaña `Piezas en devolución` del documento nativo permite consultar RMA, SAT y cantidades relacionadas.

Antes de completar movimientos vinculados se validan compañía, producto, compra, proveedor, ascendencia de la recepción, lote/serie, propiedad, ubicación, cantidad pendiente y stock físico frente a reservas. No se permite forzar una salida negativa si las existencias han cambiado desde la preparación.

La validación de integridad usa lectura elevada solo sobre las trazas asociadas a documentos de Inventario que el operador puede modificar. Esto permite que un operario con permisos nativos valide sin concederle acceso adicional a la aplicación Wex; no se eleva la escritura ni se mueven existencias con `sudo()`.

Los bloqueos siguen el orden línea interna, recepción y traza. El asistente de preparación conserva los documentos que ha generado: repetir la misma solicitud los abre, sin crear otros. Las cantidades se obtienen de los movimientos reales y los acumulados almacenados permiten los reintentos transaccionales nativos ante concurrencia.

Las pruebas `test_return_dispatch.py` cubren agrupaciones, RMA, entrega y recepción inversa, cancelaciones, parciales, lotes/series, protección de operaciones no seleccionadas, permisos y stock insuficiente. `verify_return_concurrency.py` incluye también dos preparaciones simultáneas sobre una pieza y la repetición concurrente del mismo asistente.

## Objetivo real del módulo

`wex_purchase_list` existe para centralizar necesidades internas de compra antes de emitir RFQ, sin usar el sistema de reabastecimiento estándar de Odoo como flujo principal.

El módulo no sustituye el reabastecimiento nativo. Mantiene un flujo paralelo, más rápido y manual, inspirado en una antigua hoja de Google Sheets usada en SAT.

## Qué hace hoy

- Muestra una lista interna de compra basada en `wex_purchase_list.line`.
- Usa una vista operativa propia `wex_operational_list` como entrada principal para compras y reservas.
- Permite añadir productos a esa lista desde:
  - la ficha de producto
  - una reparación, a partir de `stock.move`
  - una cotización, a partir de `sale.order.line`
- Permite registrar:
  - quién añadió el producto
  - producto
  - proveedor
  - URL del proveedor
  - reparación asociada si nace desde SAT
  - estado interno del pedido
  - si la línea es una reserva
  - si el cliente ya fue avisado
  - precio informado al cliente
  - RFQ/PO y línea de compra generadas
- Permite agrupar visualmente reservas y seguimiento mediante `reservation_board_section`.
- Permite marcar al cliente como avisado desde lista, reservas y formulario cuando el repuesto ya está recibido.
- Permite abrir rápidamente el enlace del proveedor y WhatsApp del cliente cuando el origen lo soporta.
- Permite crear RFQ agrupadas por proveedor y compañía a partir de líneas en estado `to_purchase`.

## Qué no hace

- No intenta reemplazar el planificador/reabastecimiento nativo de Odoo.
- No reutiliza RFQ borrador existentes.
- No resuelve todavía bien todos los casos futuros de recepción parcial o flujos complejos de compra.
- No tiene hoy una arquitectura claramente separada entre:
  - lista interna de compra
  - utilidades de producto
  - cálculo de precios y margen

## Modelos y responsabilidades

### `wex_purchase_list.line`

Modelo principal del módulo.

Responsabilidades actuales:
- almacenar la necesidad interna de compra
- mantener estados internos
- calcular señales operativas de reserva, retraso y tablero
- enlazar orígenes (`repair`, `sale`, `product`)
- centralizar la creación de líneas con `add_from_origin()`
- registrar avisos al cliente y su trazabilidad mínima
- generar RFQ con `action_create_rfqs()`

Métodos relevantes:
- `add_from_origin()`
- `action_create_rfqs()`
- `action_mark_customer_notified()`
- `action_open_customer_whatsapp()`
- `action_mark_as_received()`

### Vista operativa `wex_purchase_list_operational`

Archivos:
- [purchase_list_operational_action.js](/C:/odoo18/addons-wexplay/wex_purchase_list/static/src/js/purchase_list_operational_action.js)
- [purchase_list_operational_action.xml](/C:/odoo18/addons-wexplay/wex_purchase_list/static/src/xml/purchase_list_operational_action.xml)
- [purchase_list.css](/C:/odoo18/addons-wexplay/wex_purchase_list/static/src/css/purchase_list.css)

Responsabilidades actuales:
- renderizar la lista como tablero operativo más cercano a hoja interna que a kanban estándar
- permitir selección múltiple y creación agrupada de RFQ
- conservar temporalmente la selección al abrir y volver de una ficha, sin cambiar el clic normal de edición de la fila
- permitir seleccionar todas las líneas visibles del filtro actual para la compra diaria
- ofrecer una acción individual de apertura de URL por línea, amplia y separada del clic que abre la ficha
- marcar reservas como avisadas sin salir del tablero
- soportar agrupaciones visuales por proveedor, cliente, estado o bloque de reservas

### Vista operativa de Reservas

La acción de Reservas usa una vista XML distinta que reutiliza el renderizador base con una presentación específica.

Responsabilidades:
- mostrar un HERO de ancho completo con `Con retraso`, `Esperando llegada`, `Pendientes de aviso` y `Ya avisadas`
- priorizar automáticamente el primer bloque con reservas y mostrar solo sus líneas para evitar agrupaciones verticales largas
- ofrecer WhatsApp cuando exista cliente y `Marcar avisado` solo en reservas recibidas aún no avisadas
- recargar el tablero tras marcar un aviso para que la reserva se desplace a `Ya avisadas`
- no ofrecer selección múltiple ni creación de RFQ: Reservas se centra en seguimiento y aviso individual

### Extensiones de `repair.order` y `stock.move`

Archivo: [repair_order.py](/C:/odoo18/addons-wexplay/wex_purchase_list/models/repair_order.py)

Responsabilidades actuales:
- smart button de líneas de compra desde la reparación
- acción para añadir una pieza (`stock.move`) a la lista
- trazabilidad con `purchase_list_line_id` en `stock.move`

### Extensiones de `sale.order` y `sale.order.line`

Archivo: [sale_order.py](/C:/odoo18/addons-wexplay/wex_purchase_list/models/sale_order.py)

Responsabilidades actuales:
- smart button de líneas de compra desde la venta
- acción para añadir una línea de venta a la lista
- trazabilidad con `purchase_list_line_id` en `sale.order.line`
- política `Marcar como reserva` por cotización comercial, activa por defecto
- sincronización de esa política con líneas de compra aún no avisadas

Reglas:
- las ventas independientes añaden sus productos como reserva por defecto
- las cotizaciones SAT no exponen ni pueden modificar esta política; sus piezas usan `stock.move.wex_is_reservation`
- la política solo se puede cambiar en estado borrador o enviada
- el cambio puede retirar avisos futuros de líneas activas, pero no altera un aviso ya registrado

### Extensión de `product.template` en `product.py`

Archivo: [product.py](/C:/odoo18/addons-wexplay/wex_purchase_list/models/product.py)

Responsabilidades actuales:
- campo `wex_vendor_url`
- acción rápida para añadir una unidad a la lista desde la ficha del producto

### Extensión de `product.template` en `product_template.py`

Archivo: [product_template.py](/C:/odoo18/addons-wexplay/wex_purchase_list/models/product_template.py)

Responsabilidades actuales:
- cálculo auxiliar de PVP con IVA
- cálculo auxiliar de margen
- sugerencia de precio

Nota:
- esta parte está resuelta en Python mediante `compute`, `inverse`, `onchange` y acción explícita para aplicar sugerencia
- el redondeo comercial se realiza siempre hacia arriba al siguiente múltiplo de 5
- no forma parte del núcleo estable de la lista de compra y no debería condicionar el resto del diseño del addon

### Extensión de `stock.picking`

Archivo: [stock_picking.py](/C:/odoo18/addons-wexplay/wex_purchase_list/models/stock_picking.py)

Responsabilidad actual:
- al validar una recepción ligada a compra, marcar líneas de la lista como `received` cuando detecta que la línea de compra está totalmente recibida

## Estados actuales de `wex_purchase_list.line`

La documentación debe reflejar el comportamiento real actual:

- `draft_wait_customer`
  - se ha dado precio al cliente, pero aún no hay confirmación
- `to_purchase`
  - ya debe comprarse
- `ordered`
  - comportamiento actual del código: la línea pasa a `ordered` al crear la RFQ desde la lista
  - esto no coincide con la intención futura de negocio, pero hoy es el comportamiento real
- `received`
  - se intenta marcar desde la validación de recepción de compra
- `cancelled`
  - cancelación manual o cancelación del flujo que dio origen a la necesidad

## Reglas actuales por origen

### Origen `sale.order.line`

- si la línea de venta ya tiene `purchase_list_line_id`, no se puede volver a añadir
- no hace merge con otra línea existente

### Origen `stock.move`

- si el `stock.move` ya tiene `purchase_list_line_id` activa, no se puede volver a añadir
- si existe una línea activa con misma `repair_id` + mismo `product_id`, suma cantidad

### Origen `product.template`

- requiere una única variante
- crea siempre una línea nueva
- no hace merge actualmente

## Seguridad y visibilidad esperada por negocio

Negocio ha definido este comportamiento esperado:

- la lista debe separarse por compañía
- los administradores pueden ver entre compañías
- los usuarios normales deben poder editar líneas ajenas, al menos por ahora
- solo managers deben generar RFQ

Nota:
- el estado real de seguridad actual no está todavía alineado del todo con esta definición y debe revisarse en una fase posterior

## Deuda viva más importante

- `action_create_rfqs()` marca `ordered` al crear la RFQ, no al confirmar la compra
- la parte de pricing/margen en producto está en el módulo por conveniencia, aunque ya no depende de JS ni de recargas de página
- hay solape de responsabilidades entre compra interna SAT y utilidades de pricing
- el bloque de pricing sigue viviendo en este módulo aunque no pertenece al flujo principal de compra interna
- hay que revisar seguridad sobre `stock.move`
- hay que revisar reglas multi-company para alinearlas con el comportamiento esperado
- la vista operativa ya es pieza central del módulo y conviene documentar mejor sus filtros, agrupaciones y límites para evitar que la UX evolucione sin trazabilidad
