# Registro de errores y correcciones

## Formato

### Fecha

YYYY-MM-DD

### Error

Descripcion del error.

### Causa

Causa raiz detectada.

### Solucion

Correccion aplicada.

### Prevencion

Medida para evitar que se repita.

---

## Fecha

2026-05-17

## Error

El despiece guardaba correctamente el foco interno (`pieces` / `data_completion`)
pero, al volver a abrir el formulario, el notebook seguia aterrizando en
`Dispositivo`.

## Causa

Se intento forzar la pestana activa desde un widget de campo ligado a
`workflow_focus`. En Odoo 18 el notebook no queda gobernado de forma fiable por
ese campo, sino por el ciclo de render del `FormRenderer`. Ademas, en varias
pruebas la caché de assets hacia parecer que el cambio no funcionaba aunque el
codigo ya estuviera bien orientado.

## Solucion

Se cambio el enfoque: las `page` del notebook pasaron a tener atributo `name` y
el cambio de foco se movio a un parche de `FormRenderer`, siguiendo el mismo
patron ya usado en otros modulos Wexplay. `workflow_focus` sigue siendo el dato
persistido, pero la activacion de la pestana se hace desde el renderer y no
desde un field widget local.

## Prevencion

Cuando se necesite controlar una pestana de notebook de forma persistente en
formularios Odoo, no intentar resolverlo solo con un widget de campo. Preferir
`page[name=...]` mas logica en `FormRenderer` o un punto global de render.
Despues de cambios frontend, forzar recarga de assets antes de dar por roto el
comportamiento.

---

## Fecha

2026-05-17

## Error

Las acciones `Ver ficha` y rechazo de pieza lanzaban en frontend errores tipo
`Cannot read properties of undefined (reading 'map')`.

## Causa

Las acciones `ir.actions.act_window` devueltas desde Python no incluian la clave
`views`. El cliente web de esta instalacion esperaba una estructura mas
completa para preprocesar correctamente la accion.

## Solucion

Se actualizaron las acciones de apertura de formulario y wizard para devolver
`views` explicito con el formulario correspondiente, tanto en la ficha de pieza
como en el wizard de rechazo y la apertura de `product.template`.

## Prevencion

Cuando se construyan `act_window` manualmente para consumo desde widgets OWL,
devolver siempre `views` de forma explicita si el flujo depende del cliente web
moderno. Eso reduce diferencias entre instalaciones y evita errores opacos en
frontend.
