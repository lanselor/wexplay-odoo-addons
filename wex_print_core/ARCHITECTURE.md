# Wex Print Core — Arquitectura

## Propósito

`wex_print_core` es el módulo técnico compartido de impresión para el stack Wexplay.

Centraliza:
- Integración con QZ Tray
- Catálogo de dispositivos de impresión
- Configuración de perfiles y asignaciones
- Enrutamiento de impresión (legacy / híbrido / nuevo)
- Trazas de auditoría
- Diagnóstico de impresoras

No contiene lógica de negocio de SAT ni de producto.

---

## Modelos

### `wex.print.device`
Impresora física registrada en el sistema.

Campos relevantes:
- `qz_printer_name` — nombre exacto en QZ Tray / Windows
- `device_kind` — `Etiqueta`, `Térmica`, `A4`
- `model_hint` — texto libre, solo informativo (ej: "Brother QL-710W")
- `paperformat_ids` — formatos de papel que acepta (Many2many → `report.paperformat`)
- `report_action_ids` — reportes compatibles (Many2many → `ir.actions.report`)

Las capacidades (`paperformat_ids`, `report_action_ids`) son opcionales. Si están configuradas, el resolver las valida y registra warnings en la traza si hay incompatibilidad. No bloquean la impresión.

### `wex.print.device.snapshot`
Captura de estado de impresoras cargada desde QZ Tray.

- Solo lectura. Se crea desde `Cargar diagnóstico desde QZ`.
- Campo computed `existing_device_id`: detecta si ya existe un `wex.print.device` con ese nombre.
- Método `action_save_as_device()`: crea un dispositivo pre-rellenado y abre su formulario. Si ya existe, abre el existente sin duplicar.

### `wex.print.document.type`
Tipo de documento imprimible.

Campos relevantes:
- `code` — identificador único usado por el router JS
- `legacy_kind` — `Etiqueta`, `Térmica`, `A4` (fuente de verdad para el path Legacy)
- `report_action_id` — Many2one a `ir.actions.report` (fuente de verdad para el path nuevo)
- `paperformat_id` — Many2one a `report.paperformat`
- `report_name` — Char legacy, fallback si `report_action_id` no está poblado
- `paperformat_page_height` / `paperformat_page_width` — devueltos en `get_document_payload()` para que el cliente JS pueda configurar el tamaño correcto en QZ

El método `get_document_payload()` devuelve todo lo necesario para el router JS incluyendo las dimensiones del paperformat.

### `wex.print.profile`
Configuración de salida para un dispositivo.

- Apunta a un `wex.print.device` (o nombre directo para legacy)
- Parámetros: copias, modo dúplex, permitir fallback

### `wex.print.assignment`
Tabla de routing: tipo de documento → perfil.

- Puede restringirse por usuario (+20 score) y/o empresa (+10 score)
- `pilot_use_new_resolution`: activa el path nuevo en modo Híbrido para esta asignación
- El resolver `resolve_shadow()` selecciona el candidato de mayor score entre los que cumplen los filtros

### `wex.print.trace`
Registro de auditoría de cada decisión de impresión. Solo lectura.

---

## Enrutamiento

### Modos

| Modo | Comportamiento |
|------|----------------|
| `legacy` | Solo path antiguo. Ignora perfiles y asignaciones. |
| `hybrid` | Usa path nuevo si la asignación tiene `pilot_use_new_resolution=True`. Fallback automático a legacy si falla. |
| `new_only` | Solo path nuevo. Sin fallback. Para pruebas controladas. |

Configurado en: `Ajustes → Wexplay Print / QZ → Modo de Resolución` (parámetro `wex_print_core.print_mode`).

### Path Legacy

```
res.users.wex_qz_{kind}_device_id  →  qz_printer_name
res.users.wex_qz_{kind}_printer    →  nombre directo
res.company  →  fallback
ir.config_parameter  →  fallback final
```

El `device_kind` (label/thermal/a4) es la clave de selección. El height del paperformat NO se pasa en este path.

### Path Nuevo

```
document_code  →  WexPrintAssignment.resolve_shadow()
             →  profile_id  →  device_id  →  qz_printer_name
             →  paperformat_page_height (para etiquetas)
```

El height del paperformat se pasa a `buildQlLabelConfig` para que QZ informe al driver del tamaño de corte correcto. Solo activo cuando `useNewResolution = true`.

### Resolución de score en assignments

```
Sin usuario ni empresa  →  score 0
Con empresa             →  score 10
Con usuario             →  score 20
Con usuario + empresa   →  score 30
```

Se selecciona el candidato con mayor score entre los que cumplen: documento correcto + usuario/empresa coinciden o están vacíos.

### Validación de compatibilidad de dispositivo

`resolve_shadow()` comprueba si el dispositivo asignado tiene el reporte del documento en su `report_action_ids`. Si no lo tiene (y la lista no está vacía), añade un warning en el campo `message` de la resolución. No bloquea la impresión. Aparece en el trace.

---

## Assets JavaScript

| Archivo | Propósito |
|---------|-----------|
| `print_router.js` | Determina el modo y el path de ejecución |
| `qz_print.js` | Conexión QZ, config builders, función principal `printOdooDocument` |
| `printer_diagnostics_action.js` | Acción cliente de diagnóstico |
| `qz_settings_widget.js` | Widget de estado en Ajustes |
| `qz-tray.js` | Librería oficial QZ Tray (carga local) |

### `buildQlLabelConfig(printer, opts)`

Construye la configuración QZ para impresoras de etiquetas Brother QL.

- `opts.copies` — número de copias
- `opts.height` — altura en mm del paperformat. Si se pasa, se incluye en `size.height` para que el driver corte a la medida correcta. El path Legacy nunca lo pasa (comportamiento sin cambios).

---

## Estado de producción validado

- Modo Híbrido operativo
- Impresión de etiquetas de producto
- Impresión de etiquetas SAT (29x90 y 29x42)
- Impresión de tickets SAT (80x170)
- Impresión A4 con dúplex (borde largo)
- Rollback a Legacy verificado

### Impresoras validadas en producción

| Tipo | Dispositivo | Nombre en QZ |
|------|-------------|--------------|
| Etiqueta | Brother QL-710W | `Brother QL-710W` |
| Térmica | PRP-300 | `PRP-300 Copiar 1` |
| A4 | Brother MFC-L2800DW | `Brother MFC-L2800DW Printer` |

---

## Límites del módulo

**Debe contener:**
- Helpers QZ compartidos
- Ajustes compartidos
- Modelos de device, profile, assignment, document type
- Router y lógica de fallback
- Diagnósticos y trazas

**No debe contener:**
- Definiciones de reportes QWeb de producto o SAT
- Lógica de negocio de SAT ni de producto

---

## Deuda técnica conocida

- El path Legacy todavía usa `device_kind` (label/thermal/a4) como clave, no el documento concreto
- QZ sigue en modo sin firma (unsigned), se esperan prompts en navegadores con seguridad estricta
- No existe todavía una capa formal de variantes de impresión que relacione documento → reporte → paperformat → dispositivo de forma completa

---

## Documentación relacionada

- [MANUAL_CONFIGURACION_QZ.md](MANUAL_CONFIGURACION_QZ.md) — Guía paso a paso de configuración desde cero
