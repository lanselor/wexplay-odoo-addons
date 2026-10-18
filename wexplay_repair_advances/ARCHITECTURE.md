# Anticipos SAT — primera versión

## Alcance

Recepción rápida de dinero desde una reparación guardada con cliente, sin exigir
presupuesto, servicio ni precio final. El dinero se registra inmediatamente como
`account.payment` nativo, con su asiento. No existe una bolsa de dinero fuera de
contabilidad ni un estado ficticio que retrase la fecha del cobro.

Esta versión documenta el cobro con un recibí. No implementa la emisión automática
de facturas de anticipo ni acredita que el recibí sustituya una obligación fiscal.
Antes de usarla en producción debe validarse el circuito documental con la asesoría.
No debe combinarse una aplicación directa del pago con la deducción de una factura
de anticipo: son circuitos distintos y se duplicaría su efecto.

## Fuente de verdad y operaciones

- `account.payment.wex_advance_repair_id`: vínculo permanente del cobro con el SAT.
- Disponible: residual negativo de las líneas a cobrar del asiento contabilizado.
- Aplicación: `account.move.line.reconcile()`; no altera precios ni impuestos.
- Facturación y cobro restante: acciones y asistente nativos sin sustitución.
- Devolución del disponible: `account.payment.register` sobre esas líneas. Requiere
  responsable contable; la conciliación nativa deja trazabilidad del reintegro.
- Si el dinero ya se aplicó, no se devuelve desde este botón: primero debe revisarse
  la factura, el abono y la conciliación correspondiente por el circuito contable.
- No se borran anticipos confirmados ni se cambian importe, cliente, compañía,
  fecha, moneda o diario. Las correcciones se hacen por el circuito contable.
- Cancelar el SAT no cancela ni devuelve dinero automáticamente.

Primera versión limitada a moneda de compañía y una reparación inequívoca por
factura. No consume anticipos de otro SAT del mismo cliente. El crédito sigue
siendo visible en la contabilidad nativa del cliente; no se ha modificado el widget
general de créditos de Odoo ni sus permisos.

La aplicación bloquea factura y pagos en orden estable y vuelve a leer residuales.
El registro bloquea su asistente y reutiliza el pago si se reintenta la misma acción.
Una nueva apertura del asistente representa otro cobro: no se deduplica por importe.

## Seguridad y configuración

El grupo `SAT: gestionar anticipos` NO concede permisos de facturación. El usuario
necesita además `account.group_account_invoice` y acceso al SAT. Se conservan ACL
y reglas multiempresa de Odoo; no se usa sudo para crear o aplicar cobros. El único
sudo consulta la existencia de anticipos para bloquear cambios del cliente del SAT
sin revelar importes a usuarios sin acceso contable.

Sin selección en Ajustes se ofrecen los diarios de banco, caja y tarjeta de crédito existentes de la
compañía, con medios de entrada y moneda compatible. Una selección explícita en
Ajustes > Anticipos SAT restringe esa lista. El registro valida
diario, método de entrada, compañía, moneda e importe en servidor. Debe existir un
asiento contabilizado después de confirmar; si no, toda la operación se revierte.

## Interfaz, documentos e integraciones

El panel extiende `web_responsive_app_customizer.RepairFormFooter.Right`; consulta
al abrirse, sin polling. La lógica de negocio vive en Python. Al registrar se abre
el pago para imprimir o revisar con las herramientas nativas.

Avisos amarillos informativos en SAT, cotización/pedido y factura. Todos leen el
residual nativo de los pagos mediante `_get_advance_notice_values()`, sin saldo
duplicado y sin aplicar dinero automáticamente. Desaparecen al consumir o devolver
el disponible y se recalculan si se deshace una conciliación. En facturas saldadas,
anuladas y abonos no se muestra el aviso de importe pendiente de aplicar.

Los avisos respetan permisos de facturación; no elevan acceso a pagos. En documentos
comerciales solo incluyen SAT del mismo cliente comercial y compañía. Cuando hay
varios SAT con saldo se muestra un aviso explícito, con desglose en el tooltip;
esto no habilita la aplicación automática a facturas agrupadas. El widget solo
presenta texto y tooltip. No calcula saldos en JavaScript.

En reparación el aviso comparte el título con Cliente Portal y se sitúa antes en
la cuadrícula, también en pantalla estrecha. La integración de estilos es opcional
y no introduce dependencia de `wexplay_portal` ni modifica su etiqueta.

Resguardo QWeb propio en 80 x 170 mm. PDF sin Wex Print. El módulo opcional
`wexplay_repair_advances_print` añade QZ, reutiliza el paperformat SAT y registra
`sat_advance_receipt` como documento independiente. No cambia perfiles existentes.
Sin asignación piloto usa el fallback térmico legacy del stack.

El módulo no archiva documentos en DMS. El resguardo se genera desde el pago cuando se solicita.

`wexplay_repair_delivery.action_offer_delivery_after_payment()` es un punto de
integración opcional: si existe y la factura queda saldada, valida acceso, relación
única al SAT, pago y condiciones de entrega antes de ofrecer su asistente. No cambia
el estado automáticamente. Sin ese módulo se recarga la factura.

Redsys, portal, envío automático de documentos y facturación fiscal automática
quedan fuera del alcance. No se ha cambiado el flujo de ventas estándar.
