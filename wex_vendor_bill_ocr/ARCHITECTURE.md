# Wex Vendor Bill OCR Architecture

## Objetivo real del módulo

`wex_vendor_bill_ocr` existe para acelerar la recepción administrativa de compras cuando el proveedor envía una factura PDF y el equipo quiere:

- extraer datos básicos sin picarlos a mano
- revisar el resultado antes de confirmar
- recibir material y crear la factura de proveedor dentro del flujo nativo de Odoo

El módulo no pretende sustituir `account.move` ni crear un motor OCR genérico para cualquier documento.

## Qué hace hoy

- añade a `purchase.order` una entrada para subir una factura PDF de proveedor
- crea un job persistente `wex.vendor.bill.ocr.job` por cada PDF subido
- procesa la cola por `cron` con estados explícitos: `draft`, `processing`, `review`, `done`, `error`
- intenta extraer texto embebido del PDF y usa OCR como fallback si el texto directo no es útil
- parsea datos operativos mínimos:
  - proveedor
  - VAT
  - número de factura
  - fecha
  - referencia externa
  - base imponible
  - impuestos
  - total
- muestra texto bruto, progreso, flags y confianza para revisión humana
- permite completar seriales si hay recepciones pendientes de productos con tracking por serie
- valida recepciones entrantes pendientes de la compra
- crea la factura de proveedor usando `purchase.action_create_invoice()`
- copia el PDF original al `account.move` generado

## Qué no hace

- no crea facturas de proveedor fuera del flujo nativo de compra
- no soporta imágenes sueltas ni formatos distintos de PDF en esta fase
- no intenta autoaplicar resultados sin revisión humana previa
- no resuelve OCR semántico de líneas de factura
- no concilia diferencias complejas entre la factura del proveedor y la compra más allá de comprobaciones básicas de importes

## Modelos y responsabilidades

### `wex.vendor.bill.ocr.job`

Modelo principal del módulo.

Responsabilidades actuales:
- persistir la cola OCR por compra
- controlar progreso, errores y reintentos
- extraer texto del adjunto
- parsear datos mínimos de factura
- exponer flags operativos para revisión
- orquestar recepción + creación de factura al confirmar el wizard

Métodos relevantes:
- `_cron_process_queue()`
- `_claim_next_job_for_processing()`
- `_process_job()`
- `_extract_text()`
- `_parse_extracted_text()`
- `action_open_review_wizard()`
- `action_apply_review()`

### Extensión de `purchase.order`

Archivo: [purchase_order.py](/C:/odoo18/addons-wexplay/wex_vendor_bill_ocr/models/purchase_order.py)

Responsabilidades actuales:
- mostrar contador de jobs OCR por compra
- abrir el wizard de subida de PDF
- abrir el listado/formulario de jobs asociados

### `wex.vendor.bill.ocr.upload.wizard`

Archivo: [vendor_bill_ocr_upload_wizard.py](/C:/odoo18/addons-wexplay/wex_vendor_bill_ocr/wizards/vendor_bill_ocr_upload_wizard.py)

Responsabilidades actuales:
- recibir el PDF desde `purchase.order`
- crear el `ir.attachment`
- crear el job en cola con estado inicial `draft`

### `wex.vendor.bill.ocr.review.wizard`

Archivo: [vendor_bill_ocr_review_wizard.py](/C:/odoo18/addons-wexplay/wex_vendor_bill_ocr/wizards/vendor_bill_ocr_review_wizard.py)

Responsabilidades actuales:
- precargar datos parseados del job
- permitir corrección manual antes de aplicar
- recoger seriales requeridos para recepciones con tracking
- validar duplicidades y cantidades de seriales
- disparar la aplicación final sobre recepción y factura

## Flujo operativo real

1. El usuario abre una `purchase.order` confirmada.
2. Sube un PDF de factura de proveedor.
3. El módulo crea un adjunto y un job OCR en cola.
4. El `cron` reclama un job `draft` y lo pasa a `processing`.
5. El sistema intenta extraer texto:
   - primero por texto embebido
   - después por OCR si el texto directo no es suficiente
6. El job pasa a `review` con datos parseados, texto bruto y confianza.
7. El usuario abre el wizard de revisión y ajusta datos si hace falta.
8. Si existen recepciones pendientes:
   - el módulo valida que la compra siga en estado válido
   - fuerza la recepción de cantidades pendientes
   - exige seriales exactos cuando el producto tiene tracking por serie
9. El módulo crea la factura de proveedor desde la compra, escribe fecha y número de factura y adjunta el PDF.
10. El job queda en `done` enlazado al `account.move` resultante.

## Reglas funcionales actuales

- la compra debe estar al menos en `purchase` o `done`
- solo se soportan PDFs en esta fase
- no puede aplicarse un job si ya creó una factura
- no puede aplicarse si la compra ya tiene una factura de proveedor no cancelada
- el proveedor del wizard debe coincidir con el proveedor comercial de la compra
- el número de factura se valida contra facturas existentes del mismo proveedor
- los importes no pueden ser negativos
- si hay base, impuesto y total, deben cuadrar entre sí

## Dependencias Python reales

El módulo depende operativamente de:

- `pypdf` o `PyPDF2` para lectura de texto embebido
- `pytesseract`
- `pdf2image`

Si faltan estas dependencias:
- el parseo por texto directo o el fallback OCR pueden fallar
- el job queda trazado en error con mensaje explícito

## Deuda viva más importante

- el parseo está basado en heurísticas de texto y contexto de compra, no en plantillas por proveedor
- no hay tests visibles todavía para esta primera iteración local
- no hay documentación técnica separada para instalación de dependencias del servidor
- el flujo asume una factura por compra y no modela bien escenarios de múltiples facturas parciales del mismo pedido
- el job usa `commit()` explícito para asegurar trazabilidad de cola; funciona para esta fase, pero conviene revisarlo si el módulo crece
