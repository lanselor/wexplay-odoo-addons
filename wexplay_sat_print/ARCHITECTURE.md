# Wexplay SAT Print — Arquitectura

## Propósito

`wexplay_sat_print` contiene los flujos de impresión específicos del SAT (órdenes de reparación).

Pertenece a este módulo:
- Reportes QWeb de etiquetas y ticket SAT
- Modal de impresión SAT
- Acciones cliente SAT
- Actualización de los tipos de documento del core con los reportes propios

Reutiliza `wex_print_core` para toda la capa técnica compartida (QZ, router, perfiles, asignaciones, trazas).

---

## Reportes QWeb

| ID | Nombre | Modelo | Formato | Paperformat |
|----|--------|--------|---------|-------------|
| `report_repair_label_29x90` | SAT Label 29x90 | repair.order | PDF | 29×90 mm landscape |
| `report_repair_label_29x42` | SAT Label 29x42 | repair.order | PDF | 29×42 mm landscape |
| `report_repair_ticket_80x170` | SAT Ticket 80x170 | repair.order | PDF | 80×170 mm portrait |

### Paperformats definidos

| ID | Nombre | Dimensiones | Orientación | DPI |
|----|--------|-------------|-------------|-----|
| `paperformat_sat_label_29x90` | SAT Label 29x90 (Brother QL) | 29×90 mm | Landscape | 90 |
| `paperformat_sat_label_29x42` | SAT Accessories Label 29x42 (Brother QL) | 29×42 mm | Landscape | 90 |
| `paperformat_sat_ticket_80x170` | SAT Ticket 80x170 (Thermal) | 80×170 mm | Portrait | 90 |

---

## Tipos de documento actualizados

Este módulo actualiza los tipos de documento definidos en `wex_print_core` para vincularlos con los reportes y paperformats propios:

| Código | report_action_id | paperformat_id |
|--------|-----------------|----------------|
| `sat_label_main` | report_repair_label_29x90 | paperformat_sat_label_29x90 |
| `sat_label_accessory` | report_repair_label_29x42 | paperformat_sat_label_29x42 |
| `sat_ticket` | report_repair_ticket_80x170 | paperformat_sat_ticket_80x170 |

Esta vinculación se hace en `data/document_type_update.xml`, que se carga después de los reportes y paperformats.

---

## Flujo de impresión SAT

1. Usuario abre una `repair.order`
2. Clic en botón **Impresiones** (inyectado en el header del formulario)
3. Se abre el modal `SatPrintCenterModal`
4. El modal ofrece tres acciones:
   - **Etiqueta SAT Completa** (29×90) → `document_code: sat_label_main`
   - **Accesorios** (29×42) + selector de cantidad → `document_code: sat_label_accessory`
   - **Resguardo** (80×170) → `document_code: sat_ticket`
5. Cada acción llama a `printOdooDocument(documentCode, reportUrl, env, opts)` de `wex_print_core`
6. El router resuelve el path (legacy o híbrido) y envía a QZ Tray

---

## Corrección de altura de etiqueta

El fix de altura está implementado en `wex_print_core`. Para que la etiqueta 29×42 corte a 42mm (y no a 90mm):

1. El `paperformat_id` del document type `sat_label_accessory` debe estar correctamente vinculado a `paperformat_sat_label_29x42` (ya configurado en `document_type_update.xml`)
2. La asignación `sat_label_accessory` debe tener `Activar resolución nueva = True`
3. El modo de resolución debe ser `Híbrido` o `Solo nuevo`

En el path nuevo, `buildQlLabelConfig` recibe `height=42` desde el paperformat y lo pasa a QZ, que informa al driver del punto de corte correcto.

---

## Códigos de documento SAT

| Código | Descripción |
|--------|-------------|
| `sat_label_main` | Etiqueta principal 29×90 mm |
| `sat_label_accessory` | Etiqueta de accesorios 29×42 mm |
| `sat_ticket` | Ticket de resguardo para cliente 80×170 mm |
| `sat_a4` | Documento A4 (reservado para uso futuro) |

---

## Límites del módulo

**Debe contener:**
- Definiciones de reportes QWeb SAT
- Acciones cliente SAT
- Modal de impresión SAT
- Actualización de tipos de documento del core con datos SAT

**No debe contener:**
- Lógica de QZ compartida
- Router de impresión
- Diagnósticos o trazas
- Reportes de producto

---

## Deuda técnica

- Los formatos 29×90 y 29×42 no están modelados a través de una capa de variantes formal
- El fix de altura depende del path nuevo (hybrid/new_only); en legacy siempre corta según la configuración del driver

---

## Documentación relacionada

- [MANUAL_CONFIGURACION_QZ.md](../wex_print_core/MANUAL_CONFIGURACION_QZ.md) — Guía de configuración completa
- [wex_print_core/ARCHITECTURE.md](../wex_print_core/ARCHITECTURE.md) — Arquitectura del núcleo técnico
