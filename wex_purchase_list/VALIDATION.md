# Devoluciones a proveedor — guía de validación

Versión actual: `18.0.1.5.0` para Odoo 18 Community.

## Aceptación y observación diaria — 01/11/2026

El usuario confirma que el funcionamiento probado es correcto. La entrega queda aceptada funcionalmente y comienza la prueba en el día a día. El aviso de activación pendiente que constaba al entregar el código queda superado por esta confirmación; no se afirma con ello un despliegue de producción ni una validación prolongada.

Durante el uso diario conviene contrastar las piezas de las cajas de proveedor con las pendientes de Odoo, revisar que los envíos solo se validan al salir físicamente, comprobar los motivos y RMA registrados y observar las nuevas solicitudes SAT y los destinos excepcionales. Si aparece una incidencia, conservar referencia del SAT, devolución y documento de Inventario, cantidad/lote, acción realizada y mensaje de error para poder reconstruirla. No se añaden tareas automáticas ni pasos obligatorios por esta recomendación.

## Resultado de esta entrega — 01/11/2026

- Cambios aplicados al módulo activo; instalación limpia y actualización correctas.
- Suite final: 111 pruebas, cero fallos y cero errores (`C:\odoo18\test\purchase_exceptions_complete.log`).
- Diez escenarios de concurrencia entre traslado, envío, recuperación, desecho y nueva solicitud, incluidos reintentos de un mismo asistente (`purchase_exceptions_complete_concurrency.log`; los resultados se imprimen en la ejecución de los scripts).
- Los modificadores de las vistas se evalúan con el JavaScript nativo de Odoo: 221184 evaluaciones correctas. No sustituye la comprobación visual en el navegador.
- Se conserva una traza anterior con su referencia SAT y RMA, la ubicación personalizada de la compañía y el motivo histórico vacío al actualizar. Evidencia: `purchase_exceptions_upgrade_preservation.log` y `purchase_exceptions_upgrade_final.log`.
- En la comprobación previa a entregar el código, `test2` seguía en `18.0.1.4.3`; aquella ejecución no reinició ni actualizó el servicio. Posteriormente el usuario confirmó que la entrega funciona correctamente, según la aceptación anterior. La instalación o actualización en cualquier otro entorno sigue requiriendo cargar el código y actualizar el módulo desde Odoo.

## Nuevos casos: motivos y resoluciones excepcionales

1. Abrir Devolver a proveedor. Debe exigir un motivo y, al elegir Otro, observaciones. La ficha de devolución conserva ambos y el listado permite agrupar por motivo. Las devoluciones anteriores sin motivo siguen pudiendo enviarse.
2. En un SAT abierto, marcar opcionalmente Añadir nuevamente el repuesto al SAT y solicitarlo y revisar cantidad. Confirmar la retirada. Comprobar una pieza SAT nueva y una solicitud pendiente en la lista de compra, enlazadas desde la devolución. Repetir la acción no duplica la solicitud. En SAT Finalizada o Entregada no se ofrece la opción; no se añade un bloqueo nuevo al flujo de devolución.
3. Desde una ficha pendiente usar Resolver sin enviar, elegir cantidad, destino disponible y explicación. Recuperar para uso realiza un traslado interno, reduce las pendientes de envío y permite usar el material en otra reparación. No restaura la pieza del SAT original.
4. Conservar para revisión registra una anotación. La pieza permanece apartada y puede prepararse y enviarse después sin desbloqueos adicionales.
5. Desechar abre un documento nativo en borrador. Hasta validarlo no reduce las unidades pendientes ni bloquea prepararlas para envío. La validación vuelve a comprobar el stock y las cantidades pendientes; si se enviaron entretanto, el desecho no puede realizarse.
6. Con dos o más unidades, mezclar envío, recuperación y desecho parciales. La suma de destinos realizados nunca debe superar las apartadas. Comprobar el historial con usuario, fecha, decisión y documentos; el estado refleja cierre mixto o sin envío.
7. Si ya existe un envío preparado, revisar/cancelar sus reservas desde Inventario antes de recuperar esas unidades. Una parte libre puede recuperarse sin alterar otras reservas. Una pieza ya enviada requiere registrar primero su regreso nativo y comprobar su ubicación física.

Los scripts de concurrencia solo admiten bases desechables `codex_purchase_*`. La verificación de modificadores usa el evaluador JavaScript del Odoo instalado para detectar errores que la prueba Python de formularios no cubre.

## Activación

Actualizar `wex_purchase_list` con el código nuevo cargado. Reiniciar por sí solo no crea las columnas ni las vistas nuevas: actualizar el módulo antes de trabajar con él.

El servicio y el proceso de actualización deben usar el mismo directorio de datos de Odoo. No cambiar el almacén de archivos para resolver un problema de permisos de Windows. La actualización desde Aplicaciones usa la cuenta del servicio y su configuración habitual.

## Permisos y configuración

- Un administrador de Ajustes revisa **Lista de compra > Configuración > Devoluciones a proveedor**. La ubicación predeterminada existe por compañía y puede sustituirse por otra interna, activa y fuera del stock habitual y suministro SAT.
- Los responsables usan **Wexplay Purchase List Manager** y sus permisos normales de Inventario y de edición del SAT/venta afectados. El módulo no concede permisos nativos adicionales.
- Los usuarios **Wexplay Purchase List User** consultan las devoluciones. Abrir un documento de Inventario requiere sus permisos propios.
- El almacén debe tener activo su tipo de traslado interno. Revisar la configuración nativa de Ubicaciones de almacenamiento si no existe un tipo activo.
- Con varias compañías, activar la compañía correcta antes de gestionar sus piezas. Los documentos de compañías distintas se mantienen separados.

## Prueba principal con dos unidades

Usar datos de prueba: producto con seguimiento de inventario, compra y recepción validada de dos unidades, vinculadas a una línea de la lista de compra. Si el producto tiene lote o serie, utilizar los datos realmente recibidos.

1. Abrir la línea de compra y pulsar **Devolver**, o **Devolver a proveedor** desde la pieza vinculada del SAT.
2. Comprobar proveedor, compra, recepción, unidades recibidas y ubicación física. Seleccionar una unidad y, si procede, lote/serie y paquete.
3. Revisar el SAT o la venta que muestra el asistente. Confirmar su retirada/reducción solo si corresponde. La factura y las entregas realizadas se resuelven desde sus documentos; no se fuerzan desde este flujo.
4. Confirmar y apartar físicamente la pieza. Se abre un traslado interno realizado. La línea muestra su trazabilidad y la pieza figura **Pendiente de envío**.
5. Entrar en **Lista de compra > Devoluciones**. Seleccionar piezas del proveedor y, si se dispone de ella, usar **Asignar RMA**. La referencia es opcional y también se edita individualmente abriendo la ficha.
6. Pulsar **Crear devolución**. Revisar el resumen y el recordatorio de la gestión con el proveedor. Se abren uno o varios documentos nativos, según las recepciones y ubicaciones.
7. Cuando salga la caja, usar **Validar** en los documentos de Odoo. Comprobar que el estado y las cantidades devueltas se actualizan.

Con una unidad apartada de las dos recibidas, los resultados esperados son:

| Momento | Stock habitual | Zona de devoluciones | Reservadas para el envío | Total físico de la empresa |
| --- | ---: | ---: | ---: | ---: |
| Recepción validada | 2 | 0 | 0 | 2 |
| Apartar una unidad | 1 | 1 | 0 | 2 |
| Crear devolución | 1 | 1 | 1 | 2 |
| Validar el envío | 1 | 0 | 0 | 1 |

El RMA del proveedor y el número del documento de Odoo son referencias distintas. Un RMA común puede aparecer en varios documentos nativos sin duplicar el stock.

## Casos adicionales

- Cotización editable: reducir parcialmente y retirar una línea completa. La venta de origen debe conservarse en el historial de devolución.
- Venta confirmada: reducir la cantidad sin cancelar ni pasar el pedido a borrador; una cantidad cero mantiene su línea.
- SAT: reducir o retirar la pieza pendiente y comprobar la sincronización nativa de su venta. La referencia SAT de la devolución no puede cambiarse después.
- Factura en borrador o confirmada, entrega realizada, venta bloqueada o pieza marcada como utilizada: el ajuste automático debe rechazarse sin alterar stock ni documentos.
- Reserva completa sin aviso: al apartarla por completo deja de solicitar aviso al cliente. Un aviso ya registrado conserva su historial.
- Falta de stock libre: no se liberan otras reservas y se revierten también los cambios del origen si falla el traslado.
- Dos piezas de la misma recepción: comprobar selección múltiple, RMA común y un documento de devolución con trazabilidad individual.
- Distintas recepciones, ubicaciones o proveedores: se generan los documentos separados que correspondan. El RMA conjunto solo admite una misma compañía y proveedor comercial.
- Envío parcial: conservar o cancelar el pendiente mediante el asistente nativo. Usar **Abrir documentos** para consultar todo el historial y **Comprobar disponibilidad** en el pendiente si Odoo lo requiere.
- Cancelar un documento sin enviar: permite prepararlo de nuevo sin perder el primer documento. No se cancela un movimiento ya realizado desde este módulo.
- Si el proveedor devuelve una pieza: la recepción inversa respeta el destino interno nativo. Para remitirla otra vez, revisar y trasladar físicamente sus existencias a la zona de devoluciones mediante Inventario.
- Repetir una misma confirmación no debe duplicar el traslado ni la devolución.

## Comprobaciones automáticas

La suite del módulo cubre configuración, integridad, permisos, unidades de medida, compañías, traslado, ventas/SAT, facturas, RMA, lotes/series, parciales, cancelaciones e idempotencia.

El script `tests/verify_return_concurrency.py` añade cuatro escenarios con conexiones independientes. Solo admite bases desechables `codex_purchase_*` y confirma datos de prueba; no ejecutarlo sobre datos operativos.

La revisión final incluye instalación limpia, actualización con selección personalizada e historial existente, suite completa y concurrencia. La arquitectura y las decisiones están documentadas en `ARCHITECTURE.md` y `DECISION_LOG.md`.

## Alcance final

La gestión en la web del proveedor, la recogida física y el abono siguen siendo tareas independientes. No se automatizan plazos ni abonos, no se crean facturas paralelas y no se corrigen cantidades mediante ajustes de inventario artificiales.

## Resultado de validación — 31/10/2026

Registro histórico de la Fase 4; el estado de activación descrito aquí corresponde a aquella comprobación.

- Versión implementada: `18.0.1.4.0`, en el módulo activo.
- Instalación limpia correcta; suite completa sobre instalación nueva y sobre actualización: 80 pruebas, cero fallos y cero errores en cada ejecución.
- Cuatro escenarios de concurrencia verificados con transacciones independientes: capacidad compartida de recepción, repetición del traslado, preparación simultánea de una devolución y repetición de su asistente.
- La actualización conserva la ubicación personalizada, la referencia RMA y el SAT de un registro creado antes del cambio.
- Evidencias en `C:\odoo18\test`: `purchase_phase4_upgrade_tests.log`, `purchase_phase4_clean_install.log`, `purchase_phase4_clean_verified.log` y `purchase_phase4_concurrency.log`.
- En `test2`, la actualización nativa de `wex_purchase_list` queda programada (`to upgrade`). El servicio sigue con `18.0.1.2.0` hasta reiniciarlo; la página de acceso responde HTTP 200. El reinicio no se ha podido ejecutar desde esta sesión y la revisión visual del flujo nuevo queda pendiente tras activarlo.
