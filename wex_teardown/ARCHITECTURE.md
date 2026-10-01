# Wexplay Despieces

Actualizado: 2026-09-13. Versión 18.0.2.0.0; impresión excluida de esta iteración.

## Objetivo

`wex_teardown` gestiona procesos internos de despiece de dispositivos fisicos y
convierte piezas validas en productos de Odoo con stock real.

El modulo es un paso operativo previo a producto/stock. No modifica el core de
Odoo, no altera ventas y no manipula `stock.quant` directamente.

## Dependencias

- `base`
- `product`
- `stock`
- `mail`
- `web`
- `website_sale`: galería nativa de producto, sin almacenamiento propio de imágenes.
- `wexplay_repair`
- `wex_product_codes`

No depende directamente de `wexplay_product_print` ni de `wex_print_core`.

## Decision de configuracion principal

En V1, el componente es la fuente de verdad para:

- tipo de dispositivo
- categoria final del producto
- patron de nombre del producto

No existen reglas separadas de categoria ni reglas separadas de nombre en el
flujo funcional V1. Esto evita configurar la misma decision en varios sitios.

Los modelos tecnicos antiguos `wex.teardown.category.rule` y
`wex.teardown.name.rule` pueden existir de forma obsoleta para permitir una
actualizacion limpia en bases donde ya se hubiera instalado una primera version.
No deben usarse en V1 y sus menus quedan ocultos.

## Modelo mental

El flujo se organiza asi:

`Componente` -> `Plantilla` -> `Despiece real` -> `Producto + stock`

- Componente: define que pieza es, para que tipo de dispositivo sirve, a que
  categoria ira el producto y como se nombrara.
- Plantilla: lista reutilizable de componentes esperados para un tipo de
  dispositivo.
- Despiece: ejecucion real sobre un dispositivo fisico concreto.
- Producto: resultado creado o actualizado tras validacion.
- Stock: entrada real al almacen configurado.

## Modelos

- `wex.teardown.batch`: cabecera del proceso real de despiece.
- `wex.teardown.line`: pieza concreta revisada dentro de un despiece.
- `wex.teardown.template`: plantilla reutilizable por tipo de dispositivo.
- `wex.teardown.template.line`: componente esperado dentro de una plantilla.
- `wex.teardown.component.type`: componente de despiece.

Aunque el modelo tecnico conserva el nombre `component.type`, en la interfaz se
muestra como `Componentes`.

## Componente

Campos funcionales:

- `device_type`
- `name`
- `code`
- `product_category_id`
- `name_pattern`
- `sequence`
- `active`

`code` se autogenera desde `device_type + name`. No es la referencia interna del
producto. La referencia interna del producto sigue siendo responsabilidad de
`wex_product_codes`.

`name_pattern` usa estas variables:

- `{component}`
- `{part_number}`
- `{device_type}`
- `{brand}`
- `{model}`

Patron por defecto:

`{component} {part_number} para {device_type} {brand} {model}`

## Plantillas

La plantilla es reutilizable por tipo de dispositivo.

Campos funcionales:

- `name`
- `device_type`
- `line_ids`
- `active`

La plantilla no se ata tecnicamente a un modelo concreto en V1. Si se necesita
una plantilla especifica, se expresa en el nombre, por ejemplo:

- `Plantilla smartphone moderno`
- `Plantilla Samsung S26 Ultra`
- `Plantilla Nintendo Switch OLED`

Las lineas de plantilla solo permiten seleccionar componentes del mismo
`device_type`.

## Datos SAT reutilizados

El despiece real reutiliza:

- `wex.repair.brand`
- `wex.repair.device_model`
- `DEVICE_TYPE_SELECTION`

No crea marcas, modelos ni tipos de dispositivo paralelos.

## Flujo funcional

1. Se configuran componentes por tipo de dispositivo.
2. Cada componente define su categoria y patron de nombre.
3. Se crea una plantilla por tipo de dispositivo.
4. La plantilla contiene componentes filtrados por ese tipo.
5. Se crea un despiece real.
6. Se selecciona tipo, modelo y plantilla.
7. La plantilla genera lineas de piezas.
8. Cada linea hereda categoria y patron desde su componente.
9. El usuario revisa cantidades, part number, precio y control de calidad.
10. Las piezas no aptas o no recuperadas salen del flujo normal, pero quedan trazadas.
11. Se comprueban duplicados sobre piezas aptas o pendientes.
12. El usuario decide usar existente, usar existente actualizando nombre o
    continuar mas adelante con creacion/descartes en la fase de coincidencias.
13. Se valida el despiece.
14. `Preparar productos` crea fichas nuevas archivadas o vincula productos existentes, sin stock.
15. En `Productos pendientes`, se abre la ficha definitiva para completar imagen principal y galería.
16. `Finalizar pieza` activa la ficha nueva y genera el movimiento de stock en una operación atómica.
17. Los existentes conservan su activación; sus cambios propuestos se aplican al finalizar su línea.

## Estado real y foco interno

El modulo separa dos conceptos:

- `state`: estado real del lote (`draft`, `template_loaded`, `review`,
  `validated`, etc.)
- `workflow_focus`: foco interno de trabajo en la interfaz

`workflow_focus` no cambia la semantica del despiece ni sustituye al workflow
real. Solo indica en que notebook debe aterrizar el usuario al volver a abrir el
registro:

- `device`
- `pieces`
- `data_completion`

Reglas actuales:

- al cargar plantilla, el lote pasa a `template_loaded` y el foco cambia a
  `pieces`
- al buscar coincidencias, el lote pasa a `review` y el foco sigue en `pieces`
- al pulsar `Pasar a completar datos`, primero se comprueba que `Piezas` ya ha
  quedado cerrada a nivel operativo
- en ese paso, toda pieza apta que siga con decision `pending` pasa
  automaticamente a `create_new`
- despues el lote queda en `review` y el foco cambia a `data_completion`

## Categorias

La categoria se decide solo en el componente:

`component.product_category_id`

La linea de despiece muestra esa categoria como informacion heredada. No se
edita en la linea, en la plantilla ni en reglas separadas.

Sin categoria en el componente, la validacion bloquea la creacion del producto.

## Nombres

El nombre sugerido de la linea se renderiza desde:

`component.name_pattern`

El usuario puede bloquear y editar manualmente `name_final` en la linea cuando
sea necesario.

## Precio e impuestos

`list_price` es el precio principal y guardado. Es el valor que se escribe en el
producto porque Odoo trabaja con precio de venta sin IVA.

`pvp_tax_included` es auxiliar y se calcula desde `list_price` usando los
impuestos nativos de Odoo. Si se edita desde el formulario, recalcula
`list_price`; no introduce una configuracion fiscal paralela.

La linea conserva `tax_ids` para preparar el producto, pero no existe un campo de
IVA propio de despieces en compania. Si la linea no trae impuestos, se intentan
usar los impuestos por defecto que Odoo asignaria a `product.template`.

## Control de calidad

La pestana `Piezas` representa la revision fisica, no la decision final de
producto.

Valores funcionales:

- `pending`: pendiente
- `ok`: apta
- `fail`: no apta
- `not_applicable`: no recuperada / no aplica

Si una linea se marca como `fail` o `not_applicable`, se marca como descartada y
aparece en la tabla `No aptas / control de calidad fallido`. No se borra, porque
la trazabilidad del despiece es importante.

La UX principal de `Piezas` se simplifica asi:

- boton rapido verde: marcar `Apta`
- boton rapido rojo: abrir modal de rechazo obligatorio

El modal de rechazo pide motivo y notas. El usuario no necesita decidir desde la
tabla si el rechazo tecnico interno es `fail` o `not_applicable` salvo cuando
sea relevante; la intencion operativa es simplemente sacar la pieza del flujo
productivo con trazabilidad clara.

La tabla principal de `Piezas pendientes / aptas` deja de apoyarse en un
`one2many` editable estandar y pasa a una vista operativa OWL propia, con fila
compacta y bloque desplegable de edicion. Esto permite trabajar tipo
"registro expandible": ver muchas piezas a la vez, marcar apta/rechazada con un
gesto y editar solo el bloque concreto que hace falta sin abrir la ficha
completa ni saturar la tabla con columnas secundarias.

En este bloque expandido de `Piezas` se prioriza:

- `part_number`
- `quantity`
- nombre sugerido editable
- resolucion operativa de coincidencias sobre productos ya existentes

Y se dejan fuera, por ahora:

- precio
- notas largas de control de calidad

El objetivo es que `Piezas` responda primero a "que pieza es" y "con que
producto existente se relaciona", dejando otras decisiones mas tardias para
fases posteriores del flujo.

Dentro del bloque expandido de `Piezas` no se expone boton directo de
`crear nuevo`. Esta fase se limita a resolver reutilizacion de producto
existente:

- usar el producto tal como esta
- usar el producto y actualizar su nombre con el generado desde despiece
- abrir la ficha del producto coincidente

La opcion de "usar y actualizar nombre" existe para sanear catalogo heredado
sin romper stock ni referencias ya vivas. El saneo se hace solo cuando un
despiece real confirma que interesa conservar el producto existente pero alinear
su nombre con el patron actual del modulo.

La decision `use_existing` tambien queda cerrada ya en `Piezas` cuando el
usuario elige un producto coincidente. Si no se elige un existente y la pieza
queda apta para continuar, al pasar a `Completar datos` la decision se
normaliza automaticamente a `create_new`.

Excepcion importante: si la coincidencia detectada es `exact`, el flujo no debe
permitir avanzar como `create_new`. En ese caso el usuario debe reutilizar el
producto existente para no inducir duplicidad sintetica e innecesaria de
catalogo.

`discard` deja de ser una decision funcional de la fase final. Se resuelve en
`Piezas` como consecuencia del control de calidad y mueve la linea a la tabla de
no aptas / no recuperadas.

## Completar datos

La antigua pestana `Validacion` se reorienta como `Completar datos`. Ya no es
una segunda tabla genérica de piezas ni una superficie para repetir decisiones
de QC o coincidencias.

Su objetivo ahora es terminar de cubrir datos economicos de las piezas aptas:

- `Precio sin IVA`
- `PVP IVA incluido` como referencia calculada
- `Coste`
- `Impuestos`

No debe seguir arrastrando decisiones pendientes de control de calidad ni de
coincidencias. Cuando el usuario llega aqui, la fase operativa anterior ya debe
estar cerrada y solo debe quedar trabajo economico.

Las lineas sin `part_number` no se consideran advertencia tardia si el usuario
ya las ha confirmado como piezas que seguiran sin `part_number`. Para reducir
friccion, la plantilla puede marcar este checkbox por defecto al cargar el
despiece.

La tabla de `Completar datos` reutiliza el patron de fila expandible de
`Piezas`, pero solo para lineas aptas (`qc_state = ok`). La vista debe ser
deliberadamente sobria: resumen minimo arriba y edicion economica inline al
desplegar.

## Stock

El módulo crea stock real exclusivamente al finalizar piezas preparadas con imagen principal.
Preparar productos y guardar fotos no genera stock. Se exige producto almacenable con una sola
variante y sin seguimiento por lote/serie en esta fase; el resto se bloquea antes de activar.
Los movimientos se confirman sin fusionar, se marca `picked` y se verifica que terminen en `done`.

El flujo es:

`Despieces / Origen` -> `wex_teardown_default_location_id`

`Despieces / Origen` es una ubicacion virtual de uso `production`. El destino es
una ubicacion interna configurada en la compania.

No se escriben quants directamente.

## Duplicados

El sistema detecta coincidencias, pero nunca decide automaticamente.

La accion visible para el usuario es `Buscar coincidencias`. En esta version
hace una busqueda interna dentro de Odoo, refinada con `RapidFuzz` para los
casos dudosos (`partial` y `model`), y colorea las piezas segun el nivel de
coincidencia:

- `exact`: verde
- `partial`: amarillo
- `model`: azul
- `none`: sin resalte

La busqueda actual se limita a productos reacondicionados (`wex_condition =
refurbished`) para no mezclar repuestos de despiece con catalogo de producto
nuevo.

El flujo de UI no bloquea el formulario completo. La comprobacion se ejecuta en
tandas pequenas desde frontend hacia backend. Cada tanda procesa un bloque de
lineas, actualiza progreso y deja el control de la interfaz al usuario entre
peticiones. Al finalizar, la vista muestra notificacion emergente y se recarga
para reflejar colores y mensajes definitivos.

`RapidFuzz` se distribuye dentro del propio modulo en `wex_teardown/vendor`
para evitar dependencias frágiles del entorno Windows del servicio Odoo. Esta
decision reduce sorpresas entre instalaciones locales, servicios `LocalSystem`
y entornos donde no se controla facilmente el `site-packages` del proceso.

La huella estructurada que se guarda en producto es:

- `wex_teardown_component_id`
- `wex_teardown_part_number`
- `wex_teardown_model_id`

Y desde `wex_teardown_model_id` se leen marca y tipo de dispositivo por campos
related, reutilizando los maestros SAT existentes.

Estados:

- `none`
- `exact`
- `partial`
- `model`

Decisiones:

- `use_existing`
- `create_new`
- `discard`

## Matching local refinado

La estrategia actual se divide en dos capas:

1. Busqueda local simple y segura:
   - coincidencia exacta por huella estructurada
   - coincidencia exacta por nombre final
   - clasificacion inicial `exact` / `partial` / `model` / `none`
2. Afinado textual con `RapidFuzz` solo para casos no definitivos:
   - los casos `exact` y `none` no se vuelven a calcular
   - los casos `partial` y `model` se reordenan y filtran con similitud textual
     sobre nombre, modelo y componente
   - si el score refinado es demasiado debil, la linea vuelve a `none`
   - `model` no significa ya "mismo modelo sin mas"; exige una segunda senal
     minima (categoria o componente) para evitar falsos positivos azules
   - la parte del nombre antes de `para` tiene mas peso que la cola de
     compatibilidad del modelo; la identidad de la pieza manda sobre la
     compatibilidad compartida del dispositivo

Esta decision busca una V1 sobria: mantener reglas backend claras, sin
microservicio todavia, pero con un afinador mejor que la heuristica manual.

## Evolucion prevista del matcher

La arquitectura se deja preparada para crecer en dos niveles:

1. Busqueda interna rapida en Odoo.
2. Busqueda interna refinada con `RapidFuzz`.
3. Busqueda avanzada asincrona y externa para casos dudosos o sin resultado.

El servicio externo no se implementa en esta version. Queda documentado para una
iteracion futura si el volumen de catalogo o la complejidad de comparacion lo
justifican. La idea prevista es escalar solo cuando el matcher local no sea
suficiente, no sustituirlo por defecto.

## Preparación de productos y finalización

`wex_teardown_line_lifecycle.py` concentra preparación, revisión de propuestas, finalización,
rectificación y bloqueos. `wex_teardown_batch_lifecycle.py` concentra identidad y orquestación del lote.
Los modelos originales conservan QC, nombres, matching, cálculo y preparación de valores.

Los nuevos productos se crean con `product.template.create()`, `active=False`, sin publicación web
y con compañía del lote. La categoría inicial procede del componente; `wex_product_codes` genera
la referencia, también en productos archivados. `product_tmpl_id` significa producto preparado,
no stock ingresado. Se conserva el estado histórico de línea `created` para las finalizadas;
el nuevo estado `product_prepared` indica preparación sin movimiento.

El lote pasa a `products_prepared`, `partial_created` cuando hay finalizaciones parciales y `done`
cuando terminan todas las piezas recuperables. `workflow_focus=products` abre los pendientes.
Las líneas preparadas dejan de aparecer en los widgets operativos de Piezas/Completar datos.

El producto guarda `wex_teardown_origin_line_id` y un único estado de preparación de catálogo:
`pending`, `ready`, `cancelled`. Es necesario distinguir catálogo preparado de cada entrada física:
varias líneas pueden reutilizar una misma ficha y generar cantidades independientes.

La imagen y los datos del producto nuevo se editan en su ficha; los valores antiguos de la línea
no los sobrescriben al finalizar. Para existentes se guarda una instantánea de nombre, precios,
impuestos y huella al preparar. Si cambian, `Revisar propuesta` carga los valores actuales y retira
la propuesta de renombrado. Después se pueden ajustar los importes antes de finalizar.

La finalización exige imagen principal, validaciones de compañía y ubicación, producto válido y
pieza apta. Activación, modificación del existente y movimiento ocurren en un savepoint por pieza.
Si falla, se revierte esa pieza y se registra el error fuera del savepoint. Las carreras de PostgreSQL
se propagan para que Odoo reintente la transacción completa. Una finalización repetida ya completada
no genera otro movimiento. `Finalizar piezas listas` conserva las no finalizables con su motivo visible.

La activación/publicación manual de fichas pendientes o canceladas está bloqueada en Python,
incluyendo activación de variantes. Las escrituras internas usan una identidad Python privada que
no puede fabricarse mediante un diccionario de contexto RPC. No se utiliza `sudo()` para el flujo.
Activar mediante despiece no publica el producto en tienda.

## Identidad física, catálogo y concurrencia

Antes de cargar la plantilla se exige IMEI/serie o confirmación de que dispositivo/bandeja está
identificado físicamente con la referencia. El IMEI acepta 15 dígitos, eliminando espacios. La serie
conserva puntuación, elimina espacios exteriores y normaliza mayúsculas. La clave de serie incluye
la marca; ambas identidades están acotadas por compañía y protegidas por unicidad en PostgreSQL.
Sin identificador real, la confirmación física no garantiza deduplicación automática.

La búsqueda de catálogo incluye archivados y muestra si están activos, pendientes o retirados.
Solo activos y pendientes pueden reutilizarse normalmente. Un responsable puede recuperar una
preparación cancelada mediante selección explícita y preparación desde otra pieza validada, si el
producto no tiene movimientos finalizados. Un archivado ordinario no se reactiva por este flujo.

Se busca coincidencia exacta nuevamente antes de crear. Las preparaciones se serializan mediante
un UPDATE sin cambio de valor sobre la fila de la secuencia de despieces; no consume números.
Esto permite que PostgreSQL detecte conflictos de snapshot en el aislamiento REPEATABLE READ de
Odoo. Las finalizaciones bloquean lote, pieza y producto; cada línea conserva su movimiento propio.
Los bloqueos son transaccionales y se liberan al confirmar o revertir la petición.

## Cancelación, rectificación e históricos

Un lote sin movimientos puede cancelarse: conserva fichas y fotos archivadas y libera su identidad.
Si otro lote está preparando el mismo producto, se reasigna el origen a esa línea en vez de cancelar
la preparación compartida. Un lote con movimientos no se cancela ni vuelve genéricamente a revisión.

Un responsable puede rectificar una preparación sin stock. Si creó una ficha no compartida, esta
queda cancelada y archivada, conservando el vínculo de origen; puede recuperarse expresamente como
existente. No se eliminan productos o fotos automáticamente. Las relaciones y las validaciones de
borrado preservan la trazabilidad de productos preparados y movimientos.

No hay migración destructiva. Las líneas históricas `created` conservan sus movimientos; no se exige
foto retroactivamente ni se genera stock de nuevo. Si un histórico tiene ficha o movimiento pero un
estado ambiguo, no se reconcilia automáticamente: requiere revisión operativa. El responsable debe
revisar especialmente los movimientos históricos que no estén en `done`.

## Etiquetas

Las etiquetas de Zebra se implementan reutilizando `wex_print_core`. El lote tiene su propia etiqueta física y la etiqueta de producto permanece en `wexplay_product_print`; los campos históricos de trazabilidad no son una confirmación de impresión física.

## Imágenes

Se utiliza `image_1920` como principal y `product_template_image_ids` / `product.image` para la
galería de `website_sale`. Las fotos se suben directamente al producto archivado, sin copia temporal
en Despieces, sin DMS ni manipulación de rutas de filestore. La miniatura en pendientes es related,
no se almacena otra imagen. Una foto adicional no sustituye al requisito de imagen principal.

Las fotos son compartidas por el catálogo, no evidencia individual de cada unidad. La imagen ya
existente satisface el requisito; no se reemplaza automáticamente al reutilizar un producto.

## Etiqueta de lote

La etiqueta física del lote `DESP-XXXX` está implementada con Zebra a 76 x 25 mm. Se imprime desde la cabecera del despiece mediante una acción QZ configurada.

## Seguridad

Grupos:

- Usuario Despieces
- Responsable Despieces

Las reglas operativas filtran batches y lineas por companias permitidas.

El grupo Usuario Despieces implica Usuario de Inventario para trabajar con stock nativo. Se concede
crear/editar producto y variante, gestionar medios nativos y leer reglas de referencia (sin editarlas).
La galería comprueba acceso de escritura al producto propietario y compañías; los lotes/líneas
mantienen sus reglas. El archivado es una condición operativa, no una barrera de seguridad para
cualquier integración externa que busque también registros inactivos.

## Verificación de esta iteración

Instalación/actualización y pruebas sobre `codex_teardown_test_20260913`, una base local aislada.
La base operativa no se ha actualizado. Suite ORM: `tests/test_teardown_lifecycle.py`.
Las vistas efectivas y la presencia de la galería se comprueban también con usuario normal.
`tests/concurrency_check.py` prueba carreras con conexiones independientes y commits reales;
solo permite ejecutarse en bases cuyo nombre empieza por `codex_teardown_test_`.

La dependencia `wexplay_repair` necesitó corregir la firma de su hook de instalación a `post_init_hook(env)`
para Odoo 18. No se modificó su lógica funcional. La impresión no se ha implementado ni alterado.

## Etiquetas Zebra de despiece

El despiece dispone de `teardown_batch_label_zebra`, una etiqueta de lote de 76 x 25 mm. Se imprime desde el encabezado del lote y contiene la referencia `DESP-…`, tipo/modelo y un Code128 de la referencia; no muestra IMEI ni serie.

La etiqueta de producto vive en `wexplay_product_print` como `product_label_zebra`. Incluye nombre, PVP IVA incluido y la referencia interna generada por Odoo como identificador y payload del Code128. No utiliza el ID técnico de Odoo ni un contador paralelo.

Ambas rutas requieren una asignación Zebra mediante la resolución nueva de Wex Print. No caen al dispositivo Brother configurado en legacy. La etiqueta de lote no cambia estados ni marca una impresión como físicamente realizada: QZ solo confirma que el trabajo se envió.
