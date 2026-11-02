# Wex Redsys Payments

Odoo 18 Community · versión 18.0.1.1.0 · validado parcialmente con Redsys de pruebas.
Estado documental actualizado el 2026-11-01. No acredita aprobación del banco,
cobros reales ni validación completa de todos los escenarios.

## Alcance
Pago por tarjeta EUR desde enlaces nativos con token de cotizaciones y facturas.
Redirección a Redsys, notificación firmada y procesamiento contable/comercial
nativo. Devoluciones manuales totales y parciales desde el pago original.
Sin captura de tarjetas, tokenización, recurrentes, integración SAT ni cambios
funcionales en el portal B2B. Bizum específico queda fuera aunque la pasarela
pueda mostrarlo por configuración bancaria.

## Configuración
1. Instalar o actualizar el módulo; el proveedor se crea desactivado y sin secretos.
2. Introducir comercio, terminal y clave de firma como administrador. No usar la
   contraseña de Canales como clave de firma. No copiar credenciales a documentos.
3. Elegir Modo de prueba, EUR y tarjeta. Publicar el proveedor para visitantes:
   un administrador puede verlo sin publicar, el cliente anónimo no.
4. Seleccionar diario y cuenta de recibos pendientes. La columna contable está
   restringida por el grupo nativo account.group_account_readonly, no incluido
   automáticamente por el nivel Administrador de Contabilidad en Community.
5. Mantener una URL HTTPS pública y las notificaciones HTTP habilitadas en el TPV.
6. Cotización: activar pago online y porcentaje antes de confirmar. Odoo oculta
   el botón normal de pago de cotización una vez confirmada. Factura: publicar y
   usar el enlace nativo con saldo pendiente; no requiere elegir Redsys en el
   campo Método de pago de Otra información.

## HTTPS y proxy
El usuario acreditó acceso por sat.wexplay.com y www.sat.wexplay.com. Mantener un
host canónico configurado y comprobar las URLs efectivas; con website_payment,
get_base_url prioriza url_root de la petición frente al parámetro web.base.url.
El incidente observado fue HTTPS público interpretado como HTTP por Odoo.
Se resolvió en Nginx Proxy Manager añadiendo una ubicación / hacia el mismo
upstream HTTP 8069 y, en la configuración DE ESA UBICACIÓN:

```nginx
proxy_set_header X-Forwarded-Host $host;
```

Mantener proxy_mode=True y las cabeceras X-Forwarded-Proto correctas. Odoo solo
aplica ProxyFix cuando recibe X-Forwarded-Host. Conservar /websocket hacia 8072.
No cambiar el scheme interno de queue_job ni eliminar la validación HTTPS.
No reproducir cambios de infraestructura automáticamente: verificar cada despliegue.

Rutas generadas por el módulo:
- /payment/wex_redsys/notify: POST firmado de Redsys, sin login del proxy.
- /payment/wex_redsys/return: retorno GET, no confirma dinero.

## Pagos y devoluciones
HMAC_SHA256_V1 fue aceptado por el terminal en pruebas, incluyendo devolución
REST total. Confirmar algoritmo y permisos del terminal de producción con el banco.
Para devoluciones, asignar el grupo específico y responsable contable; consultar
[REFUNDS.md](docs/REFUNDS.md). No generar abonos ni cancelar pedidos automáticamente.
La factura puede aplicar un cobro previo nativo; no cobrarla otra vez si está saldada.
La contabilidad puede permanecer En proceso hasta conciliación bancaria; no forzar estados.

## Seguridad, pruebas y retirada
La clave se restringe en ORM y se oculta en vista; eso no cifra la base ni sus copias.
No se guardan tarjetas ni cuerpos completos de notificación o firmas en los logs del módulo.
Las referencias usan secuencia numérica: no reiniciarla ni compartir rangos entre clones.
Pruebas del agente siempre en base aislada y con datos ficticios. Las pruebas de
sandbox en la instancia operativa fueron realizadas por el usuario; generan
registros contables en Odoo aunque Redsys no mueva dinero real.

Para frenar nuevas operaciones despublicar/desactivar el proveedor; detener el
cron de devoluciones si procede y resolver solicitudes ya enviadas. Conservar
historial financiero. La activación real requiere aprobación bancaria.

## Documentos
- [Arquitectura](ARCHITECTURE.md), [especificación](docs/SPEC.md),
  [plan](docs/IMPLEMENTATION_PLAN.md), [resultados](docs/TEST_RESULTS.md).
- [ADR-001](docs/ADR-001_NATIVE_PROVIDER.md), [ADR-002](docs/ADR-002_REFUNDS.md).

## Licencia
AGPL-3.0-or-later. Adaptación independiente apoyada en la estructura, parámetros
y firma de payment_redsys de OCA/l10n-spain, sin modificar ni depender del checkout
OCA. Referencias: Tecnativa (Sergio Teruel, João Marques), Ignacio Ibeas, Planesnet
(Luis Planes, Laia Espinosa, Raul Solana), OCA y Wexplay.
https://github.com/OCA/l10n-spain/tree/18.0/payment_redsys
https://pagosonline.redsys.es/desarrolladores-inicio/
