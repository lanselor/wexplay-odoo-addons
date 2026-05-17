# MRW API Findings

This document records only the API evidence extracted from the legacy MRW
PrestaShop module located at:

```text
C:\Users\Alex\Downloads\mrwcarrier
```

Operational installation guide reviewed:

```text
C:\Users\Alex\Downloads\modulo-para-Prestashop-MRW.pdf
```

Notes extracted from that guide are documented in
`MRW_PRESTASHOP_GUIDE_NOTES.md`. The guide is used only as supporting
operational evidence; it is not treated as an API contract.

The legacy module is used only as a source of API evidence. Its PrestaShop
workflow, database tables, and UI behavior must not be copied into Odoo.

## Protocol

The integration uses SOAP/XML through PHP `SoapClient`.

Evidence:

- `mrwcarrier.php` header says the module manages SOAP connections with MRW
  SAGEC webservice.
- `new SoapClient(...)` is used for shipments and labels.

No REST or JSON API usage was found.

## WSDL URLs found

Main WSDL URLs found in active flows:

```text
TEST: https://sagec-test.mrw.es/MRWEnvio.asmx?WSDL
PROD: https://sagec.mrw.es/MRWEnvio.asmx?WSDL
```

Older/auxiliary code paths also contain `http://` variants, especially in mass
label helpers. The primary design should use HTTPS URLs but keep WSDL URLs
configurable.

## SOAP namespace

SOAP header namespace used by the legacy module:

```text
http://www.mrw.es/
```

Header name:

```text
AuthInfo
```

## Authentication

Authentication is sent in the SOAP header, not in the SOAP body or query string.

Header structure found:

```php
array(
    'CodigoFranquicia' => $rowSubscriber['agency'],
    'CodigoAbonado' => $rowSubscriber['subscriber'],
    'CodigoDepartamento' => $rowSubscriber['department'],
    'UserName' => $rowSubscriber['user'],
    'Password' => $rowSubscriber['password'],
)
```

Odoo mapping:

| MRW field | Odoo config field |
| --- | --- |
| `CodigoFranquicia` | `agency_code` |
| `CodigoAbonado` | `subscriber_code` |
| `CodigoDepartamento` | `department_code` |
| `UserName` | `username` |
| `Password` | `password` |

## Shipment operations

## WSDL operations confirmed from Odoo inspection

The Odoo connector can now inspect the configured WSDL without calling any MRW
business operation. The test WSDL inspection found these SOAP operations:

| Operation | SOAP action | Input | Output |
| --- | --- | --- | --- |
| `CancelarEnvio` | `http://www.mrw.es/CancelarEnvio` | `tns:CancelarEnvioSoapIn` | `tns:CancelarEnvioSoapOut` |
| `EtiquetaEnvio` | `http://www.mrw.es/GetEtiquetaEnvio` | `tns:GetEtiquetaEnvioSoapIn` | `tns:GetEtiquetaEnvioSoapOut` |
| `EtiquetaEnvioInternacional` | `http://www.mrw.es/GetEtiquetaEnvioInternacional` | `tns:GetEtiquetaEnvioInternacionalSoapIn` | `tns:GetEtiquetaEnvioInternacionalSoapOut` |
| `GetPointsByCP` | `http://www.mrw.es/GetPointsByCP` | `tns:GetPointsByCPSoapIn` | `tns:GetPointsByCPSoapOut` |
| `PointsDB` | `http://www.mrw.es/GetPointsDB` | `tns:GetPointsDBSoapIn` | `tns:GetPointsDBSoapOut` |
| `TransmEnvio` | `http://www.mrw.es/TransmEnvio` | `tns:TransmEnvioSoapIn` | `tns:TransmEnvioSoapOut` |
| `TransmEnvioEC` | `http://www.mrw.es/TransmEnvioEC` | `tns:TransmEnvioECSoapIn` | `tns:TransmEnvioECSoapOut` |
| `TransmEnvioInternacional` | `http://www.mrw.es/TransmEnvioInternacional` | `tns:TransmEnvioInternacionalSoapIn` | `tns:TransmEnvioInternacionalSoapOut` |
| `TransmitirEnvio` | `http://www.mrw.es/TransmitirEnvio` | `tns:TransmitirEnvioSoapIn` | `tns:TransmitirEnvioSoapOut` |
| `TransmitirEnvioEC` | `http://www.mrw.es/TransmitirEnvioEC` | `tns:TransmitirEnvioECSoapIn` | `tns:TransmitirEnvioECSoapOut` |

Important: WSDL operation existence does not prove the request body structure.
Only the operations also found in the legacy module are currently mapped.

### National shipment

SOAP method:

```text
TransmEnvio
```

SOAP action confirmed from WSDL:

```text
http://www.mrw.es/TransmEnvio
```

Request root:

```php
array(
    'request' => array(...)
)
```

Main request nodes found:

```text
request
  DatosEntrega
    Direccion
      CodigoDireccion
      CodigoTipoVia
      Via
      Numero
      Resto
      CodigoPostal
      Poblacion
      CodigoPais
    Nif
    Nombre
    Telefono
    Contacto
    ALaAtencionDe
    Horario
      Rangos
        HorarioRangoRequest
          Desde
          Hasta
    Observaciones
  DatosServicio
    Fecha
    Referencia
    EnFranquicia
    CodigoServicio
    DescripcionServicio
    Bultos
    NumeroBultos
    Peso
    EntregaSabado
    Retorno
    Reembolso
    ImporteReembolso
    Notificaciones
    TramoHorario
```

Optional pickup/warehouse evidence:

```text
request
  DatosRecogida
  DatosEntrega
  DatosServicio
```

This exists in the legacy module, but should not become a stock dependency in
the base Odoo connector.

Additional WSDL inspection confirms that `TransmEnvioRequest` declares:

```text
ModificaDatosEnvio
DatosRecogida
DatosEntrega
DatosServicio
```

Odoo uses this confirmed structure for manual national customer pickup requests:

- `DatosRecogida`: customer address where MRW should collect the item.
- `DatosEntrega`: configured company address where MRW should deliver it.
- `DatosServicio`: same national service data used for outbound shipments.

This is implemented through `TransmEnvio`, not through `TransmEnvioEC`, because
the legacy PrestaShop module did not provide evidence of an EC pickup flow.
International pickup remains disabled until validated with MRW.

Response fields used:

```text
TransmEnvioResult.Estado
TransmEnvioResult.Mensaje
TransmEnvioResult.NumeroSolicitud
TransmEnvioResult.NumeroEnvio
```

Additional field observed in live TEST response:

```text
TransmEnvioResult.Url
```

Observed behavior:

- `Estado == 1`: accepted/success.
- `Estado == 0`: rejected/error.
- Live TEST response can adjust the effective pickup date in `Mensaje`; example:
  `La fecha de recogida se cambió a 05/05/2026`.

Odoo stores the last date found in that MRW message as
`mrw_effective_shipping_date` and uses it for label requests.

### International shipment

SOAP method:

```text
TransmEnvioInternacional
```

International address request nodes differ from national:

```text
Direccion
  Direccion
  CodigoPostal
  Poblacion
  Estado
  CodigoPais
```

International service nodes found:

```text
DatosServicio
  Fecha
  Referencia
  CodigoServicio
  DescripcionServicio
  Bultos
  NumeroBultos
  Peso
  NotificacionSMS
```

Response fields used:

```text
TransmEnvioInternacionalResult.Estado
TransmEnvioInternacionalResult.Mensaje
TransmEnvioInternacionalResult.NumeroSolicitud
TransmEnvioInternacionalResult.NumeroEnvio
```

## Label operations

### National label

SOAP method:

```text
EtiquetaEnvio
```

WSDL detail:

- Binding operation name: `EtiquetaEnvio`
- SOAP action: `http://www.mrw.es/GetEtiquetaEnvio`
- Input message: `tns:GetEtiquetaEnvioSoapIn`
- Input XML element: `tns:GetEtiquetaEnvio`

Request:

```text
request
  NumeroEnvio
  NumerosEtiqueta
  SeparadorNumerosEnvio
  FechaInicioEnvio
  FechaFinEnvio
  TipoEtiquetaEnvio
  ReportTopMargin
  ReportLeftMargin
```

Defaults found:

```text
TipoEtiquetaEnvio: 0
ReportTopMargin: 1100
ReportLeftMargin: 650
```

Important live TEST observation:

- Requesting the label with the original requested shipping date after MRW had
  changed the pickup date caused a SOAP fault:
  `Object reference not set to an instance of an object`.
- The connector should use `mrw_effective_shipping_date` when MRW returned one
  during shipment creation.
- Sending the SOAP body wrapper as `EtiquetaEnvio` caused the same SOAP fault.
  WSDL evidence shows the request wrapper element must be `GetEtiquetaEnvio`.
- After switching to `GetEtiquetaEnvio`, live TEST returned `Estado = 1` and
  `EtiquetaFile`.

Response fields used:

```text
GetEtiquetaEnvioResult.Estado
GetEtiquetaEnvioResult.Mensaje
GetEtiquetaEnvioResult.EtiquetaFile
```

### International label

SOAP method:

```text
EtiquetaEnvioInternacional
```

Request fields are the same as national label.

Defaults found:

```text
TipoEtiquetaEnvio: 0
ReportTopMargin: 20
ReportLeftMargin: 20
```

Response fields used:

```text
GetEtiquetaEnvioInternacionalResult.Estado
GetEtiquetaEnvioInternacionalResult.Mensaje
GetEtiquetaEnvioInternacionalResult.EtiquetaFile
```

## Label payload handling

The legacy module writes `EtiquetaFile` directly to a `.pdf` file using
`file_put_contents`.

Important detail:

- Some variable names/comments call the value base64 encoded.
- The actual PHP code found does not call `base64_decode`.

Conclusion for Odoo:

- Do not assume only one format until tested.
- Implement flexible label payload handling later:
  - if payload is a PDF binary/string, store as PDF directly;
  - if payload is base64, decode before attachment storage.

Expected Odoo storage:

- `ir.attachment`
- `mimetype = application/pdf`
- linked to `mrw.shipping.shipment`
- technical logs mask `EtiquetaFile` to avoid storing large label payloads

Live TEST validation:

- MRW shipment `01400F001137` generated attachment `01400F001137.pdf`.
- Downloaded PDF size observed locally: 175034 bytes.
- The user confirmed the PDF opens correctly.
- Odoo can now open or download the stored label attachment from the shipment.

## Services

No SOAP operation was found to fetch available MRW services.

The legacy module uses local service definitions and sends the selected
`CodigoServicio` in the shipment request.

Services found in the legacy PrestaShop module:

| Code | Name | Type |
| --- | --- | --- |
| `0000` | Urgente 10 | national |
| `0015` | Urgente 10 Expedicion | national |
| `0100` | Urgente 12 | national |
| `0110` | Urgente 14 | national |
| `0115` | Urgente 14 Expedicion | national |
| `0200` | Urgente 19 | national |
| `0205` | Urgente 19 Expedicion | national |
| `0220` | Urgente 19 Portugal | national |
| `0230` | Bag 19 | national |
| `0235` | Bag 14 | national |
| `0300` | Economico | national |
| `0350` | Economico Interinsular | national |
| `0800` | eCommerce | national |
| `0810` | eCommerce Canje | national |
| `0370` | Maritimo Baleares | national |
| `0385` | Maritimo Canarias | national |
| `0390` | Maritimo Interinsular | national |
| `BOX25` | Ecobox 25 | international |
| `DOC` | Documentos | international |
| `ECOMM` | Ecommerce | international |
| `ECOP` | Economy | international |
| `EURO2` | Euro 2 Kg | international |
| `PAC` | Paquetes | international |
| `SC` | SuperCity | international |

Services are data records in Odoo, not Python hardcodes. This catalog is a
convenience preload from PrestaShop, not proof that every service is enabled on
every MRW account.

## Packages

Package/bulto fields found:

```text
BultoRequest
  Alto
  Largo
  Ancho
  Dimension
  Referencia
  Peso
```

Other shipment-level package fields:

```text
NumeroBultos
Peso
Bultos
```

The legacy module uses `Dimension = 3` in generated package lines. The exact MRW
meaning of `3` was not found in the code.

## Phone formatting

No explicit MRW phone-format rule was found in the PrestaShop code or WSDL
inspection.

Current Odoo preview rule, pending real MRW validation:

- Spanish national shipment to `ESP`: normalize `+34XXXXXXXXX`,
  `0034XXXXXXXXX`, or `34XXXXXXXXX` to the 9-digit Spanish national number.
- International shipment: preserve the international prefix after removing
  spaces and common punctuation.

This rule is intentionally limited to preview/request mapping and should be
revisited after the first real non-production submission.

## Notifications

National notifications use:

```text
Notificaciones
  NotificacionRequest
    CanalNotificacion
    TipoNotificacion
    MailSMS
```

International notification evidence:

```text
NotificacionSMS
  TelefonoSMS
```

Notification support should be deferred or implemented conservatively after the
core shipment and label flows are stable.

## Tracking

No SOAP tracking method was found.

The legacy module stores `NumeroEnvio` as the tracking number in PrestaShop and
has a public tracking URL template:

```text
http://www.mrw.es/seguimiento_envios/MRW_historico_nacional.asp?enviament=@
```

For the Odoo MVP, tracking remains private and only the MRW number is stored.

## Cancellation

No real MRW cancellation SOAP method was found in the legacy module.

The live WSDL confirms this operation:

```text
Operation: CancelarEnvio
SOAP action: http://www.mrw.es/CancelarEnvio
Input message: tns:CancelarEnvioSoapIn
Output message: tns:CancelarEnvioSoapOut
Input XML element: tns:CancelarEnvio
```

WSDL request structure:

```text
request
  CancelaEnvio
    NumeroEnvioOriginal
```

WSDL response structure:

```text
CancelarEnvioResult
  Estado
  Mensaje
  NumeroSolicitud
  NumeroEnvio
```

Odoo can preview this cancellation request offline and execute it only for TEST
configurations. A shipment must only reach `cancelled` when MRW returns
`Estado = 1`.

Live TEST rejection observed:

```text
Estado: 0
Mensaje: 1) El estado del pedido ya no permite cancelaciones
NumeroEnvio: 01400F001137
```

This means the request structure and operation are valid, but MRW rejected the
cancellation for business-state reasons. Odoo should keep the previous shipment
state and store the message in logs/`last_error`.

Internal states can be prepared:

```text
cancel_pending
cancelled
```

External cancellation is implemented only for TEST configurations until a
production enablement decision is made.

## Error handling

Error pattern found:

```text
Estado == 0
Mensaje contains the human-readable error
```

Success pattern found:

```text
Estado == 1
Mensaje contains the service message
```

Real error observed in legacy log:

```text
1) El usuario especificado no dispone de acceso al sistema, consulte con su franquicia.
```

No stable catalog of MRW error codes was found.

## Unknowns

Still not confirmed:

- Full WSDL schema.
- Whether `EtiquetaFile` is always base64 PDF or may sometimes be direct PDF.
- Real service listing method.
- Real tracking API method.
- Meaning of `Dimension = 3`.
