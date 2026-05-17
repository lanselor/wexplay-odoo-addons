# Wexplay Product Print — Arquitectura

## Propósito

`wexplay_product_print` gestiona la impresión de etiquetas de producto (`product.template`).

Pertenece a este módulo:
- Reporte QWeb de etiqueta de producto
- Paperformat de etiqueta de producto
- Modal de impresión de producto
- Controlador de URL firmada para descarga de PDF por QZ
- Actualización del tipo de documento del core con el reporte propio

Reutiliza `wex_print_core` para toda la capa técnica compartida.

---

## Reporte QWeb

| ID | Nombre | Modelo | Formato |
|----|--------|--------|---------|
| `action_report_product_label_ql700_62x29` | Etiqueta Brother QL 62x29 | product.template | PDF |

El reporte está vinculado al formulario de `product.template` mediante `binding_model_id`, por lo que aparece también en el menú estándar de impresión de Odoo.

### Paperformat

| ID | Nombre | Dimensiones | Orientación | DPI |
|----|--------|-------------|-------------|-----|
| `paperformat_product_label_42x29` | Product Label 42x29 (Brother QL) | 42×29 mm | Landscape | 90 |

> El nombre del action dice "62x29" (ancho de cinta Brother QL estándar) pero el CSS del template define `@page { size: 42mm 29mm }`. El paperformat usa las dimensiones reales del CSS (42×29).

---

## Tipo de documento actualizado

Este módulo actualiza el tipo de documento `product_label` definido en `wex_print_core`:

| Código | report_action_id | paperformat_id |
|--------|-----------------|----------------|
| `product_label` | action_report_product_label_ql700_62x29 | paperformat_product_label_42x29 |

Configurado en `data/document_type_update.xml`.

---

## Flujo de impresión de producto

1. Usuario abre un `product.template`
2. Clic en botón **Impresión** (inyectado en el header del formulario)
3. Se abre el modal `ProductPrintModal`
4. El modal obtiene una URL firmada desde `/wexplay/label/signed_url` (POST autenticado)
5. QZ Tray descarga el PDF desde `/wexplay/label/pdf/<id>?token=...` (GET público con token)
6. El router de `wex_print_core` resuelve el dispositivo y configuración de QZ
7. Se imprime en el dispositivo resuelto

---

## Controlador de URL firmada

**Clase:** `WexplayProductLabelToken`

| Ruta | Auth | Propósito |
|------|------|-----------|
| `GET /wexplay/label/ping` | public | Health check |
| `POST /wexplay/label/signed_url` | user | Genera URL firmada válida 60 segundos |
| `GET /wexplay/label/pdf/<id>` | public + token | Descarga PDF validando HMAC |

### Seguridad del token

- Firma: HMAC-SHA256 con `database.secret` como clave
- Mensaje: `"{product_id}:{expires}"`
- Validez: 60 segundos desde la generación
- El `report_name` está hardcodeado en el servidor; no se acepta ningún otro

Este mecanismo permite que QZ Tray (que no tiene sesión Odoo) descargue el PDF sin exponer el endpoint de forma permanente.

---

## Límites del módulo

**Debe contener:**
- Reporte QWeb de etiqueta de producto
- Paperformat de etiqueta de producto
- Modal de impresión de producto
- Controlador de URL firmada
- Actualización del tipo de documento del core

**No debe contener:**
- Lógica QZ compartida
- Router de impresión
- Diagnósticos o trazas
- Reportes SAT

---

## Configuración de producción validada

- Perfil: `Product Label Prod`
- Dispositivo: `Brother QL-710W`
- Asignación: `Product Label Default` con `Activar resolución nueva = True`
- Modo: Híbrido

---

## Documentación relacionada

- [MANUAL_CONFIGURACION_QZ.md](../wex_print_core/MANUAL_CONFIGURACION_QZ.md) — Guía de configuración completa
- [wex_print_core/ARCHITECTURE.md](../wex_print_core/ARCHITECTURE.md) — Arquitectura del núcleo técnico
