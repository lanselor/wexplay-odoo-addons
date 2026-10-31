# Wex Purchase List Decision Log

## Aceptación funcional y comienzo del uso diario — 01/11/2026

El usuario confirma que la versión `18.0.1.5.0` funciona correctamente y solicita documentar todos los cambios. Se registra la aceptación del comportamiento probado y el paso a observación durante el trabajo diario, sin declarar completadas pruebas prolongadas, despliegues o escenarios que no se han especificado. Se conserva el historial de decisiones y se consolida el alcance en `RELEASE_NOTES.md`, además de añadir entradas al registro general del proyecto. Esta actualización solo modifica documentación.

Durante el uso real se observarán la separación física de piezas, correspondencia de cantidades y lotes con las cajas, preparación/validación de los envíos, referencias de proveedor, nuevas solicitudes SAT y resoluciones excepcionales. La web del proveedor, los abonos y el circuito completo de RMA con sustitución mantienen el alcance y las limitaciones ya acordados.

## Decisión: motivos y salidas excepcionales sin alterar el circuito normal — 01/11/2026

Versión `18.0.1.5.0`. Se acuerda motivo predefinido por devolución con observaciones, obligatorias en Otro. Las piezas ya registradas mantienen su historial sin motivo inventado. Solicitar otro repuesto es una decisión opcional del técnico: solo se ofrece en SAT no finalizados ni entregados, crea una pieza nueva y una necesidad de compra, nunca reutiliza la retirada ni representa un RMA con sustitución. Resolver sin enviar es excepcional y opcional: recuperar para uso, anotar revisión sin bloquear el envío o preparar un desecho nativo. Las decisiones conservan usuario, fecha, explicación y documentos; las cantidades se calculan desde inventario y permiten parciales. Recuperar no reasigna automáticamente al documento de origen ni limita el uso posterior. Las reservas activas se resuelven desde sus documentos nativos, sin cancelarlas silenciosamente. La gestión habitual del proveedor y el abono siguen independientes.

## Decisión: aplazar el circuito RMA con sustitución — 01/11/2026

El usuario confirma que el taller tramita muchas devoluciones y pocos RMA con sustitución. El diseño inicial cubre devoluciones y no contempla el seguimiento completo de una sustituta. Se documenta esta carencia como deuda técnica en `ARCHITECTURE.md`; el circuito completo de sustitución permanece pendiente. En el momento de esta anotación se estaban evaluando motivos, nueva solicitud y destino de piezas no enviadas; esas tres funciones se aprobaron e implementaron después en `18.0.1.5.0`, según la decisión correspondiente, sin convertirlas en gestión de RMA con sustitución.

## Decisión: compartir los estilos existentes con la modal

Versión `18.0.1.4.3`. A petición del usuario se revisa el CSS de Lista de la compra y Reservas y se reutilizan sus clases de cabecera, paneles, títulos con iconos y tipografía. Se amplía el alcance de los selectores comunes únicamente a la modal de devolución. El CSS específico conserva ajustes de tamaño y distribución; no replica la estética ni modifica la lógica del asistente.

## Corrección: compatibilidad de visibilidad con el cliente web

Versión `18.0.1.4.2`. El evaluador JavaScript de Odoo 18 no admite `len()` en los modificadores de esta vista aunque su validación Python los acepte. La cantidad de opciones se decide ahora en `_compute_choices()` mediante dos booleanos no almacenados y XML solo consulta esos resultados. Se reproduce el fallo con el evaluador JavaScript nativo y se verifican las expresiones corregidas para los estados permitido/bloqueado, SAT/venta y distintos seguimientos.

## Decisión: simplificar la ventana de devolución

Versión `18.0.1.4.1`. La captura de uso real mostraba datos repetidos, grandes espacios vacíos y una asignación comprimida en una columna estrecha. Se priorizan pieza, cantidad, efecto sobre SAT/venta y confirmación. Los bloqueos aparecen al inicio y los detalles secundarios quedan plegados. Se conserva la validación Python existente y se usan componentes nativos con CSS limitado al formulario, sin un asistente paralelo ni frontend adicional.

## Decisión: conservar el origen histórico al cerrar la revisión

Estado: Fase 4, versión `18.0.1.4.0`.

- Guardar la referencia SAT como dato histórico de la devolución, sin hacerla depender de posteriores ediciones de la línea interna.
- Conservar la venta del SAT aunque se retire su primera pieza; tomarla del documento de reparación.
- Bloquear reasignaciones manuales del origen cuando ya existe trazabilidad, manteniendo las retiradas nativas por eliminación de pieza o línea.
- Verificar cantidades en unidad base con recepciones en otra unidad de compra y preparación de documentos de varias compañías sin mezclarlas.
- Mantener las actualizaciones idempotentes y conservar configuración e historial previos. No cambiar de almacén de archivos ni debilitar permisos del servicio para actualizar.
- Entregar una guía con los resultados de stock esperados y los límites del flujo; la gestión externa y los abonos permanecen fuera de la automatización.

## Decisión: documentos nativos por recepción y validación de envío separada

Estado: Fase 3.

- La lista Devoluciones muestra cantidades y estados derivados de movimientos, con selección múltiple y agrupación por proveedor.
- Crear documentos mediante el asistente nativo por recepción y ubicación, conservando su proveedor y vínculo documental. La preparación reserva; Validar registra el envío físico.
- Asignar RMA común solo a piezas de la misma compañía y proveedor comercial; mantener edición individual y referencias externas opcionales.
- Mantener un marcador de trazabilidad en los movimientos nativos y en sus divisiones/backorders. Conservar todos los documentos, incluidas cancelaciones y entregas parciales, sin reemplazar el primer vínculo.
- Filtrar las líneas del asistente y bloquear dependencias pendientes seleccionadas para evitar liberar reservas ajenas. Reservar los documentos nuevos al final del lote, respetando las llamadas nativas.
- Añadir el traslado de apartamiento como abastecimiento real de la devolución sin sustituir la referencia de la recepción original.
- Respetar los destinos de las devoluciones inversas y separar la identidad de unidades de reemplazo en intercambios nativos.
- Proteger la validación de salidas frente a proveedor/lote equivocados, sobrecantidades y existencias físicas insuficientes, sin crear ajustes de inventario.

## Decisión: apartar mediante traslado interno nativo y confirmación del origen

Estado: Fase 2.

- Identificar recepción y movimiento reales; admitir recepción parcial sin depender del estado interno `received`.
- Reservar unidades exactas con las APIs de stock, incluyendo lote/serie y paquete cuando existen. Excluir stock de terceros.
- Mantener activo el contrato de permisos nativos: el rol de responsable del módulo no concede derechos adicionales de Inventario, Ventas o Contabilidad.
- Reducir una venta confirmada sin cancelar ni reabrir el pedido; eliminar la línea solo si la cotización sigue editable y la cantidad queda a cero.
- Dejar que los métodos de `stock.move` del SAT sincronicen su venta. Bloquear piezas utilizadas, entregadas, facturadas o con una relación ambigua que requiera revisión manual.
- Conservar la venta de origen aunque desaparezca una línea editable. Conservar también los avisos históricos; retirar el aviso pendiente de una reserva que se aparta por completo.
- Revertir ajustes de origen y traslado juntos si falla cualquier comprobación. Usar reintentos transaccionales de Odoo ante concurrencia y evitar duplicados al repetir un mismo asistente.
- No activar automáticamente tipos internos archivados ni alterar rutas de almacén: su ausencia se informa como configuración pendiente.

## Decisión: base de devoluciones por fases sobre inventario nativo

Estado: Fase 1 implementada en código; las acciones operativas pertenecen a fases posteriores.

- Mantener en este módulo la configuración por compañía y la trazabilidad auxiliar, usando movimientos y devoluciones nativas para el inventario.
- Crear la ubicación predeterminada fuera del stock habitual y permitir reemplazarla desde Ajustes. Las actualizaciones respetan una selección existente.
- Aplicar a la nueva trazabilidad una regla global por compañías permitidas, también para managers.
- Separar el RMA externo de las operaciones internas: es una referencia opcional, no demuestra aceptación por el proveedor.
- No implementar plazos, recogidas, abonos ni integración con webs de proveedores en esta fase.
- No ofrecer creación manual de operaciones desde una base de trazabilidad incompleta: las comprobaciones de cantidades disponibles, asignaciones y concurrencia se incorporarán con el asistente de la Fase 2.

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
