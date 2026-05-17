# Wexplay Despieces

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
14. Se crean o actualizan productos linea a linea.
15. Se crea stock real mediante movimientos estandar.

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

El modulo crea stock real al finalizar/procesar lineas validas.

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

## Creacion y actualizacion de productos

La creacion usa `product.template.create()` estandar. `wex_product_codes` genera
la referencia interna si la categoria tiene regla.

Para productos existentes se actualizan:

- precio
- condicion Wexplay
- etiquetas
- datos faltantes
- stock mediante movimiento estandar

## Etiquetas

V1 solo conserva campos de trazabilidad:

- `label_printed`
- `label_printed_at`

La impresion queda pendiente. Antes de implementarla se debe revisar
`wexplay_product_print`, `wexplay_sat_print` y `wex_print_core` para reutilizar
APIs existentes y evitar duplicar logica.

## Imagenes

No se implementan en V1.

Cuando se retomen, deben definirse almacenamiento real, impacto en DMS/adjuntos y
estrategia de acceso antes de escribir codigo.

## Etiqueta de lote

Queda documentada para futuro una etiqueta fisica del lote `DESP-XXXX` para
trazabilidad y trabajo compartido. No se implementa impresion de lote en V1.

## Seguridad

Grupos:

- Usuario Despieces
- Responsable Despieces

Las reglas operativas filtran batches y lineas por companias permitidas.
