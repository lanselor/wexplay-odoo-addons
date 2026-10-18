# Wex Redsys Payments

Odoo 18 Community. Primera iteración para pagar cotizaciones y facturas mediante
su enlace nativo y redirección al TPV virtual Redsys. Versión 18.0.1.0.0, en pruebas.

## Instalación y configuración

1. Instalar `wex_payment_redsys` y actualizar la lista de aplicaciones si procede.
2. Abrir el proveedor Redsys en la configuración nativa de pagos. Se instala
   desactivado, sin publicar y sin credenciales.
3. Como administrador, introducir comercio, terminal y clave SHA256 facilitados
   por el banco. No introducir aquí las credenciales del portal Canales.
4. Seleccionar **modo prueba**, diario bancario y cuenta de cobros pendientes del
   método de entrada del proveedor. Mantener EUR y tarjeta. Publicar el proveedor
   para que aparezca al abrir el enlace como visitante.
5. Configurar una URL base HTTPS pública estable y el enrutamiento a la base de
   pruebas. La dirección debe funcionar desde fuera de la red del negocio.
6. Confirmar en Canales que está habilitada la notificación HTTP. El módulo envía
   `/payment/wex_redsys/notify` en MerchantURL; el retorno del navegador es
   `/payment/wex_redsys/return`. No deben requerir login del proxy ni sesión Odoo.
7. Enviar una cotización con pago online o una factura publicada mediante Odoo.
   Revisar el ajuste nativo de facturación automática de Ventas antes de probar.

No se han precargado las credenciales del banco. El algoritmo implementado es
HMAC_SHA256_V1, conforme al correo recibido. Su aceptación por el terminal debe
comprobarse; no se cambia automáticamente a SHA512 V2 ni se activa producción.

La secuencia usa prefijo `1000` y ocho dígitos. Antes de compartir un mismo
terminal entre bases clonadas, asignar prefijos numéricos diferentes de cuatro
dígitos o terminales distintos. No reiniciar la secuencia tras realizar pagos.

## Qué verificar

- Transacción nativa en estado realizado y referencia de autorización.
- Pago nativo creado y ligado al documento, sin duplicarlo al repetir notificación.
- Factura conciliada con el cobro; puede quedar «En proceso de pago» hasta la
  conciliación bancaria según el diario. El módulo no fuerza «Pagada».
- Cotización confirmada por las reglas nativas de Ventas.
- Si se cierra el navegador, la tarea nativa de posprocesamiento debe estar activa
  y ejecutarse. La notificación solicita su ejecución; no crea una cola adicional.
- Rechazos y errores visibles en las transacciones; contrastar en Canales.

## Seguridad y límites

Los datos de tarjeta solo se introducen en Redsys. No hay captura, campos de
tarjeta, tokenización, pagos recurrentes ni almacenamiento de metadatos de tarjeta.
Las notificaciones se validan siempre, también en tests. Los mensajes completos
y las firmas no se registran en logs del módulo ni en los logs de renderizado
nativos. La clave se restringe por permisos de campo, además de ocultarse en vista.
Como los secretos de otros proveedores nativos, se almacena en la base de datos;
la máscara visual no es cifrado. Proteger acceso administrativo y copias de BD.

El webhook solo admite POST y devuelve 200 tras una notificación validada. Una
notificación inválida devuelve 400, sin modificar estados. El retorno GET no
confirma cobros. Un fallo interno debe resolverse antes de dar el pago por cerrado.

No se automatizan devoluciones, recuperación de notificaciones perdidas ni
incidencias de dos intentos diferentes cobrados. No hay integración SAT ni cambios
en el portal B2B. Se mantiene la operativa contable y comercial de Odoo.

Rollback: desactivar y despublicar el proveedor. Conservar transacciones y pagos.

## Referencias y licencia

AGPL-3.0-or-later. Adaptación independiente apoyada en la estructura, parámetros
y firma de `payment_redsys` OCA, sin dependencia ni modificación del repositorio:
https://github.com/OCA/l10n-spain/tree/18.0/payment_redsys

Referencia original: Tecnativa (Sergio Teruel, João Marques), Ignacio Ibeas,
Planesnet (Luis Planes, Laia Espinosa, Raul Solana) y Odoo Community Association.
Cambios de integración y seguridad: Wexplay, 2026.

Especificación Redsys: https://pagosonline.redsys.es/desarrolladores-inicio/

Ver ARCHITECTURE.md, docs/SPEC.md, docs/IMPLEMENTATION_PLAN.md y docs/TEST_RESULTS.md.
