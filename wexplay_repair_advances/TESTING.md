# Validación de la primera versión

Fecha: 18/10/2026.

Base aislada: `wex_advances_test_20261018`. No se han modificado datos de producción.
Runtime: Odoo 18.0.20260220 instalado localmente.

Instalados el módulo principal, la integración opcional de impresión y el módulo
de entrega con sus dependencias. Instalación y actualización de las nuevas vistas
y reportes completadas. Python y XML validados.

Resultado actualizado: 25 pruebas, 0 fallos y 0 errores.

Correcciones posteriores: acciones de ventana con `views` explícito para el
cliente web; selección automática de diarios existentes cuando no hay restricción
configurada y actualización de medios de entrada al cambiar el diario.
Se incluyen diarios nativos de tipo `credit` en el selector, los ajustes y la
validación del registro. Probados el cobro y la aplicación a factura con un diario
de tarjeta de crédito, y su selección explícita como diario permitido.

Casos cubiertos:

- Cobro sin pedido ni servicio; reintento del mismo asistente sin duplicar pago.
- Aplicación de 20 a factura de 80: total intacto y residual 60.
- Varios anticipos y cobro final con `account.payment.register`.
- Exceso sobre factura y recuperación de disponible al deshacer conciliación.
- Separación entre SAT del mismo cliente.
- Rechazo de importes no positivos y diarios no autorizados.
- Rechazo de cliente o compañía incompatibles.
- Bloqueo de cambios de cliente e importe después de confirmar.
- Bloqueo de eliminación de pagos confirmados y aplicación a factura borrador.
- Restricción de permisos del operador.
- Render HTML del resguardo.
- Devolución efectiva usando el asistente nativo y rechazo si ya está aplicado.
- Anticipo total: oferta del asistente de entrega sin entregar automáticamente.

## Validación funcional comunicada por el usuario

El 18/10/2026 el usuario confirmó que las pruebas realizadas funcionan y que los
avisos recién incorporados se muestran correctamente. Se ha observado en las
capturas la generación del pago, la oferta del crédito pendiente en la factura y
el resguardo. Esta confirmación no equivale a una certificación fiscal ni a una
prueba de todos los casos de la suite en el entorno real.

Estado: preparado para prueba supervisada en producción; todavía sin resultados
de producción registrados. No se ha desplegado ni reiniciado producción desde
esta tarea de documentación.

## Pendientes

- Comprobación en producción del panel y de los avisos con permisos de usuarios reales.
- Saltos de página para textos largos e impresión física 80 x 170/QZ en producción.
- Distribución en pantalla estrecha y documentos con varios SAT en el entorno real.
- Dos sesiones concurrentes: se han implementado bloqueos, pero no se ha ejecutado
  una prueba concurrente con dos conexiones.
- Documentación fiscal del anticipo antes del uso en producción.

La suite histórica de workflow no se ha validado: su importación usa SavepointCase,
que no existe en este runtime. Para aislar las pruebas de anticipos se instalaron
primero las dependencias sin tests y después se ejecutó exclusivamente esta suite.

Se corrigió un fallo previo de instalación limpia de `wexplay_sat_print`: sus
reportes deben cargarse antes de la vista que referencia sus identificadores.

Revisión del ticket: eliminado el archivado DMS del módulo y ocultado Marcar como
enviado exclusivamente en anticipos SAT. Ticket rediseñado en blanco y negro,
con UTF-8 explícito y fecha dd/MM/yyyy. PDF generado y revisado visualmente
en base aislada: una página de 80 x 170 mm. Acentos y euro comprobados en muestra.

Avisos de anticipos en SAT, pedido y factura: probados aparición, desaparición al
aplicar o devolver, reaparición al deshacer conciliación, desglose de varios SAT y
ocultación en factura saldada con sobrante en el SAT. Vistas instaladas/actualizadas
en base aislada y sintaxis del widget validada. Pendiente de comprobación visual
en pantalla estrecha. El usuario ha confirmado el funcionamiento de los avisos en
su prueba posterior; no se ha realizado una inspección visual independiente del
navegador desde las herramientas del agente.
