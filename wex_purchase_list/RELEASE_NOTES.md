# Devoluciones a proveedor — cambios consolidados

Versión actual: **18.0.1.5.0**, Odoo 18 Community. Documentado el **01/11/2026**. El usuario ha validado el funcionamiento probado y comienza la observación en el trabajo diario. No se da por concluida una validación prolongada ni se presupone un despliegue de producción.

## Problema resuelto

Las piezas usadas para comprobar averías o recuperar datos podían devolverse físicamente al proveedor sin registrar la salida en Odoo. Suprimirlas del SAT o de la lista de compra no corregía las existencias. El módulo incorpora el apartado físico, la preparación del envío y su validación con trazabilidad hacia la compra, recepción, SAT o venta originales.

## Evolución de versiones

| Versión | Cambios |
| --- | --- |
| 18.0.1.1.0 | Configuración por compañía, creación de ubicación de devoluciones y base de trazabilidad con recepción validada. |
| 18.0.1.2.0 | Apartado mediante traslado interno, confirmación de retirada del origen, controles de reservas, lotes, cantidades, permisos y concurrencia. |
| 18.0.1.3.0 | Menú Devoluciones, selección múltiple, RMA individual o común y preparación de devoluciones nativas con parciales y documentos históricos. |
| 18.0.1.4.0 | Cierre de revisión, referencias históricas SAT/venta, protección de configuración al actualizar y corrección de avisos de recepción sobre envíos de devolución. |
| 18.0.1.4.1 | Reorganización de la ventana de preparación, resumen de cantidades, bloqueo destacado y detalles plegables. |
| 18.0.1.4.2 | Corrección del fallo OWL por `len()` en visibilidad: decisiones calculadas en Python y consumidas como booleanos en la vista. |
| 18.0.1.4.3 | Reutilización de tipografía, cabeceras, paneles e iconos de Lista de la compra y Reservas. |
| 18.0.1.5.0 | Motivos de devolución, nueva solicitud opcional de repuesto SAT y resoluciones excepcionales sin envío. |

## Circuito habitual de devolución

1. Abrir Devolver a proveedor desde la línea de compra o la pieza SAT vinculada. Solo se admiten recepciones de proveedor validadas y correspondientes al producto y compra.
2. Revisar cantidad, recepción, ubicación física y lote/serie cuando corresponda. Indicar motivo y, opcionalmente, RMA del proveedor.
3. Si hay que retirar o reducir una asignación SAT/venta, revisar el documento y el resumen de cantidades y marcar la confirmación explícita. La facturación, entregas realizadas, piezas utilizadas o bloqueos existentes se resuelven desde sus documentos; no se cancelan pedidos ni se pasan a borrador automáticamente.
4. Apartar para devolución realiza un traslado interno y deja las unidades pendientes de envío. El técnico separa físicamente las piezas de forma coherente con ese traslado.
5. En Lista de compra > Devoluciones, seleccionar piezas y crear los documentos de devolución. La agrupación respeta recepción y ubicación; no fuerza un único documento para compras distintas.
6. Cuando salga la caja físicamente, validar los documentos nativos de Odoo. Preparar el envío y validar su salida son operaciones distintas.

| Momento, con dos unidades recibidas y una destinada a devolución | Stock habitual | Zona de devoluciones | Total físico interno |
| --- | ---: | ---: | ---: |
| Recepción | 2 | 0 | 2 |
| Apartado | 1 | 1 | 2 |
| Envío preparado | 1 | 1 reservada para el envío | 2 |
| Salida validada | 1 | 0 | 1 |

La ubicación de devoluciones se crea al instalar/actualizar para las compañías que no tengan una selección. Puede sustituirse desde configuración, sin referencias operativas hardcodeadas ni sobrescritura de elecciones existentes. Se mantiene fuera del suministro habitual de almacenes y reparaciones. Las cajas por proveedor siguen siendo una organización física del taller, sin imponer una ubicación distinta por cada proveedor.

## Referencia RMA y motivos

El RMA externo es opcional e independiente del número de devolución de Odoo. Puede asignarse por devolución o en conjunto a piezas de la misma compañía y proveedor comercial. Una misma referencia puede relacionar varios documentos nativos. No acredita aceptación por el proveedor ni sustituye su gestión web.

El motivo se registra por devolución, aunque varias piezas compartan envío o RMA:

| Motivo | Observaciones |
| --- | --- |
| No utilizado / ya no necesario | Opcionales. |
| Defectuoso | Opcionales. |
| Referencia incorrecta | Opcionales. |
| Dañado al recibir | Opcionales. |
| Otro | Obligatorias. |

Los motivos pueden consultarse y agruparse en el listado. No se inventan motivos para registros antiguos ni se impide enviar una devolución antigua por carecer de este dato. No se ha añadido una función específica de fotografías o pruebas del defecto en esta entrega.

## Solicitar otra pieza para el SAT

La opción Añadir nuevamente el repuesto al SAT y solicitarlo está desmarcada por defecto y permite revisar cantidad. Solo se ofrece si el SAT no está Finalizado ni Entregado. Esa condición gobierna la nueva solicitud; no añade una prohibición de devolución a los controles anteriores.

Al confirmarla se crea una pieza SAT nueva, sin reutilizar la retirada, y una solicitud independiente pendiente en Purchase List con el proveedor original. No se suma a una compra ya pedida, no genera automáticamente una orden de compra y no reabre la reparación. La retirada y la nueva solicitud se confirman juntas; si una falla, se revierten ambas. Repetir el mismo asistente no duplica solicitudes.

## Resolver sin enviar: excepción opcional

Esta acción se usa cuando la pieza se apartó por error, cambia la decisión o finalmente no puede enviarse. No se exige para preparar ni enviar una devolución habitual. Permite resolver cantidades parciales y exige explicar la decisión.

| Decisión | Resultado |
| --- | --- |
| Recuperar para uso | Traslado interno a un destino disponible seleccionado. El material queda utilizable en otro SAT o venta mediante el flujo normal, sin restaurar la asignación original ni imponer restricciones permanentes. |
| Conservar para revisión | Anotación histórica; la pieza permanece apartada y pendiente. No resta cantidades ni bloquea un envío posterior. |
| Desechar | Preparación de un `stock.scrap` en borrador para revisión y confirmación nativa. Las unidades solo cuentan como desechadas al realizarse el documento. |

Los borradores de desecho no bloquean el envío. Al validarlos se vuelven a comprobar cantidades, identidad y stock libre, de modo que no puedan desechar unidades ya enviadas o recuperadas. No se fuerza stock negativo ni se activa reaprovisionamiento automático.

Las reservas activas de envíos u otras operaciones se respetan; no se liberan silenciosamente. Una pieza ya enviada requiere registrar su regreso nativo y comprobar su ubicación física antes de recuperarla o desecharla. La reversión nativa de una recuperación conserva sus referencias y comprueba que la capacidad de recepción no esté ya comprometida de nuevo.

El historial guarda decisión, cantidad, explicación, usuario, fecha y documentos. El listado distingue enviadas, recuperadas, desechadas y pendientes. Los estados cubren gestión parcial, resuelta sin envío y cierre mixto, además de los estados habituales de devolución. Recuperar libera la capacidad de apartamiento correspondiente; desechar no convierte unidades destruidas en disponibles.

## Seguridad, integridad y mantenimiento

- Los responsables de Purchase List gestionan apartados, documentos, RMA y resoluciones; los usuarios de consulta conservan acceso de lectura según sus permisos. Inventario y edición de SAT/ventas mantienen sus permisos nativos.
- Las trazas y resoluciones se separan por compañía mediante reglas de registro y validaciones de relaciones.
- No se sustituyen `stock.picking`, `stock.move` ni `stock.scrap`; los modelos auxiliares conservan trazabilidad y decisiones operativas.
- Se preservan lotes/series, unidades de medida, documentos parciales, cancelaciones y referencias históricas de SAT/venta.
- Se evitan duplicados por reintentos y se resuelven carreras mediante bloqueos y reintento transaccional nativo.
- Los envíos al proveedor no disparan avisos de llegada de otras piezas. Los avisos al cliente ya registrados no se borran; el apartado completo evita nuevos avisos de disponibilidad sobre esas unidades.
- El CSS específico de la modal se limita a distribución y adaptación; reutiliza los estilos comunes del módulo y no añade una aplicación frontend paralela.

## Validación y siguientes comprobaciones

Se han superado 111 pruebas, diez escenarios de concurrencia y 221184 evaluaciones de modificadores con el JavaScript nativo de Odoo. También se han comprobado instalación limpia, actualización y conservación de configuración e historial anteriores. Las instrucciones y evidencias están en `VALIDATION.md`.

El usuario confirma funcionamiento correcto. Durante el uso diario se observarán correspondencia entre cajas y existencias, lotes/series, RMA, envíos parciales, confirmaciones de salida, solicitudes nuevas y resoluciones excepcionales. Esta observación no incorpora nuevos pasos obligatorios ni automatismos.

## Fuera de alcance y deuda técnica

- Sin conexión con las webs de proveedores: registrar la devolución o el RMA allí sigue siendo responsabilidad operativa del equipo. Odoo conserva su propia trazabilidad.
- La salida de stock no acredita aceptación del proveedor, abono ni cierre económico. No se automatizan abonos, recogidas, transportistas o plazos.
- El circuito completo de RMA con sustitución permanece como deuda: seguimiento del reemplazo, su recepción e identidad y su relación con la pieza enviada y el SAT pendiente. Solicitar una pieza nueva en Purchase List no implementa ese circuito.
- Se conservan las deudas previas del módulo descritas en `ARCHITECTURE.md`; esta entrega no supone una reorganización general de compras, pricing o seguridad histórica.
