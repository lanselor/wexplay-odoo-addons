# Plan de evolución de Despieces: preparación, imágenes y finalización

Fecha: 2026-09-13.
Estado: implementación autorizada y realizada para preparación, imágenes nativas, finalización, identidad y protecciones. El punto 6 y la fase de impresión están expresamente aplazados por el usuario. Este documento conserva el plan original; ARCHITECTURE.md describe el resultado efectivo.

## 1. Objetivo y decisiones de partida

Preparar repuestos sin llenar el catálogo operativo de productos incompletos, subir las fotos directamente a su destino definitivo y evitar duplicar dispositivos, productos o entradas de stock.

Decisiones acordadas en la conversación:

- Crear los productos nuevos archivados y completar sus fotos en el propio producto.
- Reutilizar imagen principal y galería nativas de Odoo. `website_sale` ya está instalado según lo confirmado por el usuario; su dependencia debe declararse porque se utilizará su galería.
- No incorporar DMS, almacenamiento provisional de imágenes ni manipulación manual del filestore.
- Subir imágenes no activa automáticamente el producto. Usar una acción explícita de finalización.
- Activar el producto nuevo y generar stock al finalizar la pieza.
- No archivar productos existentes al reutilizarlos.
- Buscar también productos archivados en preparación para evitar nuevas fichas duplicadas.
- Mantener la categoría del componente para productos nuevos y conservar la del producto existente.

Las políticas concretas de identificación, cancelación y coordinación de productos compartidos que siguen son propuestas de este plan, todavía no implementadas.

## 2. Flujo operativo completo

### A. Registrar e identificar el dispositivo

1. Crear el lote antes de desmontar, con compañía, técnico, tipo y modelo.
2. Registrar IMEI o número de serie cuando exista. La identidad corresponde al dispositivo físico, no al modelo ni al part number de una pieza.
3. Comprobar si ese dispositivo ya tiene un lote. Si existe uno vigente o finalizado, bloquear la creación normal y facilitar el acceso al anterior dentro de los permisos del usuario.
4. Identificar físicamente dispositivo o bandeja con la referencia del lote desde el inicio.
5. Si no hay identificador legible, permitir continuar con confirmación expresa de identificación física mediante referencia de lote. No prometer detección automática de un mismo equipo sin identificador.

Propuesta de alcance de identidad: compañía + tipo de identificador + valor normalizado. Normalización conservadora; no eliminar caracteres de números de serie sin comprobar que son irrelevantes. La serie genérica no se considera globalmente única entre fabricantes: incluir fabricante en su ámbito cuando proceda. No exponer datos de otras compañías.

La comprobación debe soportar registros simultáneos mediante una restricción o índice único en base de datos, además del mensaje funcional. Los lotes cancelados sin movimientos finalizados podrán liberar esa identidad. Un lote con piezas finalizadas no podrá cancelarse para eludir la protección. La duplicación nativa de un lote no copiará identidad, productos, movimientos ni estados de ejecución.

### B. Revisar piezas

Conservar la fase actual: plantilla, QC, rechazo con motivo, part number o ausencia confirmada, cantidad, nombre y selección de coincidencias.

- La selección de producto existente continúa siendo expresa.
- Coincidencia exacta: no crear otro producto.
- Mostrar si el candidato está activo, archivado en preparación o archivado por otro motivo.
- Ofrecer reutilización normal de activos y de pendientes reconocidos por Despieces. Un archivado ajeno al proceso no se reactiva automáticamente: necesita revisión de catálogo fuera de este flujo.

### C. Completar y validar datos

Conservar precio sin IVA, PVP calculado, coste e impuestos con lógica fiscal nativa.

Validar QC, identidad de pieza, decisión de producto, categoría y datos económicos antes de preparar fichas. Las fotos aún no se exigen en esta fase.

### D. Preparar productos

Nueva acción visible: `Preparar productos`.

- Producto nuevo: crear una única ficha con `active=False`, datos validados y vínculo explícito a su línea de origen. Generar su referencia mediante `wex_product_codes`.
- Producto existente: enlazarlo, conservando su activación y sin aplicar todavía los cambios económicos o de nombre propuestos por esta pieza.
- No generar movimientos de stock en esta acción.
- Si la pieza ya tiene ficha preparada, devolver esa ficha, sin crear otra.
- Revalidar coincidencias antes de crear, porque otro usuario puede haber preparado un producto desde la búsqueda inicial.
- El producto pendiente no estará publicado en web. Activar y publicar son acciones diferentes.

Desde este momento, el producto es la fuente de verdad de sus fotos y de los datos económicos que se completen en su ficha. Para productos nuevos preparados, impedir que valores antiguos de la línea sobrescriban cambios posteriores del producto. Para reutilizaciones, la línea conserva los cambios propuestos hasta finalizar y permite revisarlos antes de aplicarlos.

No se permite cambiar libremente producto seleccionado, componente o decisión después de preparar la ficha. Una rectificación debe ser explícita y comprobar que no hay stock ni otros usos antes de desvincular nada.

### E. Completar imágenes

Nueva superficie `Productos pendientes` dentro del despiece, accesible al reabrirlo.

Cada fila mostrará pieza, referencia y nombre del producto, nuevo/existente, imagen principal, estado de preparación y acceso a `Abrir producto` y `Finalizar pieza`.

- Abrir directamente la ficha nativa, incluso si el producto está archivado.
- Subir la imagen principal y fotos adicionales con los controles nativos.
- No copiar fotos entre pieza y producto, no guardar rutas del filestore y no ampliar `product.image` para almacenamiento temporal.
- Mostrar el estado actualizado al regresar de la ficha.
- Una imagen adicional sin imagen principal no cumple el requisito de finalización.
- Producto existente con imagen principal: no exigir volver a fotografiarlo.
- Producto existente sin imagen principal: completar la imagen antes de finalizar la entrada de esa pieza.
- Las imágenes son de catálogo compartido, no evidencia individual de cada unidad recuperada. No reemplazar automáticamente fotos existentes.

### F. Finalizar la pieza

Acción explícita `Finalizar pieza`. Una acción de lote `Finalizar piezas listas` podrá procesar las que cumplan requisitos y mostrar claramente cuáles continúan pendientes.

Validación backend:

- Lote no cancelado y pieza apta, con producto preparado y datos válidos.
- Imagen principal presente en el producto definitivo.
- Compañía y ubicación interna válidas.
- No existe entrada de stock finalizada para esa línea.
- Producto activo o pendiente de activación reconocido por este proceso; no reactivar un archivado ajeno.
- Acceso suficiente a pieza, producto y stock.

Ejecución atómica por pieza:

1. Bloquear la línea y, cuando corresponda, el producto para evitar doble procesamiento concurrente.
2. Revalidar condiciones después del bloqueo.
3. Aplicar cambios autorizados al producto existente, si los hay.
4. Activar el producto nuevo o el producto compartido pendiente autorizado.
5. Crear y completar el movimiento nativo desde `Despieces / Origen` a la ubicación de compañía.
6. Registrar finalización, usuario, fecha y movimiento, y recalcular el estado del lote.

Si falla cualquier paso, revertir toda esa finalización. No dejar el producto activado por esta acción sin su entrada de stock. Registrar el error después del rollback del savepoint. Un reintento nunca añade stock por segunda vez.

Subir fotos, guardar una ficha o desarchivarla manualmente nunca genera stock. La activación manual de productos reconocidos como pendientes debe pasar por la misma validación de finalización; bloquear el atajo genérico mientras siga pendiente, también por RPC/importación, sin alterar el archivado de otros productos.

## 3. Estado y fuente de verdad

Mantener separados el estado persistido del lote y `workflow_focus`.

- Conservar los estados históricos: una línea `created` con movimiento terminado sigue siendo finalizada.
- Añadir un estado de línea `product_prepared` para el producto vinculado pendiente de finalización.
- Añadir un estado de lote `products_prepared`; mantener `partial_created` para finalización parcial y `done` para todas las líneas finalizadas o descartadas.
- Una línea descartada no exige producto ni foto ni genera stock.
- La presencia de `product_tmpl_id` deja de significar que la pieza ya entró en inventario.
- Añadir un vínculo de origen en producto, por ejemplo `wex_teardown_origin_line_id`, para distinguir un archivado de preparación de una retirada de catálogo. No inferirlo solamente de `active=False`.
- Si varios despieces reutilizan el mismo producto preparado, la preparación del catálogo se resuelve una sola vez, pero cada línea conserva su propia finalización y movimiento de stock.
- Tras activar el producto, el estado de preparación de catálogo deja de bloquear las otras líneas. Un archivado posterior no debe interpretarse como nueva preparación.

Resolver el estado de preparación de catálogo en un único punto; si hace falta un estado explícito en producto para separar activación de finalización de su línea de origen, justificarlo en la implementación. No duplicar flags editables entre lote, línea y producto.

## 4. Duplicados y concurrencia

Hay tres protecciones diferentes:

1. Dispositivo físico: impedir dos lotes para una misma identidad conocida.
2. Catálogo: reutilizar coincidencias exactas, incluidas fichas archivadas en preparación.
3. Inventario: como máximo una entrada finalizada por línea.

Usar `active_test=False` solo en búsquedas y accesos acotados, conservando permisos y dominios de compañía. No habilitar indiscriminadamente todos los archivados.

La búsqueda previa no basta para dos creaciones simultáneas. Serializar la creación para la misma clave exacta normalizada y volver a buscar bajo bloqueo. Elegir el mecanismo tras revisar PostgreSQL y los dominios existentes; no imponer una unicidad global que invalide el catálogo histórico. Coincidencias aproximadas siguen necesitando decisión humana.

Si dos piezas proponen precios o nombres diferentes para un mismo producto, mostrar el valor actual y requerir revisar la propuesta cuando haya cambiado desde su preparación. No sobrescribir silenciosamente cambios concurrentes.

## 5. Cancelación y rectificación

- Antes de preparar productos: cancelación sin efectos sobre catálogo o stock.
- Con productos preparados y sin stock: conservar las fichas archivadas y la trazabilidad. Mostrar que la preparación fue cancelada, retirarla de pendientes operativos y no borrar automáticamente fotos o productos.
- Producto pendiente reutilizado por otra línea: la cancelación del lote de origen no debe eliminarlo ni impedir que la otra línea autorizada complete su preparación. Resolver o reasignar el origen operativo de forma explícita.
- Con alguna entrada finalizada: bloquear la cancelación y la vuelta genérica a revisión; una devolución o corrección de inventario necesitará un flujo explícito posterior.
- No permitir borrar lotes o líneas que hagan perder trazabilidad de fichas preparadas o movimientos. Las retiradas de fichas abandonadas se gestionan con permisos de responsable, sin borrado físico manual.

## 6. Etiquetas e identificación física

Dos momentos distintos:

- Al registrar: etiqueta de lote con referencia legible y datos mínimos para reconocer el dispositivo/bandeja.
- Al finalizar: etiqueta de producto con su referencia definitiva mediante la impresión existente.

Antes de implementar impresión, inspeccionar las APIs reales de `wexplay_product_print` y `wex_print_core`. Reutilizar la etiqueta de producto existente. Para lote, definir QWeb/formato y encaje en el stack sin crear otra integración QZ.

La impresión no condiciona la transacción de stock ni activa el producto. Un fallo permite reimprimir sin volver a finalizar. No marcar una impresión física como confirmada si la API solo acredita envío.

La integración con impresión será opcional y separada si requiere dependencias adicionales. Mientras no esté disponible, la referencia visible permite etiquetado manual. El formato y medio físico de la etiqueta de lote se elegirán antes de codificar esa fase.

## 7. Archivos previstos y responsabilidades

Los nombres de métodos son propuesta; se ajustarán sin duplicar helpers existentes.

| Archivo | Responsabilidad y métodos relevantes |
|---|---|
| `__manifest__.py` | Declarar `website_sale`, incrementar versión y cargar vistas necesarias. No añadir dependencias de DMS ni impresión al núcleo del flujo. |
| `models/wex_teardown_batch.py` | Identidad física, estados y acciones finas: `_check_device_identity`, `action_prepare_products`, `action_finalize_ready_lines`, actualización de resumen y controles de cancelación. |
| `models/wex_teardown_line.py` | Separar preparación/finalización: `action_prepare_product`, `_prepare_product`, `_check_can_finalize`, `action_finalize_piece`, `_finalize_piece`; reutilizar preparación de valores, validación y stock existentes. Aislar errores y bloquear reintentos concurrentes. |
| `models/product_template.py` | Origen y preparación de catálogo, protección de activación manual, acceso a despieces autorizados y validación central de activación. No almacenar otra copia de imágenes. |
| `views/wex_teardown_batch_views.xml` | Acciones, fase de productos pendientes, cantidades y estados inequívocos. |
| `views/product_template_views.xml` | Aviso de preparación, origen y acceso al flujo de finalización. Reutilizar la ficha y galería nativas. |
| `static/src/js/notebook_focus_widget.js` | Incorporar el foco de productos pendientes al mecanismo existente. |
| `static/src/js/data_completion_widget.js` y su XML | Adaptar acciones/datos si afecta a su superficie actual; mantener decisiones de negocio en Python. |
| `security/ir.model.access.csv` y `security/wex_teardown_security.xml` | Revisar acceso efectivo a productos archivados y galería; conceder solo lo necesario y mantener aislamiento por compañía. |
| `tests/__init__.py`, `tests/test_teardown_preparation.py`, `tests/test_teardown_finalization.py` | Casos críticos de preparación, fotos, transacciones, seguridad y reintentos. |
| `tests/test_teardown_identity.py` | Identidad física y concurrencia; usar conexiones independientes para carreras reales. |
| `ARCHITECTURE.md` | Actualizar después de implementar para describir el comportamiento efectivo. |
| `ERRORS_AND_FIXES.md` | Registrar problemas corregidos cuando corresponda. |

Evitar otro widget OWL si una lista/formulario nativo resuelve productos pendientes. Los archivos de impresión, migración o wizard se enumerarán concretamente tras la revisión de esa fase, antes de modificarlos.

## 8. Fases de implementación

### Fase 0: revisión técnica y datos existentes

- Verificar versión local real de Odoo, galería instalada, ACL y extensiones de almacenamiento/producto.
- Revisar reglas de código interno en productos archivados, matcher y estados históricos.
- Comprobar cómo queda la preparación compartida entre compañías si el catálogo es global.
- Identificar productos con variantes o seguimiento por lote/serie: no asumir `product_variant_id` único ni generar stock sin trazabilidad requerida. Bloquear casos no soportados con mensaje claro antes de activar.
- Revisar confirmación de advertencias: actualmente `_prepare_for_data_completion` la reinicia; asegurar que una confirmación válida se puede utilizar y que se invalida solo ante cambios relevantes.

### Fase 1: identidad del dispositivo y protección de estados

Añadir identidad, detección concurrente y reglas de cancelación/copia. Permitir registros históricos sin identidad; exigir identificación o confirmación física para los nuevos. No deducir seriales de notas antiguas.

### Fase 2: preparación y finalización backend

Separar producto/stock, introducir pendientes, acceso a archivados, política de reutilización y activación, y transacciones por pieza. Mantener instalable el módulo y añadir pruebas críticas con la funcionalidad.

### Fase 3: interfaz e imágenes nativas

Exponer preparación, pendientes y finalización; abrir fichas archivadas; mostrar foto principal y progreso. Revisar el flujo con usuario normal y responsable.

### Fase 4: impresión

Integrar etiqueta temprana de lote y reutilización de etiquetas de producto tras inspeccionar el stack. Separar entrega de impresión del éxito del inventario.

### Fase 5: validación y actualización

Probar sobre copia de la base antes de actualizar producción. Las líneas históricas finalizadas no se archivan, no exigen fotos retroactivamente y no regeneran stock. No convertir automáticamente estados parciales ambiguos: presentar incidencias para revisión.

Actualizar arquitectura con el resultado real. El registro global `C:\odoo18\WEXPLAY_CHANGELOG.md` se actualizará cuando se solicite, siguiendo su formato de tabla y conservando entradas anteriores.

## 9. Pruebas de aceptación

1. Preparar una pieza nueva crea un producto archivado y cero entradas de stock.
2. Repetir la preparación reutiliza la misma ficha.
3. Abrir la ficha archivada y subir varias fotos mediante la galería nativa funciona con los permisos previstos.
4. Subir una foto no activa ni genera stock; sin principal no se puede finalizar.
5. Finalizar activa y genera exactamente la cantidad indicada, con movimiento y trazabilidad.
6. Fallar el movimiento revierte la activación y las modificaciones de esa finalización; permite reintentar.
7. Doble clic y dos sesiones concurrentes no crean dos entradas ni dos fichas exactas.
8. Un producto existente activo nunca se archiva y conserva sus fotos; recibe stock solo al finalizar su línea.
9. Otro despiece detecta y reutiliza un producto archivado en preparación; ambos generan sus cantidades una sola vez.
10. Un archivado por retirada de catálogo no se reactiva accidentalmente.
11. Dos altas concurrentes del mismo dispositivo conocido no crean dos lotes válidos.
12. Sin identificador, el flujo exige confirmación de identificación física y explica su alcance.
13. Cancelar preparación conserva fotos y fichas, sin stock; un lote con stock finalizado no se cancela por el atajo actual.
14. Cambios de precio/nombre en un producto compartido no se sobrescriben desde datos antiguos sin revisión.
15. Acceso directo por RPC respeta validación, permisos y compañías; no basta la invisibilidad de botones.
16. Despieces históricos finalizados mantienen productos, movimientos y estados al actualizar.
17. Un fallo de impresión permite reimprimir sin repetir activación ni stock.

## 10. Límites de esta iteración

No crear productos paralelos, DMS, galerías propias, servicios externos de matching, publicación automática en tienda, reversión automática de stock ni un sistema nuevo de impresión.

Archivar reduce la presencia en el catálogo operativo habitual; no equivale a una barrera de seguridad ni garantiza que cualquier integración externa ignore esos productos. Verificar expresamente los consumidores del catálogo que tenga la instalación.

El resultado esperado es una única ficha definitiva por producto, fotos guardadas desde el principio en Odoo y entrada de stock únicamente cuando cada pieza se finaliza de forma explícita.
