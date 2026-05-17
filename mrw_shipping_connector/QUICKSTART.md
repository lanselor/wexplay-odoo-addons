# MRW Connector Quickstart

This guide validates the connector without relying on any Wexplay-specific
module.

## 1. Install

Install or update `mrw_shipping_connector` from Odoo Apps.

Required standard Odoo modules:

- `delivery`
- `stock_delivery`

## 2. Configure MRW

Go to:

```text
Envíos MRW > Configuración > Configuraciones MRW
```

Create or edit a configuration:

- Entorno: `Pruebas`
- URL WSDL pruebas: `https://sagec-test.mrw.es/MRWEnvio.asmx?WSDL`
- URL WSDL producción: `https://sagec.mrw.es/MRWEnvio.asmx?WSDL`
- Código de franquicia
- Código de abonado
- Código de departamento, if any
- Usuario
- Contraseña
- Servicio nacional por defecto
- Servicio internacional por defecto, if needed

Use:

- `Probar conexión`
- `Inspeccionar WSDL`

These actions do not create shipments.

## 3. Configure Delivery Carrier

Go to Odoo delivery methods and create a carrier:

- Proveedor: `MRW`
- Configuración MRW: your MRW configuration
- Servicio MRW: for example `Bag 19`
- Obtener etiqueta MRW al enviar: enabled for normal TEST validation

The delivery price comes from the Odoo delivery product. No MRW rating API has
been confirmed. If MRW invoice cost depends on mileage or account-specific
billing, keep the Odoo carrier price as an estimate or commercial charge.

## 4. Test National Shipment

Use an outgoing delivery order:

```text
Inventario > Operaciones > Entregas
```

Requirements:

- Type is an outgoing delivery order.
- Destination is a customer.
- Carrier is an MRW delivery method.
- Delivery address has street, ZIP, city, country, and phone.
- Shipping weight is greater than zero.

Validate the picking, then use Odoo's standard `Send to Shipper` action.

Expected result:

- Odoo tracking reference is filled with MRW `NumeroEnvio`.
- A linked `Envío MRW` audit record is created.
- The MRW label is attached to the delivery order when enabled.
- Admin users can inspect sanitized technical logs.

## 5. Label Retry

If MRW created the shipment but the label was not retrieved, use:

```text
Obtener etiqueta MRW
```

from the delivery order.

## 6. Cancellation

Use:

```text
Previsualizar cancelación MRW
Solicitar cancelación MRW
```

MRW may reject cancellation with messages such as:

```text
1) El estado del pedido ya no permite cancelaciones
```

In that case Odoo keeps the existing tracking reference and stores the MRW
message.

## 7. International

International operations are disabled by default.

Enable `Permitir envíos internacionales` only when ready to validate a real TEST
international destination with MRW.
