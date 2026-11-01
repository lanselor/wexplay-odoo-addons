# Devoluciones — 18.0.1.1.0

2026-11-01. Implementación autorizada del plan de devoluciones. Solo tarjeta EUR,
REST tipo 3, firma SHA256 V1. Pendiente de aceptación bancaria en test.

## Uso
Actualizar el módulo y asignar «Redsys: realizar devoluciones» al responsable
contable. Se exigen ambos grupos en servidor. Desde el pago original, abrir el
asistente nativo Reembolsar e indicar el importe total o parcial. La solicitud
crea una transacción hija pendiente; la tarea Redsys la envía después (un envío
por ejecución, intervalo un minuto). No cerrar el proceso interpretando la cola
como una devolución ya realizada. Consultar el estado de la transacción hija.

Las nuevas transacciones fijan entorno, comercio y terminal. Las antiguas no se
rellenan por migración: abrir la transacción original, registrar evidencia de
Canales y pulsar Verify legacy environment. Verificar primero que el entorno
actual del proveedor coincide realmente con la operación original. Esta acción
queda trazada. No basta con que el proveedor esté actualmente en pruebas.

## Respuestas inciertas
La tarea usa cursor propio, bloquea con SKIP LOCKED, marca enviada y confirma
ANTES de contactar con el banco. Timeout, firma inválida, respuesta sin firma o
caída posterior al envío dejan pending/sent. No hay reenvío automático. Un fallo
antes de enviar también puede exigir verificación, por seguridad.

En ese caso consultar Canales/soporte, escribir evidencia en la transacción hija
y usar Bank confirms refunded o Bank confirms NOT refunded. La segunda acción
solo procede si el banco confirma que no se ejecutó NI sigue pendiente. Una
devolución incierta bloquea nuevas solicitudes del mismo cobro. No devolver
directamente en Canales mientras exista una solicitud en cola sin resolver.

## Contabilidad y alcance
Se reutilizan el asistente nativo, saldo disponible, transacciones hijas y pagos
salientes enlazados mediante source_payment_id. No crear notas de crédito ni
desconciliar facturas automáticamente. Si corresponde rectificar, emitir la nota
de crédito y conciliar el pago saliente mediante las herramientas contables
nativas. No se cambia el pedido ni su logística.

Una devolución aceptada se identifica con respuesta firmada 0900, validando
importe, moneda, comercio, terminal, referencia ORIGINAL y tipo 3. La referencia
única interna de la hija no se envía como número de pedido Redsys.

No hay tarjetas, tokenización, nuevos saldos ni cola externa. La ruta pública de
cobros permanece separada. No hay reintento automático ni consulta bancaria
automática. Confirmar con el banco habilitación REST y firma antes de usar real.

## ADR y archivos
Se añade un cron pequeño porque el asistente debe confirmar la solicitud antes
del efecto bancario. No se confirma el cursor de la petición del usuario. Solo
el cursor independiente del despachador establece fronteras de commit.
models/refund.py contiene proveedor, metadatos, validación, envío y resolución;
security/refund_security.xml restringe la acción; views/refund_views.xml permite
verificación; data/refund_cron.xml despacha; tests/test_refund.py cubre el flujo.

## Pruebas y límites
Base aislada wex_redsys_test_20261018; requests al banco simuladas. Comprobar
parcial y saldo restante, rechazo sin pago, límites, entorno, permisos, firma y
datos alterados, resolución con evidencia y timeout sin reenvío. Los tests de
timeout simulan fronteras de commit para compartir fixtures no confirmadas;
no equivalen a una prueba de caída de proceso real ni concurrencia multinodo.
Faltan prueba REST real y aceptación con factura/nota de crédito en el banco test.

Rollback: desactivar el cron para frenar nuevas salidas; conservar solicitudes
y pagos. Resolver operaciones enviadas antes de retirar el código. No borrar
transacciones para liberar un límite ni reutilizar credenciales entre entornos.
