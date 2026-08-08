# Manual de configuración — Wex Print / QZ Tray

## Índice

1. [Requisitos previos](#1-requisitos-previos)
2. [Verificar la conexión con QZ Tray](#2-verificar-la-conexión-con-qz-tray)
3. [Buscar y configurar impresoras desde QZ](#3-buscar-y-configurar-impresoras-desde-qz)
4. [Configuración avanzada](#4-configuración-avanzada)
5. [Configurar impresoras Legacy por usuario](#5-configurar-impresoras-legacy-por-usuario)
6. [Activar el modo híbrido](#6-activar-el-modo-híbrido)
7. [Verificar con Trazas](#7-verificar-con-trazas)
8. [Vuelta atrás de emergencia](#8-vuelta-atrás-de-emergencia)
9. [Referencia rápida de documentos](#9-referencia-rápida-de-documentos)

---

## 1. Requisitos previos

### QZ Tray instalado y en ejecución

QZ Tray debe estar instalado y ejecutándose en el ordenador desde el que se imprime.
La aplicación corre en segundo plano y se conecta al navegador por WebSocket en los puertos 8181/8182.

- Descarga: https://qz.io/download/
- Se iniciará automáticamente con Windows si se configura como servicio o inicio automático.
- Verificación: el icono de QZ Tray debe aparecer en la barra de tareas.

### Módulos instalados

Los tres módulos deben estar instalados en Odoo:

| Módulo | Propósito |
|--------|-----------|
| `wex_print_core` | Núcleo técnico: dispositivos, perfiles, asignaciones, trazas |
| `wexplay_sat_print` | Centro de impresión SAT (órdenes de reparación) |
| `wexplay_product_print` | Centro de impresión de productos |

---

## 2. Verificar la conexión con QZ Tray

`Ajustes → Wexplay Print / QZ`

En la sección **Estado y Diagnóstico** se muestra el estado actual de QZ Tray en ese navegador.

1. Haz clic en **Probar conexión QZ**.
2. Si aparece `Conexión OK (versión X.X.X)` → QZ está operativo.
3. Si falla: comprueba que QZ Tray esté ejecutándose en el ordenador y que el navegador permita conexiones WebSocket locales.

> **Nota:** El estado de QZ es por navegador y por puesto. Un test OK en un ordenador no garantiza que funcione en otro.

---

## 3. Buscar y configurar impresoras desde QZ

Este es el flujo habitual para añadir una impresora. Crea el dispositivo, el perfil y las asignaciones documentales sin modificar la configuración Legacy existente.

### 3.1 Buscar impresoras

`Wex Print → Buscar impresoras`

Esto conecta con QZ Tray y abre **Impresoras encontradas** con los dispositivos disponibles en el ordenador actual.

### 3.2 Configurar impresora

En la impresora elegida, pulsa **Configurar impresora**. El asistente muestra el nombre exacto de QZ y el driver detectado.

1. Confirma el nombre, tipo físico y empresa.
2. Añade los tipos de documento que imprimirá. El asistente enseña el reporte y formato de cada uno y los guarda como capacidades del dispositivo.
3. Define si la regla aplica a un usuario concreto y los ajustes relevantes, como dúplex para A4.
4. Pulsa **Crear configuración**.

El asistente crea el dispositivo, un perfil estándar y una asignación por documento. `Activar resolución nueva ahora` queda desmarcado por defecto para que el modo `Hybrid` siga utilizando el camino Legacy hasta que la nueva configuración se pruebe.

> Para que las columnas **Reporte** y **Formato** se completen y queden como capacidades del dispositivo, el tipo documental elegido debe tener esos dos campos configurados. El nombre técnico del reporte mantiene compatibilidad con impresiones existentes, pero no sustituye la relación documental necesaria para el asistente.

> La impresora Legacy de usuario o empresa no se modifica desde este asistente. Sigue siendo el fallback operativo y se configura de forma explícita en Preferencias o Ajustes.

### Ampliar una impresora ya configurada

`Wex Print → Dispositivos → [impresora] → Añadir documentos`

La ficha del dispositivo muestra todos los documentos que ya se resuelven hacia esa impresora, con su reporte, formato, perfil, usuario y estado de la resolución nueva. El botón **Añadir documentos** reutiliza el mismo asistente para crear o reutilizar el perfil necesario y añadir las asignaciones sin tener que navegar por Perfiles y Asignaciones.

Las capacidades visibles de reporte y formato se derivan de esas asignaciones, por lo que no se mantienen manualmente en un tercer sitio.

---

## 4. Configuración avanzada

`Wex Print → Dispositivos → [selecciona dispositivo]`

### Sección Identificación

| Campo | Qué poner |
|-------|-----------|
| **Nombre** | Nombre descriptivo. Ej: `QL-710W Taller` |
| **Modelo de impresora** | Solo informativo. Ej: `Brother QL-710W` |
| **Backend** | Siempre `QZ Tray` |
| **Tipo** | `Etiqueta`, `Térmica` o `A4` según el tipo de impresora |
| **Nombre en QZ** | Nombre exacto como aparece en Windows. Ej: `Brother QL-710W` |
| **Empresa** | Opcional. Deja vacío si es válido para todas |

### Sección Capacidades derivadas

| Campo | Cómo se completa |
|-------|-----------|
| **Formatos de papel soportados** | Se derivan de los tipos de documento asignados a los perfiles de esta impresora |
| **Reportes compatibles** | Se derivan de los mismos tipos de documento |

Estos campos son informativos y de solo lectura. No se mantienen manualmente: para añadir o retirar capacidad documental hay que usar **Añadir documentos** desde la ficha de la impresora o gestionar la asignación correspondiente. Así se evita que la ficha de dispositivo, los perfiles y las reglas de resolución puedan quedar desalineados.

#### Capacidades por tipo de impresora

**Brother QL-710W (etiquetas):**
- Formatos: `SAT Label 29x90 (Brother QL)`, `SAT Accessories Label 29x42 (Brother QL)`, `Product Label 42x29 (Brother QL)`
- Reportes: `SAT Label 29x90`, `SAT Label 29x42`, `Etiqueta Brother QL 62x29`

**PRP-300 / Impresora térmica 80mm:**
- Formatos: `SAT Ticket 80x170 (Thermal)`
- Reportes: `SAT Ticket 80x170`

**Brother MFC-L2800DW / Impresora A4:**
- Formatos: `A4` (el formato estándar de Odoo)
- Reportes: los reportes A4 que uses

> **Dos impresoras del mismo modelo en distintos puestos** (ej: dos QL-710W): crea un dispositivo para cada una con el mismo nombre en QZ y las mismas capacidades. Cada usuario apuntará a su dispositivo correspondiente.

---

### Crear o editar perfiles de impresión

Un perfil une un dispositivo con su configuración de salida (copias, dúplex).

`Wex Print → Perfiles → Nuevo`

| Campo | Descripción |
|-------|-------------|
| **Nombre** | Descriptivo. Ej: `SAT Etiqueta Principal - Taller` |
| **Código** | Único, sin espacios. Ej: `sat_label_main_taller` |
| **Tipo legacy** | Debe coincidir con el tipo del dispositivo (`Etiqueta`, `Térmica`, `A4`) |
| **Dispositivo** | Selecciona el dispositivo creado en el paso anterior |
| **Nombre directo de impresora** | Solo si no usas dispositivo guardado (modo legacy puro) |
| **Permitir fallback** | Activado: si QZ falla, usa la impresora por defecto del sistema |
| **Copias** | `0` = usa el valor por defecto. Ponlo en `1` o más para forzar |
| **Modo dúplex** | Solo relevante para A4. `Por defecto` para el resto |

### Ejemplo de perfiles mínimos para una instalación SAT completa

| Perfil | Código | Tipo | Dispositivo |
|--------|--------|------|-------------|
| SAT Etiqueta Principal | `sat_main_label` | Etiqueta | QL-710W Taller |
| SAT Etiqueta Accesorios | `sat_acc_label` | Etiqueta | QL-710W Taller |
| SAT Ticket | `sat_ticket` | Térmica | PRP-300 Taller |
| Etiqueta Producto | `product_label` | Etiqueta | QL-710W Taller |

> Si tienes un solo perfil para varios documentos del mismo dispositivo, puedes reutilizarlo en múltiples asignaciones.

---

### Crear o editar asignaciones

Una asignación conecta un tipo de documento con un perfil, con la posibilidad de restringirla a un usuario o empresa concretos.

`Wex Print → Asignaciones → Nuevo`

| Campo | Descripción |
|-------|-------------|
| **Nombre** | Descriptivo. Ej: `SAT Etiqueta Principal - Default` |
| **Prioridad** | `100` por defecto. Números menores tienen más prioridad |
| **Activar resolución nueva** | ☑ Debe estar marcado para que el path nuevo funcione en modo Híbrido |
| **Tipo de documento** | El código del documento (ver tabla al final) |
| **Perfil de impresión** | El perfil creado en el paso anterior |
| **Usuario** | Opcional. Si se rellena, esta asignación solo aplica a ese usuario (+20 puntos de score) |
| **Empresa** | Opcional. Si se rellena, solo aplica a esa empresa (+10 puntos) |

### Lógica de resolución

Cuando hay varias asignaciones para el mismo documento, el sistema elige la más específica:

```
Sin usuario ni empresa  →  score 0   (asignación genérica)
Solo empresa            →  score 10  (más específica que la genérica)
Solo usuario            →  score 20  (más específica que la de empresa)
Usuario + empresa       →  score 30  (la más específica posible)
```

**Caso más habitual — impresora distinta por usuario:**
1. Crea una asignación genérica (sin usuario ni empresa) apuntando al perfil por defecto.
2. Para el usuario que necesita una impresora distinta, crea una segunda asignación con su `usuario` rellenado y un perfil diferente.
3. Para ese usuario, la segunda asignación ganará siempre por tener mayor score.

### Asignaciones mínimas para una instalación SAT + Producto

| Nombre | Tipo de documento | Perfil | Usuario |
|--------|-------------------|--------|---------|
| SAT Etiqueta Principal - Default | SAT Main Label | SAT Etiqueta Principal | (vacío) |
| SAT Etiqueta Accesorios - Default | SAT Accessory Label | SAT Etiqueta Accesorios | (vacío) |
| SAT Ticket - Default | SAT Thermal Ticket | SAT Ticket | (vacío) |
| Etiqueta Producto - Default | Product Label | Etiqueta Producto | (vacío) |

---

## 5. Configurar impresoras Legacy por usuario

Este paso es para el **path Legacy** y como fallback. Mientras no estés en modo `Solo nuevo`, es conveniente rellenarlo.

El usuario puede configurar sus impresoras desde su perfil de Odoo:

`(menú de usuario) → Mis preferencias → sección Wex Print`

O desde la ficha del usuario:

`Ajustes → Usuarios → [usuario] → pestaña Preferencias → sección Wex Print`

| Campo | Descripción |
|-------|-------------|
| **Dispositivo etiquetas (usuario)** | Selecciona el dispositivo guardado para etiquetas en este puesto |
| **Impresora etiquetas (usuario)** | Alternativa de texto si no usas dispositivo guardado |
| **Dispositivo térmico (usuario)** | Para tickets térmicos |
| **Dispositivo A4 (usuario)** | Para documentos A4 |

> La configuración de usuario tiene prioridad sobre la configuración de empresa. Si el campo de usuario está relleno, el de empresa se ignora.

### Configurar impresoras por empresa (default para todos)

`Ajustes → Wexplay Print / QZ → Configuración de Impresoras`

Aquí se define la impresora que usan todos los usuarios que no tengan configuración propia.

---

## 6. Activar el modo híbrido

Una vez que tienes dispositivos, perfiles y asignaciones configurados y verificados:

`Ajustes → Wexplay Print / QZ → Opciones Avanzadas → Modo de Resolución`

| Valor | Comportamiento |
|-------|----------------|
| **Legacy** | Usa solo la configuración antigua (usuario/empresa). Ignora perfiles y asignaciones. |
| **Híbrido** | Usa el path nuevo si la asignación tiene `Activar resolución nueva` marcado. Si falla, cae a Legacy automáticamente. **Recomendado para producción.** |
| **Solo nuevo** | Usa exclusivamente el path nuevo. Sin fallback a Legacy. Solo para pruebas controladas. |

> **Recomendación:** mantén **Híbrido** en producción. El fallback automático a Legacy garantiza que una mala configuración no deja al usuario sin imprimir.

---

## 7. Verificar con Trazas

Tras imprimir cualquier documento, puedes ver exactamente qué ha hecho el sistema:

`Wex Print → Trazas`

### Columnas clave

| Columna | Qué indica |
|---------|-----------|
| **Código de documento** | El tipo de documento que se imprimió |
| **Modo ejecutado** | `Legacy` o `Híbrido` — qué path se usó realmente |
| **Resolución nueva encontrada** | `True` = el sistema encontró una asignación para el path nuevo |
| **Impresora (nueva)** | Nombre de impresora que habría (o ha) usado el path nuevo |
| **Coincide con legacy** | `True` = ambos paths habrían usado la misma impresora (señal de configuración consistente) |
| **Éxito** | `True` = la impresión se envió sin error |
| **Mensaje** | Si hay warnings de compatibilidad de dispositivo, aparecen aquí |

### Diagnóstico rápido

| Síntoma | Causa probable |
|---------|---------------|
| `Resolución nueva encontrada = False` | No hay asignación para ese documento, o `Activar resolución nueva` no está marcado |
| `Modo ejecutado = Legacy` aunque modo sea Híbrido | `Activar resolución nueva` desmarcado en la asignación |
| `Éxito = False` | Error en QZ (impresora apagada, nombre incorrecto, QZ no conectado) |
| Warning en Mensaje | El dispositivo no tiene ese reporte en sus `Reportes compatibles` |

---

## 8. Vuelta atrás de emergencia

### Revertir un solo documento

En la asignación del documento problemático, desactiva:
```
☐ Activar resolución nueva
```
Ese documento vuelve inmediatamente a Legacy. No requiere reinicio ni actualización de módulo.

### Revertir todos los documentos a la vez

`Ajustes → Wexplay Print / QZ → Opciones Avanzadas → Modo de Resolución → Legacy`

Todos los documentos ignoran perfiles y asignaciones y vuelven a la configuración antigua de usuario/empresa.

---

## 9. Referencia rápida de documentos

Tipos de documento preconfigurados en el sistema:

| Código | Nombre | Módulo | Modelo Odoo | Tipo |
|--------|--------|--------|-------------|------|
| `product_label` | Product Label | wexplay_product_print | product.template | Etiqueta |
| `sat_label_main` | SAT Main Label | wexplay_sat_print | repair.order | Etiqueta |
| `sat_label_accessory` | SAT Accessory Label | wexplay_sat_print | repair.order | Etiqueta |
| `sat_ticket` | SAT Thermal Ticket | wexplay_sat_print | repair.order | Térmica |
| `sat_a4` | SAT A4 Document | wexplay_sat_print | account.move | A4 |

Estos códigos son los que se usan en el campo **Tipo de documento** de las asignaciones.
