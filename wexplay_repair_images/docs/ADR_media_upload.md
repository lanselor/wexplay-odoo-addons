# Arquitectura / ADR â€” Editor previo a la subida SAT
Fecha: 2026-11-01. Estado: implementado segÃºn plan aprobado.
SPEC: SPEC_media_upload.md.

## Contexto e impacto
Ãšnico mÃ³dulo funcional afectado: wexplay_repair_images. repair.order recibe descripciÃ³n opcional en el mÃ©todo existente; no hay modelos, campos, ACL ni migraciones nuevos. Portal, informes y compresiÃ³n no cambian.

## DecisiÃ³n
Componente OWL de diÃ¡logo con lote temporal, miniaturas y descripciÃ³n por fotografÃ­a. Filerobot 4.8.1 MIT vendorizado, cargado bajo demanda desde el servidor local. Se restringen dos tablas de herramientas del bundle a Crop y Pen; los reemplazos quedan documentados en static/lib/filerobot/README.md. Se deshabilitan traducciones remotas y procesamiento cloud. H5P descartado por alcance y TOAST UI por archivo del proyecto.

El estado de diseÃ±o se conserva junto al archivo original en memoria para reabrir ediciones. Los cambios se exportan a PNG antes de cambiar de foto o subir, sin aÃ±adir compresiÃ³n destructiva. Original no editado se envÃ­a sin transformaciÃ³n. Las URLs temporales se liberan al quitar/cerrar. Una sola instancia del editor evita multiplicar memoria por foto.

## Flujo
SelecciÃ³n/arrastre -> diÃ¡logo -> archivo preparado + descripciÃ³n -> mÃ©todo existente de repair.order -> compresiÃ³n existente -> create_image_from_binary -> DMS.
VÃ­deos -> controlador existente -> cola de procesamiento existente.

## Responsabilidades y mÃ©todos
- chatter_repair_images_patch.js: abrir diÃ¡logo, fijar repairId para evitar subir a otro SAT al navegar, callback uploadFile y refresco.
- repair_media_upload_dialog.js: mountEditor/destroyEditor, captureCurrentImage, selectItem, updateDescription, removeItem y upload.
- plantilla XML / SCSS: estructura, galerÃ­a, descripciÃ³n, estado y adaptaciÃ³n mÃ³vil.
- repair_order.py: parÃ¡metro opcional description compatible con llamadas anteriores.
- manifiesto: recursos y versiÃ³n 18.0.1.2.0.

## Errores y lÃ­mites
Subida secuencial, estado de confirmaciÃ³n por archivo y reintento de pendientes. Cierre bloqueado durante envÃ­o. Una respuesta de red perdida despuÃ©s de confirmar en servidor sigue siendo ambigua: no se introduce protocolo de idempotencia nuevo. GIF editado se convierte a imagen estÃ¡tica; formatos que el navegador no decodifica pueden subirse sin editar. Prueba aislada no sustituye validaciÃ³n en Odoo instalado ni en mÃ³vil fÃ­sico.

## Corrección 2026-11-01: compatibilidad de estilos
El compilador libsass de Odoo evalúa min(55dvh, 560px) como función Sass y falla por unidades incompatibles. Se usa height: 55vh más max-height: 560px; móvil usa 50vh. Se reproduce el error con el Python de Odoo antes del cambio y se añade comprobación real de compilación en tests/browser/check_styles.py. La prueba previa de navegador no compilaba SCSS y no cubría este fallo.

## Investigación de bloqueo al seleccionar — 2026-11-01
Usuario confirma que el bloqueo ocurre al seleccionar, antes de mostrar galería, sin errores de consola. No se ha reproducido en prueba aislada: causa exacta pendiente de confirmar en la instancia afectada. Se desactiva observePluginContainerSize para eliminar posible realimentación de layout, se monta el editor tras dos frames para permitir el dibujo del diálogo, y se contiene su layout. No cambia la subida ni compresión. Se corrige también codificación de textos del editor.
Validación: compilación real con libsass, prueba OWL de recorte/pincel/descripciones/reintento y comprobación temporal con clase/plantilla nativas de Dialog, datos reactivos y hooks de servicios simulados: apertura, respuesta del event loop y cierre por cabecera. No equivale a validación de la instancia completa. PENDIENTE: confirmar resolución en el navegador afectado.

## Causa reproducida y corrección definitiva del bucle — 2026-11-01
La prueba con overlayService, OverlayContainer y dialogService reales reproduce el bloqueo antes de abrir. Sustituir env.dialogData.close desde setup modifica datos reactivos compartidos del servicio y provoca un bucle de actualización con crecimiento de memoria. Al retirar esa mutación el mismo ensayo abre y cierra con normalidad. La investigación anterior sobre ResizeObserver era una hipótesis insuficiente y no resolvía este bucle.

Se utiliza una subclase local RepairMediaDialog con prop busy y dismiss() que delega en el comportamiento nativo cuando no se está enviando. No se altera env.dialogData. Se añade tests/browser/odoo_dialog_lifecycle.cjs que carga las clases, servicios y plantillas desde la instalación Odoo, simulando únicamente hooks de servicios auxiliares y el callback de red: apertura, cierre, reapertura, envío y cierre bloqueado durante envío. La prueba tiene un límite externo de tiempo para detectar bloqueos del hilo de la página. Pasan también pruebas de edición y compilación libsass. Pendiente comprobación final en la instancia del usuario.

Verificación DMS/filestore: diff de repair_order.py limitado a description opcional y su transmisión a create_image_from_binary. No se modifican _compress_sat_image, _get_sat_image_directory, wexplay_image_core, OCA DMS ni configuración/rutas de filestore. El bloqueo reproducido ocurre antes de invocar uploadFile, por tanto no ejecuta escrituras DMS.

## Iteración visual — 2026-11-01
Plan aprobado: ampliar foto y compactar herramientas en el diálogo. Archivos: componente JS (defaults de trazo opaco y versión del recurso), plantilla XML (pantalla completa/banda inferior), SCSS (distribución flexible/controles), bundle Filerobot y su parche reproducible, pruebas navegador/compilación y manifiesto. Sin métodos de negocio ni cambios Python. Nuevo componente interno del bundle wexPenControls usa el actualizador inmediato de anotación nativo para color y grosor, sin sustituir el motor. Debounce descartado para evitar perder un cambio de grosor al cambiar el color inmediatamente. Opacidad fijada a 1 y sombra desactivada en defaults y cambios del control. Se conservan callbacks, historial, recorte y trazos originales de la biblioteca.

SCSS usa clases semánticas FIE de la versión fijada, sin selectores de clases generadas ni índices de elementos. Herramientas de recorte flotan en esquina; panel de pincel flota al lateral. No hay selector redundante del único pincel. Disposición compacta inferior: galería y descripción en una banda en escritorio, apiladas en móvil. Pantalla completa con cuerpo flexible permite ampliar el encuadre sin un tope de 560px. Las barras FIE siguen siendo responsables del zoom y selección de modo.

Validación: libsass real; prueba de recorte/pincel/galería/descripciones/reintento; prueba con servicios Odoo y SCSS compilado para abrir/cerrar/reabrir, modificar color y grosor, dibujar y comprobar píxeles verdes opacos en PNG exportado. Capturas de escritorio y viewport móvil revisadas. Pendiente prueba con dedo en móvil físico y en instancia de usuario con todos los estilos de Odoo.

## Altura explícita del diálogo — 2026-11-01
La captura del usuario muestra el contenedor reducido al mínimo de 240px: fullscreen no garantiza altura en todos los estilos de escritorio de Odoo. Se asigna altura y altura máxima al modal-content concreto mediante calc(100vh - 32px) y el cuerpo recibe flex: 1 1 0. No depende de que el tema interprete fullscreen; conserva espacio para galería, descripción y botones. El editor sigue ajustando la foto completa a la superficie resultante. Se elimina de la prueba la altura de modal-content simulada que ocultaba el defecto y se verifica que el lienzo ocupe al menos el 55% de la altura del viewport de escritorio. Compilación libsass y prueba de servicios de diálogos superadas.

## Lateral sin desbordamiento y descripción de ancho completo — 2026-11-01
Se confirma en prueba que el lateral tenía clientWidth 64 y scrollWidth 80: los botones conservaban su ancho fijo de biblioteca. Se ajusta FIE_tab al 100% del ancho interior con box-sizing border-box, iconos de 18px y centrado explícito, sin ocultar una barra que siguiera teniendo contenido fuera. Galería arriba de descripción en todos los tamaños; campo de texto al ancho completo de la banda inferior. Cambios en SCSS y versión del manifiesto; sin cambios de motor o subida. La prueba verifica ausencia de overflow horizontal, centrado del icono y ancho/orden de galería y descripción. Se adapta umbral de lienzo a 45% del viewport de prueba de 720px de altura al reservar una fila adicional para galería por decisión del usuario. Compilación y pruebas de ciclo de vida/editor superadas.

## Máscara exterior opaca de recorte — 2026-11-01
Usuario pide ocultar completamente la parte exterior sin perder posibilidad de deshacer antes de subir. Se sustituye solo la Image desenfocada/oscurecida de CropTransformer por un Rect opaco con color bg-secondary del tema. Se conserva la ventana destination-out y los manejadores nativos, por lo que se ve únicamente la zona seleccionada y el original sigue siendo la fuente de edición. Adaptación exacta reproducible: static/lib/filerobot/crop_overlay_patch.py. No se modifica geometría ni exportación. El archivo original se conserva en el lote; cualquier previsualización exportada al cambiar de miniatura es temporal y no lo reemplaza. Solo se envía el resultado al confirmar subida. Prueba de navegador verifica píxel exterior opaco de fondo, ausencia de envío al recortar, deshacer recuperando anchura original y rehacer recuperando recorte antes de subir. Sin cambios de servidor.
