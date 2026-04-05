# Wexplay Repair Images – Architecture

## Objetivo

`wexplay_repair_images` es el módulo de integración entre SAT (`repair.order`) y el sistema reusable de imágenes definido en `wexplay_image_core`.

Este módulo no implementa un sistema de imágenes desde cero.
Su responsabilidad es adaptar el core de imágenes al flujo de trabajo de reparaciones de Wexplay.

---

## Alcance de este módulo

Este módulo permite, dentro de `repair.order`:

- subir imágenes desde la pestaña **Imágenes**
- guardar las imágenes en la carpeta DMS correspondiente a la orden SAT
- visualizar miniaturas dentro del formulario
- abrir una preview ampliada ligera
- añadir descripción a cada imagen
- clasificar imágenes mediante etiquetas controladas
- mantener orden y trazabilidad básica

---

## Qué NO hace este módulo

Este módulo no:

- implementa la lógica genérica de imágenes
- duplica la lógica de integración con DMS
- crea una arquitectura de portal
- define permisos de cliente o portal
- expone imágenes públicamente
- añade etiquetas libres
- acopla el sistema a un solo caso de uso futuro

La lógica reusable vive en `wexplay_image_core`.

---

## Dependencias

Este módulo depende de:

- `repair`
- `wexplay_repair`
- `wexplay_image_core`
- módulo DMS/OCA usado por el proyecto
- `wex_consent`, porque hoy es quien introduce la notebook SAT con pestañas de firmas e imágenes

---

## Relación con `wexplay_image_core`

`wexplay_repair_images` consume el core y añade contexto SAT.

### El core aporta

- modelo genérico de imágenes
- etiquetas
- metadatos
- servicios de subida
- integración con DMS
- previews y miniaturas reutilizables

### Este módulo aporta

- relación con `repair.order`
- pestaña de imágenes en SAT
- estructura de carpeta SAT para fotos
- etiquetas por defecto para SAT
- UX adaptada al flujo del taller

---

## Estructura DMS SAT

La estructura objetivo para SAT sigue la convención del ecosistema Wexplay ya usada por firmas:

`SAT/<NUMERO_SAT>/IMAGES`

Y convive con otras carpetas hermanas como:

- `SAT/<NUMERO_SAT>/DOCUMENTS`
- `SAT/<NUMERO_SAT>/SIGNATURES`

### Regla importante

La resolución o creación de carpetas SAT no está hardcodeada en varios sitios.

Existe una lógica única en `wexplay_repair` para:

- localizar la carpeta raíz de SAT
- localizar la carpeta propia de la orden
- localizar o crear subcarpetas funcionales como `IMAGES`

---

## Etiquetas SAT por defecto

En esta fase, SAT utiliza etiquetas controladas.

Etiquetas iniciales:

- `entrada`
- `diagnostico`
- `dano_externo`
- `interior`
- `reparacion`
- `resultado_final`
- `accesorios`
- `humedad`

### Criterio

Las etiquetas:

- no son libres
- se mantienen consistentes
- sirven para filtros y ordenación futura
- no implican todavía lógica de portal

---

## Diseño de la vista en `repair.order`

La pestaña **Imágenes** es operativa para uso diario de taller.

### Elementos incluidos

- acción para subir una o varias imágenes
- listado visual con miniaturas
- descripción visible
- etiquetas visibles como badges
- orden por secuencia
- acceso a preview ampliada ligera
- acceso al documento DMS original

### Criterio UX

No se busca un visor complejo.
La prioridad es una interfaz:

- rápida
- mantenible
- útil en mostrador y taller
- coherente con el backend actual de Wexplay

---

## Portal

Este módulo no implementa portal.

### Sí deja preparado

- estructura de datos ordenada
- clasificación por etiquetas
- orden consistente
- separación clara entre core e integración SAT

### No incluye todavía

- visibilidad cliente
- rutas públicas
- control de acceso portal
- frontend portal
- optimizaciones específicas para exposición externa

---

## Seguridad

Los permisos están orientados a usuarios internos.

En esta fase, usuarios SAT autorizados pueden:

- ver imágenes
- subir imágenes
- editar descripción y clasificación
- eliminar imágenes

No se implementan permisos de cliente ni reglas de portal.

---

## Decisiones de diseño

### 1. Separación core / vertical

La lógica reusable vive en `wexplay_image_core`; la integración SAT vive en este módulo.

### 2. DMS como almacenamiento real

Las imágenes se almacenan en DMS; la experiencia de usuario se articula sobre el modelo del core.

### 3. Etiquetas controladas

Se evita el uso de etiquetas libres para mantener consistencia futura.

### 4. Sin lógica prematura de portal

Se prioriza una base sana antes de definir arquitectura pública.

---

## Límites de esta primera fase

Esta versión se centra en:

- backend
- SAT
- integración DMS
- clasificación controlada
- preview ligera
- estructura reutilizable

Queda fuera de alcance:

- portal cliente
- publicación externa
- permisos avanzados de compartición
- automatizaciones complejas por etiqueta
- edición masiva sofisticada
- reordenación drag and drop avanzada
