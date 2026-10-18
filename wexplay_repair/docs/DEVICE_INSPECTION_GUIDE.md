# Estado del dispositivo: guía funcional y técnica consolidada

Fecha: 17/10/2026. Estado: implementación completada y funcionamiento confirmado
por el usuario, incluida la integración del portal. Esta confirmación no identifica
el entorno concreto de despliegue ni sustituye los resultados técnicos registrados.
Esta guía recoge el comportamiento vigente; los planes y changelogs conservan la
secuencia de iteraciones y decisiones anteriores.

## Módulos y responsabilidades

| Módulo | Versión | Responsabilidad |
|---|---|---|
| wexplay_repair | 18.0.1.5.1 | Datos de inspección, validación, esquemas compartidos e informe técnico SAT. |
| wex_consent | 18.0.1.1.0 | Instantánea de recepción, kiosko, protección del contenido y PDF firmado en DMS. |
| wexplay_portal | 18.0.1.1.0 | Consulta B2B autorizada del estado de recepción y selección de su procedencia. |

No se han añadido reglas de workflow o entrega a la base SAT. La declaración del
campo existente x_device_description se trasladó de wex_consent a wexplay_repair
sin cambiar su nombre ni la columna SQL. Al desplegar toda la serie se actualizan
los tres módulos; no se desinstalan para trasladar el campo.

## Inspección en la ficha de reparación

La descripción está debajo de Accesorios entregados y ocupa su mismo ancho.
El botón de apertura, solo con icono, está alineado a la derecha del título y mide
42 × 42px. Incluye ayuda y nombre accesible. El punto verde indica trazos en alguna
de las caras; texto, etiquetas o selección de formato sin dibujos no lo activan.

La modal usa el selector visual y los estilos SAT de la ficha. Exige elegir tipo
antes de mostrar el contenido o editar la descripción. La validación Python exige
tipo cuando existe descripción, etiquetas o inspección, sin convertirlo en un
bloqueo de operaciones ajenas sobre reparaciones históricas sin tipo.

En la modal se trabaja con una cara por vez. Frontal/Trasera conservan sus trazos
independientes e indican si contienen marcas; en portátiles se llaman Pantalla y
teclado / Parte inferior. El lápiz permite dibujar a mano alzada con el ratón.
Deshacer y Borrar esta cara afectan solo a la cara activa. Los desperfectos son
selecciones de catálogo y se muestran también como etiquetas bajo la descripción;
no se convierten en texto ni se deducen automáticamente de los dibujos.

Aplicar lleva el conjunto al borrador de la reparación; Guardar nativo lo persiste.
Cancelar o cerrar la modal descarta todos sus cambios, incluidos los cambios de
tipo/formato confirmados dentro de ella. Descartar nativo revierte el borrador.

### Cambios de tipo y formato

| Acción | Confirmación | Se borra | Se conserva |
|---|---|---|---|
| Cambiar tipo de dispositivo | Si hay marcas o etiquetas, desde ficha o modal. | Ambas caras y etiquetas. | Descripción. |
| Cambiar formato de consola | Solo si hay marcas en alguna cara. | Ambas caras. | Etiquetas y descripción. |
| Cambiar de cara | No. | Nada. | Ambas caras, etiquetas y texto. |

Cancelar una confirmación mantiene la selección y el progreso. Los cambios de tipo
cargan el esquema nuevo inmediatamente y vuelven a la primera cara.

### Tipos y consolas

Existen esquemas para móvil, tablet, portátil, Todo en Uno, Mini PC, monitor,
smartwatch y consola. Son 20 SVG en total: dos caras por cada uno de los siete
tipos no consola y seis para los tres formatos de consola. Otros tipos permiten
registrar descripción y etiquetas aplicables, pero no tienen esquema de dibujo.

La ficha mantiene el tipo Consola. Solo la inspección permite elegir Sobremesa,
Portátil clásica o PC de mano mediante tarjetas con ilustración y nombre, sin
subtítulos ni ejemplos comerciales. No hay un campo nuevo de subtipo de reparación.
No se muestra su esquema ni se permite Aplicar hasta seleccionar formato.

Sobremesa representa una consola de salón, con dibujo genérico inspirado en
Series S y sin logotipos; no un ordenador compacto. Las miniaturas del selector
se limitan a 112 × 72px; en pantallas de hasta 767px de ancho o 800px de alto, a
80 × 56px, con menos separación y relleno. El esquema de dibujo no se reduce por
ese ajuste. La revisión de la silueta no reescribió coordenadas de marcas anteriores.

## Datos y preparación documental compartida

- x_device_description: texto existente, conservando datos y consumidores previos.
- x_device_condition_ids: etiquetas del catálogo wex.repair.device.condition,
  comunes o específicas por tipo. Usuarios internos consultan; administradores mantienen.
- x_device_inspection_marks: JSON con device_type, front y back. Solo consola añade
  console_format: desktop, classic_handheld o handheld_pc. Su formato se conserva
  incluso sin trazos. No se guardan SVG/HTML aportados por el usuario.

Python valida tipo, compatibilidad de etiquetas, estructura, coordenadas finitas
normalizadas entre 0 y 1 y límites de trazos/puntos. El catálogo de esquemas vive
en Python y la modal consume sus metadatos con comprobación de lectura.

_prepare_device_inspection_snapshot y los helpers de composición están en
models/repair_order_inspection.py. Generan ambas caras si al menos una tiene
trazos, usando recursos locales y el mismo espacio 320 × 400 del editor. Informe
y firmas reutilizan esa preparación; no dependen de una captura del navegador.

## Diferencias entre las tres salidas

| Destino | Fuente | Cuándo se fija | Cambio posterior de la reparación |
|---|---|---|---|
| Informe técnico SAT | Datos guardados actuales. | Al generar o regenerar PDF. | No modifica el PDF archivado hasta su regeneración; las notas complementarias conservan su regeneración existente. |
| Recepción para firma | Copia de texto, nombres de etiquetas y esquemas ya compuestos. | Al crear la solicitud de firma. | No cambia una solicitud pendiente ni un documento firmado. |
| Portal: Recepción firmada | Instantánea de la recepción firmada. | La de esa solicitud. | No mezcla datos actuales con el contenido firmado. |
| Portal: Estado registrado en la reparación | Inspección guardada actual cuando no existe recepción firmada. | Al consultar la ficha. | Refleja cambios guardados posteriores. |

En documentos y portal: si no hay texto, etiquetas ni trazos, no hay sección.
Si no hay trazos, no hay dibujos. Si al menos una cara contiene marcas, aparecen
las dos, identificadas y manteniendo sus proporciones. La selección de formato
sin contenido no crea una página ni una tarjeta.

## Informe técnico y gestión documental

Desde Documentos, en Ficha técnica y diagnóstico, el informe existente añade
Estado del dispositivo en recepción en página propia antes de las fotografías.
Incluye texto completo, etiquetas y los esquemas cuando corresponda. Los textos
largos pueden continuar en otra página sin recortarse; las fotos empiezan en una
página nueva y mantienen una fotografía por página.

Se conserva el PDF del mismo informe en DOCUMENTS de DMS, con el nombre SAT
estable y los permisos de informe existentes. Generar/regenerar actualiza ese
archivo; descargar o enviar usa el archivado. No se crean documentos paralelos.
Editar la inspección no regenera silenciosamente el informe ya emitido.

## Recepción, kiosko y firma

Solo recepción incorpora la nueva inspección. Entrega mantiene su contenido.
La copia guarda también tipo/formato y los dibujos compuestos, de modo que cambiar
una etiqueta del catálogo o una ilustración SVG después tampoco altera lo mostrado.

En borrador puede refrescarse desde la reparación. Desde que la solicitud entra
en cola o está presentada, el contenido queda fijado. Reabrir una solicitud activa
no lo refresca. Para corregirlo se cancela y se reenvía, capturando los datos
actualizados. Los bloqueos de contenido se aplican en Python, no solo en la vista.

El kiosko presenta texto, etiquetas y ambas caras de solo lectura antes de firmar;
en pantallas estrechas las caras se apilan. El PDF lee la misma copia y comienza
la inspección en página propia antes del bloque de firma. Se archiva en SIGNATURES
de DMS. No se añade otra casilla de aceptación por esta integración.

El contenido firmado, la firma y el PDF no pueden reescribirse mediante las acciones
normales ni mediante el antiguo contexto de regeneración forzada. Las operaciones
sobre un mismo documento se serializan; un fallo de PDF/DMS revierte la firma y
permite reintentar. Esto no bloquea la reparación ni otras solicitudes globalmente.
Se mantienen las comprobaciones de acceso y la configuración DMS existente.

Los PDF ya firmados no se migran ni regeneran. Las solicitudes antiguas pendientes
conservan su copia anterior; deben cancelarse y reenviarse si se quiere incorporar
la inspección nueva. No se presupone que un dato actual fue firmado anteriormente.

## Portal B2B

La tarjeta Estado del dispositivo en recepción está en Ficha, justo debajo de
Diagnóstico y notas visibles. No añade pestaña al Hero ni modifica Reparación.
Texto y etiquetas quedan visibles; Ver inspección visual despliega ambas caras
mediante details/summary nativo, plegado inicialmente y sin JS adicional.

Se prioriza la recepción firmada. Para una recepción firmada antigua sin inspección
estructurada, solo se usa su descripción guardada: no se añaden etiquetas o marcas
actuales. Una copia firmada vacía no se sustituye por datos posteriores. Sin firma,
o sin el módulo opcional de firmas, se usa el estado registrado de la reparación.
Solicitudes pendientes, canceladas y firmas de entrega no son fuentes firmadas.

El acceso sigue limitado al commercial_partner_id del usuario autenticado. Antes
de una elevación acotada en el modelo se validan lectura y pertenencia del SAT.
Solo se entregan texto, etiquetas, imágenes SVG embebidas y procedencia. No se
amplían ACL de campos internos, firmas o DMS, ni se exponen notas internas,
instantáneas completas, documentos, ids de archivos o rutas públicas nuevas.
Un SAT ajeno devuelve 404; el texto se escapa y no se admiten URLs remotas para
los esquemas. El portal no depende obligatoriamente de wex_consent.

## Validación y alcance

- Reparación y firmas: 47 pruebas conjuntas sin fallos ni errores.
- Portal con firmas: 28 seleccionadas, 27 ejecutadas y una de garantía omitida
  porque el módulo correspondiente no estaba instalado; sin fallos ni errores.
- Portal sin firmas: 28 seleccionadas, 23 ejecutadas y cinco omitidas por módulos
  opcionales ausentes; sin fallos ni errores.
- Revisión de seis PDF técnicos y cinco PDF firmados, con lectura de vuelta desde
  DMS, textos largos, casos vacíos, consolas y una o ambas caras marcadas.
- Firma ficticia completada en navegador, vuelta a espera y comprobación de que
  cambios posteriores no alteran la copia. Fallo de DMS y reintento verificados.
- Portal revisado como contacto de empresa: copia firmada, datos registrados,
  desplegable y URL ajena bloqueada. Sin envíos externos de correo.
- El usuario confirmó el funcionamiento final el 17/10/2026. La comprobación física
  específica de ergonomía táctil en tablet sigue sin constar como prueba realizada.

Las pruebas del agente se realizaron en bases aisladas con datos ficticios. No se
ha ejecutado una nueva batería por esta consolidación exclusivamente documental.
La compatibilidad antigua de SavepointCase y sus fixtures ya quedó corregida.
La prueba de detalle portal requirió el núcleo de imágenes existente; esa suposición
previa de la base portal no se cambió ni convirtió en nueva dependencia aquí.

## Referencias por módulo

- [Especificación de inspección](SPEC_DEVICE_INSPECTION.md)
- [Historial de implementación](PLAN_DEVICE_INSPECTION.md)
- [Pruebas de reparación e informe](TEST_DEVICE_INSPECTION.md)
- [Arquitectura de firmas](../../wex_consent/ARCHITECTURE.md)
- [Pruebas de firmas](../../wex_consent/docs/TEST_RECEPTION_INSPECTION.md)
- [Arquitectura del portal](../../wexplay_portal/ARCHITECTURE.md)
- [Pruebas del portal](../../wexplay_portal/docs/TEST_RECEPTION_INSPECTION.md)

El registro operativo del proyecto y los changelogs de cada módulo mantienen las
entradas de cada iteración. Las fichas YAML/HTML recogen las reglas vigentes.
