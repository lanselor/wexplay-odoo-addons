# Wexplay SAT Advances Print

Integración opcional entre `wexplay_repair_advances` y `wexplay_sat_print`.

## Funcionamiento

Añade Imprimir térmica al pago SAT y usa la acción existente
`wexplay_sat_print.print_report_qz`. El PDF procede del reporte
`wexplay_repair_advances.advance_receipt`. Reutiliza el paperformat SAT 80 × 170 mm.

Registra el documento `sat_advance_receipt`, independiente del ticket de reparación.
No modifica los perfiles ni las asignaciones de otros documentos. Sigue los modos
de resolución y el fallback térmico del stack Wex Print existente.

## Configuración y prueba

1. Instalar después del módulo principal, con Wex Print/QZ operativo.
2. Comprobar la impresora térmica de Legacy o crear una asignación para el documento
   SAT Advance Receipt si se quiere usar la resolución nueva.
3. En Hybrid, probar la asignación concreta con Pilot new resolution antes de
   ampliar su uso. No es necesario cambiar el modo global para este documento.
4. Abrir un pago de anticipo confirmado y pulsar Imprimir térmica.
5. Revisar márgenes, corte, importe, acentos y euro en la impresora real.

Si falla QZ, no volver a registrar el cobro: reintentar solo la impresión o usar
Resguardo 80 × 170 para obtener el PDF. No hay archivado DMS.

El PDF se ha revisado visualmente en pruebas; la validación física en producción
sigue pendiente. Consultar el [manual principal](../wexplay_repair_advances/README.md)
y sus [resultados de pruebas](../wexplay_repair_advances/TESTING.md).
