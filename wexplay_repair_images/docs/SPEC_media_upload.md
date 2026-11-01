# SPEC — Preparación de imágenes SAT

| Campo | Valor |
|---|---|
| Módulo | wexplay_repair_images |
| Fecha | 2026-11-01 |
| Estado | Aprobada por el usuario en conversación antes de implementar |
| Versión | 1.0 |
| ADR | ADR_media_upload.md |

## Problema y contexto
Las fotografías móviles necesitan recorte, anotaciones y descripción antes de almacenarse.
Usuarios: técnicos con los permisos actuales de gestión multimedia SAT. Sin nuevos permisos ni exposición portal.

## Solución y reglas
Selección y arrastre abren una galería previa. Edición y descripción son opcionales e individuales.
El navegador recorta y pinta; solo entrega el resultado confirmado. Una imagen sin cambios conserva su archivo.
La descripción se guarda en el campo existente. La compresión y DMS mantienen su comportamiento.
Los vídeos conservan su ruta y procesamiento, sin edición ni descripción nueva.
Cancelar antes de confirmar no envía archivos. Los envíos confirmados no se revierten al cerrar tras un fallo parcial.

## Aceptación y casos de uso
- Seleccionar o arrastrar una o varias fotos abre la misma ventana.
- Cambiar de foto conserva descripción y edición; quitar descarta el archivo pendiente.
- Confirmar sin editar sube los originales; editar envía una imagen PNG sin compresión destructiva adicional.
- Recorte y pincel con colores/grosor, deshacer y restablecer disponibles.
- Fallo parcial conserva pendientes y no reenvía los ya confirmados por el servidor.
- Servidor sigue comprimiendo y almacenando con el circuito existente.

## Fuera de alcance
Edición de fotos ya guardadas, almacenamiento de originales editados, campos/modelos nuevos, cambios de compresión, filtros y textos sobre la imagen.

## Validación
Prueba de navegador aislada con OWL real y biblioteca local: dibujo, exportación, galería, descripción y reintento parcial.
PENDIENTE: actualización y prueba end-to-end en instancia Odoo y móvil físico.

## Iteración visual aprobada — 2026-11-01
Usuario autoriza implementar: foto protagonista, herramientas compactas y barra lateral persistente de color/grosor al pintar. Trazo sólido sin controles de opacidad ni desenfoque; quitar selector redundante Pincel. Mantener descripción y galería. Se utiliza pantalla completa y banda inferior compacta; móvil mantiene banda de miniaturas sobre descripción para conservar ergonomía. Aceptación: color y grosor cambian el trazo exportado, controles visibles sin desplegables y sin nuevas opciones de transparencia. Sin cambios de servidor.

## Funcionamiento final — 2026-11-01
El área multimedia del chatter acepta selección y arrastre. La ventana muestra la galería sobre una descripción opcional por fotografía, una zona de imagen ampliada y herramientas de recorte y pintura. Al pintar se muestran color y grosor; el trazo es opaco. El exterior del recorte se oculta visualmente y el original se conserva durante la preparación. La edición no modifica el archivo original; se envía el resultado confirmado. Las imágenes no editadas mantienen su archivo, y los vídeos usan su procesamiento existente.

En envíos múltiples, los archivos confirmados quedan marcados y un reintento continúa con los pendientes. Si el servidor guarda un archivo pero su respuesta se pierde, el resultado es ambiguo y no existe una garantía de idempotencia. El GIF editado se exporta como imagen estática. No se modifican las rutas de filestore, compresión ni almacenamiento DMS; la subida de imágenes recibe además la descripción opcional.

## Estado de validación
El usuario ha podido abrir y utilizar el editor en Windows después de corregir el bloqueo de diálogo. Las pruebas automatizadas cubren el ciclo de diálogo de Odoo, dibujo y exportación, máscara de recorte, deshacer y rehacer en la imagen activa, descripciones y reintento parcial simulado. Pendiente confirmar con un móvil físico, fotografías grandes y el resultado guardado en el entorno real. No está confirmado que el historial de deshacer sobreviva al cambiar de miniatura y volver; la edición y descripción sí se conservan al cambiar de imagen.
