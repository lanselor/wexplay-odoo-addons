# Wexplay Image Core – Architecture

## Objetivo

`wexplay_image_core` es el módulo base reutilizable para la gestión de imágenes dentro del ecosistema Wexplay en Odoo 18 Community.

Su propósito es centralizar la lógica común necesaria para:

- registrar imágenes
- clasificarlas
- ordenarlas
- relacionarlas con registros de distintos modelos
- integrarlas con DMS
- ofrecer miniaturas y previews reutilizables

Este módulo sirve como base para integraciones verticales como SAT, mantenimientos IT u otros futuros casos de uso.

---

## Responsabilidades del core

Este módulo es responsable de:

- modelo genérico de imágenes
- catálogo de etiquetas
- metadatos de imagen
- asociación flexible a registros de otros modelos
- enlace con documentos DMS
- helpers de subida
- helpers de preview y miniatura
- ordenación
- seguridad base
- vistas mínimas de administración

---

## Qué NO debe hacer

`wexplay_image_core` no debe:

- conocer `repair.order`
- contener reglas de negocio SAT
- contener rutas o lógica de portal
- asumir carpetas DMS específicas de un módulo concreto
- implementar UX específica de un vertical
- convertirse en un framework sobredimensionado

La lógica específica debe vivir en módulos consumidores como `wexplay_repair_images`.

---

## Modelo de datos

### 1. Etiquetas

`wex.image.tag` es un catálogo controlado para clasificar imágenes.

Objetivos:

- evitar etiquetas libres
- garantizar consistencia
- permitir filtros y agrupaciones futuras

### 2. Registro de imagen

`wex.image.record` es el modelo genérico para representar una imagen vinculada a un registro de negocio.

Almacena:

- metadatos
- clasificación
- orden
- enlace al documento físico en DMS
- información mínima de subida y trazabilidad

La relación de negocio se resuelve mediante `res_model` + `res_id` como punto de verdad genérico. Los módulos verticales pueden añadir relaciones tipadas de conveniencia si aportan valor a su UX.

---

## Relación con DMS

El almacenamiento real de archivos se apoya en DMS.

### Criterio

- el core gestiona la integración técnica con `dms.file`
- los módulos verticales deciden la carpeta funcional concreta
- la resolución de carpetas debe encapsularse fuera del core cuando dependa del dominio

El core no hardcodea estructuras como:

- `SAT/<NUM>/IMAGES`
- `IT/<CLIENTE>/ASSETS`

Eso pertenece a los módulos consumidores o a helpers compartidos del dominio.

---

## Consumo desde otros módulos

Los módulos verticales deben usar este core para:

- crear imágenes desde subidas
- enlazar imágenes a su registro de negocio
- definir sus carpetas funcionales DMS
- decidir su UX concreta
- aportar etiquetas por defecto si procede

### Ejemplos de consumidores esperados

- `wexplay_repair_images`
- futuros módulos de mantenimiento IT
- futuros módulos de activos o incidencias

---

## Seguridad

El core define grupos y permisos base para usuarios internos autorizados.

No incluye todavía:

- reglas de acceso portal
- compartición pública
- exposición externa de archivos

---

## Principios de diseño

### 1. Reutilización real

El core debe poder servir a varios módulos sin copiar lógica.

### 2. Bajo acoplamiento

Los verticales dependen del core, pero el core no depende de ellos.

### 3. DMS encapsulado

La integración con DMS queda centralizada en el modelo de imagen.

### 4. Sin sobrediseño

La arquitectura es extensible, pero pragmática.

### 5. Preparado para el futuro, sin adelantar portal

El modelo es sólido para futuras extensiones, pero sin meter aún lógica de cliente o publicación.

---

## Decisiones clave

- imágenes como recurso transversal
- etiquetas siempre controladas
- DMS como almacenamiento físico real
- UX específica fuera del core
- sin portal en la primera fase

---

## Límites de esta fase

El core cubre:

- backend
- clasificación
- metadatos
- integración DMS
- soporte reusable

Queda fuera:

- portal
- visibilidad pública
- permisos cliente
- frontends externos
- workflows específicos por vertical
