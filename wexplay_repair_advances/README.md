# Wexplay SAT Advances

Versión funcional: **18.0.1.0.4**. Odoo 18 Community.

Estado a 18/10/2026: pruebas automáticas superadas y funcionamiento confirmado
por el usuario en su entorno de pruebas. Pendiente de prueba en producción.

## Objetivo

Recibir dinero a cuenta de un SAT y entregar un recibí sin exigir crear antes el
servicio, presupuesto o precio definitivo. Cuando se conoce el trabajo realizado,
se factura por el circuito habitual y se aplica el pago existente mediante la
conciliación nativa. No se descuenta el anticipo del precio del servicio ni se cobra
dos veces. No se cambia el flujo de exportación ni se añade gestión de gestoría.

## Avisos para el responsable

- Reparación: etiqueta amarilla de anticipo disponible, delante de Cliente Portal
  cuando ambas existen.
- Cotización/pedido: aviso del dinero disponible de sus SAT.
- Factura: aviso del anticipo SAT pendiente de aplicar; no aparece en facturas
  saldadas, canceladas ni en abonos.
- El importe se actualiza al aplicar o devolver el dinero. Si se deshace la
  conciliación, el disponible vuelve a aparecer al recargar el documento.
- Si hay varios SAT con saldo, el aviso lo indica y ofrece el desglose al pasar
  el ratón. La aplicación desde nuestro botón sigue limitada a un SAT por factura.

Los avisos requieren permisos de facturación. Registrar y aplicar anticipos exige
además el grupo `SAT: gestionar anticipos`, que debe asignarse expresamente.

## Prueba funcional

1. Instalar `wexplay_repair_advances` en una base de pruebas.
2. Se usan los diarios de banco, caja y tarjeta de crédito compatibles existentes. Opcionalmente limitar
   la selección en Ajustes > Anticipos SAT. Configurar sus medios de entrada
   y cuentas de cobros pendientes según la contabilidad de la compañía.
3. Asignar al usuario permisos de facturación y `SAT: gestionar anticipos`.
4. Abrir un SAT con cliente, sin servicio ni presupuesto. En la barra inferior,
   Anticipos > Registrar anticipo: introducir 20 €, diario y medio, y confirmar.
5. Desde el pago, imprimir el resguardo PDF. Volver al SAT y comprobar el disponible.
6. Preparar el servicio y la factura por el circuito habitual. Contabilizarla.
7. Pulsar Aplicar anticipos SAT. Una factura de 80 € conserva su total y queda
   pendiente de 60 €. Registrar esos 60 € con el asistente habitual.
8. Probar también varios anticipos, un exceso sobre el total y una devolución.

Para impresión directa instalar también `wexplay_repair_advances_print`; comprobar
la impresora térmica legacy o configurar una asignación para `sat_advance_receipt`.
La impresión física requiere QZ y prueba sobre la impresora real.

La acción Devolver disponible abre el asistente nativo para transferir dinero al
cliente. Revisar siempre sentido, importe y medio. Solo responsables contables.

## Ejemplos de cierre

| Situación | Factura | Resultado tras aplicar el anticipo |
| --- | --- | --- |
| Anticipo de 10 €, reparación de 25 € | Servicio completo: 25 € | Pendiente: 15 € |
| Anticipo de 20 €, dispositivo mojado no reparable con diagnóstico cobrado | Diagnóstico/presupuesto: 20 € | Pendiente: 0 € |
| Anticipo de 100 €, servicio de 80 € | Servicio completo: 80 € | Factura saldada y 20 € disponibles en el SAT |

No poder reparar no implica devolver automáticamente el dinero: el técnico decide
el servicio realmente prestado y lo factura por el procedimiento existente.

## Resguardo y controles

El resguardo QWeb es térmico, de 80 × 170 mm, con fecha española, importe destacado,
cliente, SAT, dispositivo, diario, medio y concepto. Declara UTF-8 para acentos y
euro. Puede generarse de nuevo desde el pago. No se archiva en DMS.

`Marcar como enviado` se oculta en los anticipos SAT. El estado nativo En proceso
no impide que un pago contabilizado tenga saldo disponible; no debe cambiarse
manualmente solo para aplicar el anticipo.

El aviso nativo de créditos pendientes es general del cliente. `Aplicar anticipos
SAT` selecciona los pagos de la reparación concreta; usar este botón evita elegir
por error un crédito de otra reparación.

## Puesta en producción

1. Preparar una copia recuperable de la base y del filestore, según el procedimiento
   habitual de despliegue, y desplegar juntos los cambios relacionados.
2. Reiniciar Odoo y actualizar `wexplay_repair_advances` y, si se usa QZ,
   `wexplay_repair_advances_print`. Actualizar la lista de aplicaciones si es una
   instalación nueva. No se ha automatizado el despliegue desde este trabajo.
3. Incluir los cambios acompañantes: orden de carga corregido en
   `wexplay_sat_print/__manifest__.py` y helper opcional en
   `wexplay_repair_delivery/models/repair_order.py`. Reiniciar carga el código Python.
4. Revisar permisos, diarios, medios de entrada, moneda y configuración de QZ de
   la compañía real. La restricción de diarios en Ajustes es opcional.
5. Recargar el navegador con Ctrl + F5. Verificar las etiquetas y el panel.
6. En el primer caso real supervisado, comprobar referencia SAT, recibí, importe
   disponible, total íntegro de factura, aplicación y cobro restante. No crear
   cobros ficticios en producción para comprobar la interfaz.
7. Comprobar la impresión en la térmica real y anotar cualquier incidencia antes
   de extender el uso al resto de responsables.

Si se interrumpe la prueba, los pagos confirmados deben conservarse y resolverse
por las operaciones nativas. No borrar registros, resetearlos a borrador ni
desinstalar el módulo como forma de deshacer cobros. El circuito habitual de
facturación sigue disponible; revisar y aplicar los pagos ya recibidos antes de
cobrar de nuevo.

## Documentación

- [Arquitectura y decisiones](ARCHITECTURE.md).
- [Resultados y pendientes de validación](TESTING.md).
- [Historial del módulo](CHANGELOG.md).
- [Integración opcional de impresión](../wexplay_repair_advances_print/README.md).

## Límites

Este módulo registra pagos reales, no facturas de anticipo automáticas. El recibí
no sustituye una factura exigible. El circuito documental debe validarse antes del
uso en producción; no combinar la aplicación del pago con la deducción del mismo
importe como anticipo facturado. Ver ARCHITECTURE.md.
