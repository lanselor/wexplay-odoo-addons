# Wexplay Portal - Architecture

## Objetivo

`wexplay_portal` es la capa puente entre el portal nativo de Odoo y los modulos
de negocio de Wexplay.

Su responsabilidad no es duplicar logica SAT ni de facturacion, sino exponerla
de forma segura y mantenible en un portal B2B autenticado para clientes empresa.

En esta fase:

- reutiliza el portal nativo de facturas de `account`
- expone SAT basados en `repair.order`
- prepara un punto de entrada futuro para mantenimiento IT
- añade una portada website simple y coherente para acceso publico y acceso portal

---

## Alcance actual

Este modulo cubre:

- portal B2B autenticado con usuarios tipo portal
- home del portal con accesos a SAT y facturas
- listado de SAT accesibles para la empresa del usuario
- detalle de SAT con informacion operativa visible para cliente
- integracion con facturas relacionadas desde la ficha SAT
- visualizacion y descarga controlada de fotografias SAT
- placeholder de `Mantenimiento IT`

---

## Que NO hace este modulo

Este modulo no:

- implementa portal B2C
- expone accesos por token
- crea vistas publicas de SAT
- expone rutas genericas al DMS
- convierte `wexplay_repair` en modulo portal
- publica adjuntos o chatter del SAT
- expone followers ni relaciones indirectas sensibles
- desarrolla aun la funcionalidad real de mantenimiento IT

---

## Decision arquitectonica principal

La logica portal no debe vivir dentro de `wexplay_repair`.

`wexplay_portal` existe como capa de integracion para:

- evitar acoplar frontend portal con la base SAT
- permitir crecimiento futuro sin contaminar `wexplay_repair`
- separar mejor seguridad portal de logica operativa interna

### Regla importante

Las reglas de negocio SAT siguen viviendo en los modulos SAT.

El portal:

- consume datos
- aplica filtros y validaciones de acceso
- renderiza frontend

Pero no debe convertirse en el nuevo centro de verdad del flujo SAT.

---

## Dependencias

Dependencias funcionales actuales:

- `portal`
- `website`
- `account`
- `wexplay_repair`

### Criterio

- `website` es obligatorio
- `account` se reutiliza, no se duplica
- `wex_it_maintenance` no es dependencia dura en esta fase

---

## Relacion con otros modulos

### `wexplay_repair`

Aporta:

- base SAT
- campos SAT
- helpers funcionales compartidos
- integracion documental base

`wexplay_portal` no debe mover logica fuerte de SAT aqui.

### `wexplay_repair_images`

Aporta:

- gestion backend de fotografias SAT
- clasificacion y almacenamiento DMS

`wexplay_portal` solo expone fotografias de forma segura en frontend.

### `account`

El portal de facturas debe seguir siendo el nativo.

El criterio es:

- enlazar con el portal estandar
- no reinventar rutas ni controladores de factura
- usar integracion desde SAT solo como capa de navegacion

### `wex_it_maintenance`

En esta fase solo se prepara integracion visual.

La entrada aparece si el cliente tiene marcado:

- `x_is_it_maintenance_customer = True`

No se debe acoplar aun funcionalidad de mantenimiento IT al portal SAT.

---

## Usuarios objetivo

Este portal esta pensado para:

- clientes empresa
- usuarios autenticados de tipo portal
- acceso por empresa comercial, no por acceso puntual a un unico SAT

### Regla de negocio clave

La unidad de acceso en portal es el `commercial_partner_id`.

Esto permite que:

- un contacto hijo de empresa vea el historial de su empresa
- no se limite la visibilidad solo al contacto exacto

---

## Seguridad

La seguridad es la restriccion mas importante de este modulo.

### Principios no negociables

- el usuario portal solo ve sus propios datos
- no confiar en filtros visuales
- no abrir rutas publicas para SAT
- no exponer DMS de forma directa
- no usar `sudo()` en controladores
- cualquier `sudo()` puntual en modelos debe quedar encapsulado y precedido por validacion de acceso al SAT

### Capas de seguridad

#### 1. ACL

Portal tiene permisos de solo lectura sobre `repair.order`.

#### 2. Record rules

La visibilidad de SAT se limita por partner comercial.

#### 3. Controladores

Las rutas del portal buscan siempre dentro del dominio visible del usuario.

Un acceso manual a registros ajenos debe responder `404`.

Si una accion portal valida necesita despues disparar workflow interno o logica
comercial sensible, el controlador no debe resolverlo abriendo permisos al
usuario portal sobre modelos de backend. La validacion sigue siendo del usuario
portal, pero la ejecucion tecnica sensible debe quedar encapsulada en modelo y
aislada del entorno ORM del cliente cuando haga falta tocar modelos como
`sale.order` o sus lineas.

#### 4. Exposicion de imagenes

Las fotos SAT no se sirven desde rutas genericas de DMS.

Se sirven mediante una ruta portal vinculada al SAT:

- primero se valida acceso al SAT
- despues se valida pertenencia de la imagen a ese SAT

### Datos que NO deben exponerse

- `x_internal_notes`
- chatter
- followers
- adjuntos genericos
- relaciones peligrosas que den acceso indirecto a backend

### Datos que SI pueden exponerse si negocio lo confirma

- `internal_notes` como diagnostico visible para cliente

### Regla critica

`x_internal_notes` es observacion interna del tecnico y no debe mostrarse
nunca en portal.

`internal_notes` es el campo nativo usado como diagnostico visible al cliente.

---

## Experiencia de portal

### Home publica y acceso

La web publica no debe quedarse en blanco.

Regla:

- un usuario portal que caiga en `/` debe ser redirigido a `/my`
- un usuario no autenticado debe ver una portada website simple y util

### Home de portal

La home del portal debe mantener el lenguaje nativo de Odoo y añadir:

- Servicio Tecnico
- Mantenimiento IT si aplica

### SAT listado

El listado SAT debe priorizar:

- `Activos` como filtro por defecto
- `Finalizados`
- `Todos`

La busqueda debe ser controlada por selector previo para evitar dominios
fragiles y errores de permisos.

### SAT detalle

La ficha SAT debe aportar contexto real para cliente empresa:

- referencia SAT
- referencia cliente
- estado SAT
- recorrido de estados
- diagnostico visible
- garantia
- piezas y servicios
- acceso a facturacion relacionada
- fotografias SAT

El recorrido de presupuesto puede mostrar `No reparable` cuando el diagnostico
interno determina que no hay solucion tecnica viable. Ese estado se consume del
workflow SAT y no implica cancelacion de la reparacion ni exposicion de notas
internas.

La ficha SAT incluye una barra contextual sticky propia del portal base para
mantener visibles durante el scroll:

- acceso a `Mi cuenta`
- referencia SAT
- referencia cliente si existe
- dispositivo
- estado principal visible para el cliente

Los modulos puente pueden extender esa barra para anadir acciones especificas,
pero la barra base no debe depender de flujos concretos como presupuesto,
imagenes o mantenimiento IT.

---

## Facturacion

La facturacion del portal debe reutilizar `account`.

### Decision clave

No crear portal de facturas paralelo.

El detalle SAT puede enlazar facturas relacionadas, pero:

- la visualizacion de factura sigue siendo la nativa
- los breadcrumbs y contexto QWeb no deben romper plantillas del portal estandar

---

## Fotografias SAT

La integracion de fotografias en portal fue tratada como zona sensible.

### Criterios

- no exponer ids o rutas genericas del DMS
- no abrir navegacion de carpetas
- no sacar al usuario del portal al abrir una imagen
- permitir descarga controlada
- mostrar metadatos utiles: nombre, descripcion, etiquetas

### UX decidida

- miniaturas dentro de la ficha SAT
- filtros por etiqueta
- modal de previsualizacion
- boton de descarga

### Restriccion importante

La arquitectura de exposicion de imagenes debe seguir acotada al SAT
autorizado, no al repositorio documental.

---

## Portal y mantenimiento IT

La integracion con mantenimiento IT es deliberadamente pequena.

### En esta fase

- solo se muestra la entrada si el partner cumple condicion
- no se desarrolla aun su backend funcional
- no se deben inventar modelos o rutas complejas por anticipacion

---

## UI y estilo

La UI del portal debe seguir una linea hibrida:

- portal Odoo reconocible
- jerarquia visual mas cuidada
- identidad Wexplay integrada con moderacion

### Reglas practicas

- no sobrecargar de frontend innecesario
- SCSS propio solo donde aporte claridad
- priorizar legibilidad, estados, tablas y bloques funcionales
- evitar una portada vacia o sin contexto

---

## Rutas principales

- `/`
- `/my`
- `/my/invoices`
- `/my/repairs`
- `/my/repairs/<id>`
- `/my/repairs/<repair_id>/images/<image_id>`
- `/my/it-maintenance`

---

## Checklist para futuras iteraciones

Antes de tocar este modulo conviene verificar:

- si el cambio pertenece realmente a portal o a SAT base
- si rompe la separacion B2B / B2C
- si intenta exponer datos tecnicos internos
- si toca DMS de forma directa
- si duplica funcionalidad nativa de facturas
- si requiere mover una eleccion hardcodeada a configuracion

---

## Deuda tecnica pendiente

Puntos detectados para sanear en futuras iteraciones, sin bloquear el MVP actual:

- Encapsular en modelo el `sudo()` usado para servir fotografias SAT desde portal,
  manteniendo siempre una validacion previa de acceso al SAT.
- Revisar si la integracion con imagenes SAT debe ser dependencia explicita o
  integracion opcional completamente defensiva frente a ausencia de modelos/campos.
- Reducir llamadas directas a helpers desde QWeb cuando el detalle SAT siga
  creciendo, preparando mas valores desde Python y dejando las plantillas mas
  centradas en renderizar.
- Formalizar para futuras refactorizaciones el flujo de diagnostico, plan,
  fases pequenas y documentacion tecnica antes de tocar codigo.
- Revisar periodicamente que las acciones portal que disparan workflow interno
  sigan ejecutandose con el menor privilegio posible sin introducir ACL
  peligrosas en modelos comerciales o logistico-financieros.

---

## Decisiones que no deberian reabrirse sin motivo fuerte

- portal solo B2B autenticado en esta linea
- `wexplay_portal` como capa puente separada
- portal de facturas nativo reutilizado
- acceso SAT por partner comercial
- `x_internal_notes` fuera del portal
- `internal_notes` como diagnostico visible
- imagenes servidas por ruta segura del portal y no por DMS directo
- `website` como dependencia obligatoria
