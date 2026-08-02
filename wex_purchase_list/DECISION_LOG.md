# Wex Purchase List Decision Log

## Decisión: mantener una lista de compra paralela al reabastecimiento de Odoo

Estado:
- activa

Motivo:
- el sistema de reabastecimiento nativo se considera demasiado complejo para la operativa diaria del equipo
- se necesita una forma rápida y manual de registrar necesidades de compra

Consecuencia:
- el módulo convive con Odoo estándar, pero no lo sustituye

## Decisión: replicar la lógica operativa de una antigua Google Sheet

Estado:
- activa

Motivo:
- antes del módulo se trabajaba con una hoja compartida
- negocio necesitaba mantener campos y señales operativas similares:
  - reserva
  - cliente avisado
  - precio informado al cliente
  - estados visuales sencillos

Consecuencia:
- el modelo actual refleja más una hoja operativa interna que un flujo de compra puramente estándar

## Decisión: centralizar la creación de líneas en `add_from_origin()`

Estado:
- activa

Motivo:
- evitar duplicar lógica entre producto, venta y SAT

Consecuencia:
- es el principal punto de verdad del módulo
- también es uno de los puntos de deuda más importantes porque ya mezcla demasiadas responsabilidades

## Decisión: crear una RFQ nueva por proveedor

Estado:
- activa

Motivo:
- es el comportamiento actual esperado por negocio
- no se pretende reutilizar RFQ borrador existentes

Consecuencia:
- el flujo actual es simple y predecible
- si en el futuro se quiere reutilizar borradores, habrá que rediseñar la lógica de agrupación

## Decisión: documentar `ordered` según comportamiento actual, no según intención futura

Estado:
- activa

Motivo:
- negocio ha pedido documentación honesta del estado actual

Comportamiento actual:
- `ordered` se asigna al crear la RFQ desde la lista

Nota:
- la intención futura sería que `ordered` represente compra confirmada al proveedor, pero hoy no funciona así

## Decisión: mantener `wex_vendor_url`

Estado:
- activa

Motivo:
- el equipo necesita abrir manualmente los enlaces del proveedor para realizar pedidos

Consecuencia:
- `wex_vendor_url` es funcionalidad real del módulo y no debe tratarse como residuo accidental

## Decisión: dejar la parte de pricing/margen documentada como deuda viva

Estado:
- activa con deuda

Motivo:
- se añadió intencionadamente para ayudar a calcular precios desde producto
- hoy no funciona correctamente

Consecuencia:
- no debe documentarse como parte sólida del flujo principal
- debe quedar marcada para corrección futura
- mientras no se corrija, no debe usarse como referencia de arquitectura para crecer el módulo

## Decisión: usar una vista operativa propia como entrada principal del módulo

Estado:
- activa

Motivo:
- la lista estándar de Odoo se queda corta para el uso diario del equipo
- negocio necesita una vista más cercana a una hoja operativa con bloques, agrupaciones y acciones rápidas

Consecuencia:
- la acción principal del módulo entra por `wex_operational_list`
- la UI de compras y reservas debe priorizar velocidad de lectura y manipulación
- los cambios visuales relevantes de esta vista deben seguir documentándose porque ya forman parte del flujo real, no de una capa cosmética

## Decisión: permitir marcar cliente avisado desde la propia vista operativa

Estado:
- activa

Motivo:
- cuando una reserva ya está recibida, el paso operativo habitual es avisar al cliente cuanto antes
- obligar a abrir cada ficha añade fricción innecesaria

Consecuencia:
- la acción `action_mark_customer_notified()` debe estar disponible desde lista, reservas y formulario
- el cambio no altera reglas de negocio: solo puede ejecutarse en reservas recibidas y con cliente
- la trazabilidad mínima del aviso sigue registrándose en el origen funcional cuando existe

## Decisión: conservar la edición directa de fila y ampliar solo la zona de selección

Estado:
- activa

Motivo:
- la compra diaria requiere seleccionar muchas líneas con rapidez, pero abrir la ficha completa sigue siendo la forma más ágil de corregir producto, proveedor o cantidad
- convertir toda la fila en selector introduciría un modo de interacción adicional y ralentizaría la edición puntual

Consecuencia:
- el clic habitual sobre la fila mantiene la apertura de la ficha
- la primera franja de cada línea es un objetivo de selección amplio y explícito
- la vista ofrece selección total sobre las líneas visibles y conserva la selección durante la navegación de vuelta
- la alternativa secuencial de enlaces se descartó porque no resolvía el caso de uso de abrir todos los proveedores desde una única acción

## Decisión: probar apertura múltiple con enlaces HTML nativos

Estado:
- en validación

Motivo:
- la apertura mediante varias llamadas a `window.open()` y la alternativa secuencial no satisfacen la necesidad de revisar varios proveedores desde una sola acción
- los enlaces nativos con `target="_blank"` se ejecutan de forma síncrona dentro del gesto del usuario y pueden recibir un tratamiento menos restrictivo del navegador

Consecuencia:
- el botón de la vista operativa intenta abrir una pestaña por cada URL seleccionada sin esperas, RPC ni temporizadores
- el resultado final sigue condicionado por la política de ventanas emergentes del navegador y debe validarse con popups permitidos para `localhost:8069`

## Decisión: descartar la apertura masiva de enlaces

Estado:
- activa

Motivo:
- incluso usando enlaces HTML nativos, el navegador no autorizó de forma fiable una pestaña por URL seleccionada
- insistir en esa interacción introduciría una promesa que el módulo web no puede garantizar

Consecuencia:
- se elimina la acción de apertura múltiple y su lógica JavaScript asociada
- cada línea conserva un único enlace de proveedor, convertido en un objetivo de clic amplio dentro de su columna `Enlace`
- la selección se guarda solo durante un máximo de cinco minutos y se consume al volver a la vista; una recarga completa la descarta

## Decisión: usar HERO y acciones rápidas en Reservas

Estado:
- activa

Motivo:
- las agrupaciones verticales por seguimiento pierden legibilidad cuando crecen las reservas
- el aviso al cliente es una acción repetitiva que no debe obligar a abrir cada ficha

Consecuencia:
- Reservas tiene una vista XML operativa propia que reutiliza la infraestructura de la lista general sin acoplar sus dos UX
- el HERO presenta cuatro estados operativos en orden de prioridad: retraso, llegada, aviso pendiente y aviso completado
- WhatsApp se mantiene disponible si hay cliente; el marcado de aviso solo aparece cuando Python permitiría ejecutarlo
- Reservas no muestra selección múltiple porque no tiene una acción masiva válida y crear RFQ desde ese contexto induciría a error

## Decisión: controlar reservas de venta por cotización comercial

Estado:
- activa

Motivo:
- las ventas de equipos a medida contienen muchos componentes que no deben producir avisos individuales al cliente
- una decisión única por cotización resuelve el caso frecuente sin introducir diez excepciones por línea

Consecuencia:
- `Marcar como reserva` está activo por defecto en cotizaciones comerciales independientes
- al desactivarlo, los productos añadidos desde esa venta no se crean como reserva y se sincronizan las líneas activas aún no avisadas
- la opción queda fuera de cotizaciones SAT para mantener `stock.move.wex_is_reservation` como única fuente de verdad de sus piezas
- el cambio se limita a cotizaciones en borrador o enviadas y no borra avisos históricos
