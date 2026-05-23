# Wex Accounting Portal - Architecture

## Objetivo

`wex_accounting_portal` expone un portal financiero de solo lectura para
usuarios externos concretos, sin abrir acceso al backend contable completo.

En esta fase el alcance queda limitado a:

- facturas de venta
- abonos de venta
- facturas de compra
- abonos de proveedor
- ventas POS
- dashboard resumen del periodo
- hero superior con separacion `Ventas / Compras`
- filtros por periodo y rango personalizado
- busqueda por numero, cliente o proveedor, NIF y referencia
- selector de compañia para entornos multi-company
- exportacion CSV
- exportacion XLSX
- descarga individual de PDF de factura
- detalle opcional de lineas en factura y POS
- reporte analitico interno para backend
- tablero en `Tableros` basado en la misma fuente contable

No incluye:

- asientos contables
- diarios
- conciliacion
- chatter
- adjuntos internos

---

## Dependencias reales

Dependencias Odoo:

- `portal`
- `website`
- `account`
- `point_of_sale`

Dependencia Python actual:

- `openpyxl` para generar el export XLSX

Si `openpyxl` no esta disponible en el entorno Python de Odoo, la exportacion
XLSX fallara aunque el modulo instale correctamente.

---

## Decision principal de seguridad

Este modulo no abre permisos ORM generales de lectura sobre `account.move` ni
`pos.order` al usuario portal.

En su lugar:

- el acceso se decide en el controlador
- la validacion se apoya en grupo especifico + flag en `res.partner`
- la lectura real de datos se hace con helpers encapsulados y dominio acotado
- el portal renderiza valores preparados, no objetos backend completos
- los accesos denegados relevantes se registran en log para trazabilidad

Con esto se evita convertir el portal en una puerta lateral al backend
contable.

---

## Condiciones de acceso

Un usuario solo puede entrar si cumple todas:

- es usuario portal
- pertenece al grupo `Wex Accounting Portal`
- su contacto tiene `wex_accounting_portal_enabled = True`

Ademas, la informacion visible se restringe a las compañias permitidas en
`user.company_ids`.

No existe acceso por token ni enlaces publicos.

---

## Dominio funcional visible

### `account.move`

Solo:

- `move_type in ('out_invoice', 'out_refund', 'in_invoice', 'in_refund')`
- `state != 'cancel'`
- `company_id` dentro de las compañias del usuario

### `pos.order`

Solo:

- estados `paid`, `done`, `invoiced`
- `company_id` dentro de las compañias del usuario

---

## Controladores y navegacion

La navegacion principal vive en:

- `/my/accounting`
- `/my/accounting/invoices/<id>`
- `/my/accounting/pos/<id>`
- `/my/accounting/invoices/<id>/pdf`
- `/my/accounting/export/csv`
- `/my/accounting/export/xlsx`

Los breadcrumbs y botones de volver usan una URL base preparada en controlador
para no duplicar rutas en plantilla.

Las URLs de mostrar u ocultar lineas se preparan en modelo para mantener la
plantilla simple.

La portada de `/my/accounting` ya no es solo un listado. Actua como dashboard y
combina:

- hero conmutador entre `Ventas` y `Compras`
- tarjetas de resumen
- filtros por tipo de documento
- busqueda y selector de compañia
- filtros por periodo
- listado detallado del periodo seleccionado

Ademas, el mismo modulo publica una capa interna de analitica para backend:

- modelo `wex.accounting.dashboard.report`
- vistas `list`, `pivot` y `graph`
- un `spreadsheet.dashboard` dentro del grupo `Finance`

Con esto no existe un segundo modulo paralelo para tablero: portal y dashboard
comparten la misma responsabilidad funcional dentro de `wex_accounting_portal`.

---

## Exportaciones

La exportacion unificada se construye desde filas preparadas por controlador.

Reglas actuales:

- CSV y XLSX comparten la misma base de datos exportados
- el XLSX se genera con `openpyxl`
- existe un limite tecnico de `5000` registros por exportacion
- el limite aplica tanto a facturas como a POS dentro de la misma exportacion
- la exportacion respeta el filtro de tipo, el periodo, la compañia y la busqueda
- las columnas exportadas siguen la lectura economica principal del portal

Este limite protege al portal frente a exportaciones demasiado pesadas en una
peticion web normal. Si en el futuro negocio necesita mas volumen, convendra
pasar a exportacion diferida o asistida.

---

## Filtros temporales

El dashboard soporta estas vistas temporales:

- todo
- dia
- mes
- trimestre
- año
- rango personalizado

La seleccion del periodo se convierte en un rango `start_date` / `end_date`
comun para facturas y POS.

Aplicacion por modelo:

- `account.move` filtra por `invoice_date`
- `pos.order` filtra por `date_order` con limite superior exclusivo para cubrir
  bien el caso datetime

Ademas existe:

- busqueda por numero
- busqueda por cliente o proveedor
- busqueda por NIF
- filtro por compañia permitida del usuario

---

## Resumen economico

La vista principal ya no mezcla ventas y compras dentro de un solo bloque
monolitico. Primero presenta un `Hero + secciones` con dos accesos claros:

- `Ventas`
- `Compras`

Cada seccion mantiene sus propios filtros, resumenes y tabla de detalle, aunque
comparten infraestructura de periodo, compañia, busqueda y exportacion.

### Ventas

El dashboard de ventas muestra varias magnitudes separadas para evitar lecturas
engañosas:

- ventas facturadas
- abonos
- neto facturado
- base imponible operativa
- IVA operativo
- POS no facturado
- POS ya facturado
- pendiente de cobro
- vencido
- total operativo

Tambien expone un bloque fiscal simple orientado a gestoría:

- base imponible fiscal neta
- IVA repercutido neto
- IVA reducido por abonos

### Regla de negocio importante

El `total operativo` se calcula como:

- `neto facturado + POS no facturado`

No suma aparte el `POS ya facturado`, porque eso podria duplicar ventas que ya
han terminado convertidas en factura.

### Criterio actual

- `ventas facturadas`: suma de `out_invoice`
- `abonos`: suma absoluta de `out_refund`
- `neto facturado`: ventas facturadas menos abonos
- `POS no facturado`: POS en estados `paid` y `done`
- `POS ya facturado`: POS en estado `invoiced`

Para lectura operativa de cobro:

- las facturas se muestran como `paid`, `partially paid`, `pending` u `overdue`
- el listado muestra vencimiento y saldo pendiente
- el detalle intenta mostrar metodos de pago detectables
- POS muestra estado simplificado y metodos de pago cuando existen

### Compras

La seccion de compras sigue un criterio separado y mas orientado a pagos a
proveedor:

- compras facturadas
- abonos de proveedor
- neto de compras
- base fiscal de compras
- IVA soportado neto
- pendiente de pago
- vencido

La tabla operativa de compras mantiene la misma estructura economica base que
ventas, pero cambia el lenguaje visible a proveedor/pago y permite filtrar por:

- todo
- facturas proveedor
- abonos proveedor

## Helpers de modelo

`account.move` y `pos.order` concentran:

- dominio visible
- conteo
- orden por defecto
- validacion de acceso a registro concreto
- preparacion del item de listado
- preparacion del detalle
- preparacion de lineas
- preparacion de dominios de busqueda
- preparacion de lectura de cobro y metodos de pago

El modelo `wex.accounting.dashboard.report` concentra la lectura analitica
interna para `Tableros` y reporting backend, reutilizando el mismo criterio de
negocio del portal:

- neto facturado
- total operativo
- pendiente de cobro
- vencido
- POS no facturado
- base e IVA fiscal

Ademas:

- `account.move` prepara la descarga individual del PDF
- `account.move` prepara agregados de facturacion y abonos
- `pos.order` prepara agregados POS por estado
- ambos modelos exponen URLs de mostrar u ocultar lineas para el detalle

---

## Criterios de diseño

- no duplicar portal nativo completo de contabilidad
- mantener una interfaz simple y operativa
- usar una vista unificada solo para consulta
- mantener PDF individual solo en factura, no en POS
- no introducir API publica, tokens ni acceso por URL generica
- extraer constantes pequeñas cuando ayuden a evitar hardcodes repetidos
