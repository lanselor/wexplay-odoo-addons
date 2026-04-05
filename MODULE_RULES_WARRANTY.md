# MODULE_RULES_WARRANTY.md

## Objetivo del módulo
Implementar un sistema de garantías SAT en Odoo 18 Community para Wexplay, integrado sobre `repair.order`, que permita calcular automáticamente la garantía desde la factura, diferenciar garantía de piezas y mano de obra, tramitar RMAs y mantener trazabilidad completa entre SAT original y órdenes de garantía.

## Contexto técnico
- Odoo 18 Community
- On-premise
- Multi-company compatible
- Sin Studio
- Debe convivir con:
  - `wexplay_repair`
  - `wexplay_repair_workflow`
  - `wexplay_repair_delivery`

## Principio arquitectónico principal
NO crear un modelo operativo nuevo para RMA.

- Todo debe vivir en `repair.order`
- El RMA es un subtipo funcional
- Se identifica mediante:
  - `x_is_warranty_case = True`

El campo nativo `under_warranty` puede mantenerse como apoyo o compatibilidad, pero no debe ser la base del diseño.

---

## Alcance MVP
El MVP debe incluir:

- campos de garantía en `product.template`
- campos de garantía en `repair.order`
- cálculo de garantía desde servicios + factura
- excepción manual `x_force_no_warranty`
- bloque visual de garantías en ficha SAT
- badge visual de estado
- wizard de confirmación para tramitar garantía
- creación de nueva `repair.order` RMA
- secuencia propia `SATRMA/...`
- relación SAT origen ↔ garantías hijas
- adaptación mínima del workflow para casos de garantía
- integración mínima con delivery para permitir entrega de RMA sin depender necesariamente de factura

## Qué no entra en esta primera versión
- motor complejo de políticas reutilizables
- modelo separado de garantías
- frontend complejo
- reescritura completa del workflow
- automatismos avanzados no pedidos
- lógica excesiva en producto

---

## Reglas de negocio cerradas

### 1. Fuente de la garantía
La garantía se toma de los productos de tipo servicio en la pestaña `Services` de la `repair.order`.

### 2. Campos en producto
En `product.template` solo deben existir:

- `x_warranty_parts_months`
- `x_warranty_labor_months`

Reglas:
- default = 0
- no negativos
- `0 / 0` = sin garantía

### 3. Si hay varios servicios
- revisar todas las líneas de servicio
- elegir el servicio con mayor cobertura total
- cobertura total = `parts + labor`
- en empate, usar la primera línea

### 4. Excepción manual por SAT
Debe existir en `repair.order`:

- `x_force_no_warranty`

Caso de uso:
- cliente trae su propia pieza
- se cobra mano de obra genérica
- ese SAT concreto no debe tener garantía

Regla:
- si `x_force_no_warranty = True`, la garantía final es `0 / 0`

### 5. Cálculo temporal
La garantía se calcula desde la fecha de la factura vinculada.

Debe diferenciar:
- garantía de piezas
- garantía de mano de obra

### 6. Congelación de datos
Los meses de garantía efectivos deben copiarse a `repair.order` para mantener histórico aunque luego cambie el producto.

### 7. Estado visual
Debe mostrarse visualmente si la orden:
- está en garantía
- está fuera de garantía
- no tiene garantía por decisión manual

---

## Modelo de datos

### En `product.template`
- `x_warranty_parts_months`
- `x_warranty_labor_months`

### En `repair.order`

#### Identificación y trazabilidad
- `x_is_warranty_case`
- `x_warranty_origin_repair_id`
- `x_warranty_child_ids`

#### Garantía congelada
- `x_warranty_parts_months`
- `x_warranty_labor_months`

#### Excepción manual
- `x_force_no_warranty`

#### Factura base
- `x_warranty_source_invoice_id`
- `x_warranty_source_invoice_date`

#### Fechas y estado
- `x_warranty_parts_deadline`
- `x_warranty_labor_deadline`
- `x_is_parts_under_warranty`
- `x_is_labor_under_warranty`
- `x_is_any_warranty_valid`

---

## UI

### Bloque de garantías en repair.order
Ubicación sugerida:
- debajo de recepción SAT / dispositivo

Debe mostrar:
- meses aplicados
- factura base
- fechas límite
- estado visual

### Badge
- verde → en garantía
- rojo → fuera de garantía

### Caso especial
Si `x_force_no_warranty = True`:
- mostrar claramente “Sin garantía”

---

## Tramitación de garantía

### Botón
Debe existir botón:
- `Tramitar garantía`

### Wizard
Mensaje:
- `¿Está seguro de que desea tramitar la garantía?`

Botones:
- `Sí, tramitar garantía`
- `Cancelar`

### Fuera de plazo
Si está fuera de plazo:
- checkbox obligatorio:
  - `Confirmo que desea tramitar igualmente la garantía`

Idealmente restringido por permisos/grupos.

---

## Creación del RMA

### Crear nueva `repair.order`

### Copiar
- cliente
- producto/equipo
- marca / modelo
- IMEI / nº serie
- avería
- datos de desbloqueo si aplican
- vínculo al SAT origen
- datos de garantía congelados

### No copiar
- piezas usadas
- servicios usados
- notas
- técnico recepciona
- referencia cliente
- accesorios

### Inicialización
- `x_is_warranty_case = True`
- vínculo al SAT origen
- prioridad de garantía si existe el campo correspondiente

---

## Secuencia
El RMA debe usar secuencia propia:
- `SATRMA/...`

Pero debe seguir listándose en `repair.order` como cualquier otra orden.

---

## Relaciones

### En SAT original
Smart button:
- Garantías

### En RMA
Smart button:
- SAT origen

### En `res.partner`
Acceso a:
- órdenes con `x_is_warranty_case = True`

---

## Integración con Workflow
NO duplicar workflow completo.

Reutilizar `wexplay_repair_workflow` tanto como sea posible.

Si `x_is_warranty_case = True`, adaptar labels:
- `Sin presupuesto` -> `Sin revisión`
- `Iniciar presupuesto` -> `Iniciar revisión`
- `Aceptado` -> `RMA aceptado` / `Garantía aprobada`
- `Rechazado` -> `RMA rechazado`
- `Esperando cliente` se mantiene

---

## Integración con Delivery
El RMA puede no tener factura.

Regla:
- no bloquear entrega por ausencia de factura
- permitir flujo manual/operativo
- reutilizar `wexplay_repair_delivery` si no rompe el flujo actual

---

## Prioridad
Si existe `wex_repair_priority_option` y hay opción específica de garantía:
- marcarla por defecto al crear RMA
- dejarla readonly si es posible sin hacks frágiles

---

## Ajustes
Cualquier ajuste nuevo debe integrarse en la vista/app de Ajustes:
- `Wexplay SAT`

---

## Reglas de código obligatorias
- evitar `if` anidados largos
- usar métodos pequeños y semánticos:
  - `_can_*`
  - `_is_*`
  - `_has_*`
  - `_get_*`
  - `_prepare_*`
  - `_check_*`
- los `action_*` deben ser finos
- usar guard clauses
- separar validación, cálculo, preparación y acción
- si una condición se repite, extraerla a método
- no esconder lógica importante en XML o JS

---

## Qué evitar
- lógica duplicada entre capas
- múltiples fuentes de verdad
- sobreingeniería
- campos innecesarios en producto
- JS para resolver reglas de negocio
- reescribir más de lo necesario