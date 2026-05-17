# AGENTS.md

## Objetivo del proyecto
Desarrollar módulos personalizados para Odoo 18 Community dentro del ecosistema Wexplay, con foco en procesos reales de SAT, mantenimiento IT, consentimientos, firmas y flujos internos, priorizando siempre robustez, claridad y mantenibilidad a medio y largo plazo.

## Plataforma y contexto
- Odoo 18 Community
- On-premise
- Proyecto Wexplay
- Sin Studio
- Multi-company compatible
- Integración con módulos personalizados Wexplay ya existentes
- Reutilizar la lógica nativa de Odoo siempre que aporte valor real

## Principios generales
- Priorizar claridad, simplicidad y mantenibilidad
- No introducir complejidad innecesaria
- No añadir funcionalidades no pedidas
- Mantener el código fácil de revisar y retocar manualmente después
- Evitar hacks y soluciones frágiles
- Separar bien responsabilidades
- Mantener coherencia con otros módulos Wexplay
- Favorecer soluciones sobrias antes que diseños “demasiado listos”
- Cualquier complejidad nueva debe justificarse por necesidad real de negocio

## Filosofía de arquitectura
- Reutilizar al máximo la lógica nativa de Odoo y la lógica ya existente en módulos Wexplay
- No crear modelos paralelos si el modelo nativo ya resuelve bien el flujo operativo
- Preferir extensión limpia de modelos existentes frente a duplicación funcional
- Diseñar para crecer, pero sin sobrediseñar la v1
- Mantener un único punto de verdad para cada decisión de negocio importante
- La complejidad debe vivir donde realmente aporta valor, no repartida por vistas, JS y condiciones duplicadas

## Convenciones de código
- Código en inglés
- Comentarios en español solo cuando realmente ayuden
- Nombres claros, directos y semánticos
- Evitar helpers genéricos sin valor real
- Evitar abstracciones excesivas
- Mantener cambios pequeños y revisables
- No esconder la lógica importante
- Preferir la opción más simple y mantenible cuando haya duda

## Reglas de diseño del código
- Evitar cadenas largas de `if` anidados para lógica de negocio
- Extraer las decisiones de negocio a métodos pequeños con nombre claro
- Usar helpers tipo:
  - `_can_*`
  - `_is_*`
  - `_has_*`
  - `_get_*`
  - `_prepare_*`
  - `_check_*`
- Los métodos `action_*` deben ser finos y actuar como orquestadores
- Separar claramente:
  - validación
  - cálculo
  - preparación de valores
  - escritura / creación / actualización
- Priorizar guard clauses frente a `if` anidados profundos
- Si una condición se usa más de una vez, extraerla a un método reutilizable
- Preferir más métodos pequeños y claros antes que pocos métodos grandes
- Evitar métodos largos salvo necesidad muy justificada
- No mezclar demasiadas responsabilidades en `create()` y `write()`
- No duplicar reglas entre botón, wizard, modelo, XML y JS si pueden centralizarse
- No mover lógica de negocio al frontend salvo necesidad real de interfaz

## Arquitectura por capas
Organizar claramente por:
- `models`
- `security`
- `views`
- `reports`
- `wizard` si hace falta
- `data` si hace falta
- `static` solo cuando aporte valor real

Separar claramente:
- dominio de negocio
- ORM / persistencia
- seguridad
- configuración
- reportes
- frontend OWL solo si realmente aporta valor

## Flujo de implementación
- Antes de cambios grandes, explicar el plan
- Enumerar archivos a crear o modificar antes de empezar
- Explicar en una línea la responsabilidad de cada archivo
- Enumerar métodos nuevos relevantes por modelo/archivo
- Implementar por fases pequeñas
- Mantener el módulo instalable en cada fase razonable
- Añadir tests para lógica crítica cuando proceda
- No cambiar arquitectura sin explicarlo primero

## Registro de cambios del proyecto
- El archivo de gestión de cambios del proyecto es `C:\odoo18\WEXPLAY_CHANGELOG.md`
- Cuando el usuario pida actualizar el registro de cambios, añadir una nueva entrada sin sustituir las anteriores
- Cada entrada debe usar formato de tabla con estas columnas:
  - `Fecha`
  - `Módulo(s) modificados`
  - `Descripción larga de los cambios`
  - `Decisiones de negocio`
- La descripción larga debe tener al menos 200 caracteres y explicar con claridad qué se ha cambiado
- Si durante el trabajo se ha hablado, aclarado o decidido lógica de negocio, incluir en `Decisiones de negocio` las decisiones tomadas
- Las entradas deben quedar identificadas por fecha y ser útiles para reconstruir por qué se hizo cada cambio, no solo qué archivos se tocaron

## Seguridad
- Crear grupos específicos del módulo cuando tenga sentido
- Restringir datos sensibles por grupos
- No mostrar secretos en vistas lista
- Ocultar secretos por defecto en formulario
- Preparar la arquitectura para cifrado futuro si aplica
- No asumir que la ocultación visual equivale a seguridad completa
- Cualquier excepción funcional sensible debe poder restringirse por permisos o grupos

## Dependencias
- Evitar dependencias innecesarias
- Justificar cualquier dependencia no estándar antes de introducirla
- No usar Studio
- No asumir APIs de terceros u OCA sin comprobarlas

## UI
- Mantener vistas limpias y operativas
- Evitar frontend complejo salvo necesidad real
- Usar OWL solo si aporta valor claro
- Priorizar ergonomía real de trabajo diario
- Mantener la base visual nativa de Odoo 18
- No reemplazar completamente la estética de Odoo
- Integrar la identidad visual de los módulos personalizados de Wexplay ya existentes
- Buscar una estética híbrida:
  - Odoo reconocible
  - interfaz más cuidada, jerárquica y profesional
- Usar SCSS propio solo cuando aporte valor real
- Evitar estilos frágiles, hacks visuales o sobrecarga estética
- Mantener consistencia entre formularios, listas, dashboards y bloques funcionales
- Priorizar paneles claros, separación visual limpia y buena legibilidad

## Reportes
- Usar QWeb
- Diseños claros y profesionales
- Mantener separada la lógica de negocio del render del reporte
- No mezclar cálculo de negocio dentro del QWeb salvo lo mínimo imprescindible

## Qué evitar
- lógica de negocio importante dispersa en JS
- modelos ambiguos que mezclen varias responsabilidades
- hardcodes innecesarios
- sobreingeniería
- helpers genéricos sin semántica clara
- `if` anidados largos en decisiones de negocio
- métodos gigantes difíciles de revisar
- generar toda la v2 dentro de la v1
- frontend complejo para resolver problemas que deben resolverse en Python
- introducir campos, flags o modelos sin justificar el caso de negocio real

---

# Contexto específico: mantenimiento IT

## Objetivo del proyecto
Módulo Odoo 18 Community para gestionar el servicio de mantenimiento preventivo, correctivo y soporte IT básico que Wexplay presta a empresas, incluyendo clientes del servicio, activos IT, visitas, revisiones, servicios, credenciales e informes.

## Reglas funcionales clave
- Solo forman parte del sistema los `res.partner` con `x_is_it_maintenance_customer = True`
- Un activo IT debe tener identidad propia
- La visita es la unidad operativa principal
- El historial de revisiones debe normalizarse en modelo propio
- Los servicios IT deben modelarse aparte de los activos
- Las credenciales no deben tratarse como simples textos visibles
- La generación de códigos internos debe ser automática y mantenible
- El dashboard debe ser útil, no ornamental
- El informe base debe salir de la visita realizada

## MVP
- extensión de contactos
- clientes del servicio
- activos
- revisiones
- visitas
- líneas de visita
- servicios
- credenciales
- checklist por plantilla
- dashboard base
- informe QWeb por visita
- seguridad base
- menús y vistas funcionales

---

# Contexto específico: consentimientos y firmas

## Objetivo del proyecto
Desarrollar un sistema propio de consentimientos y firmas para Odoo 18 Community, integrado con `repair.order`, orientado a SAT de mostrador y con almacenamiento documental obligatorio en OCA DMS.

## Contexto funcional
El sistema debe permitir:
- firma de recepción del dispositivo
- firma de entrega del dispositivo
- recogida de consentimientos RGPD y de comunicaciones
- generación de PDFs firmados
- guardado documental en OCA DMS
- visualización de documentos firmados desde la reparación
- modo kiosko para tablet o navegador dedicado

## Plataforma y restricciones
- Odoo 18 Community
- Sin Odoo Enterprise Sign
- No usar `sign_oca` como motor principal del flujo
- Integración obligatoria con OCA DMS
- Compatibilidad con entornos on-premise
- Multiusuario
- No bloquear otras operaciones del sistema

## Principios específicos
- Mantener la integración con `repair.order` limpia y estable
- Cualquier flujo kiosko debe ser robusto y asíncrono
- Cualquier guardado documental debe seguir una estrategia DMS coherente
- Mantener estados persistidos en BD para solicitudes y cola kiosko
- Diseñar con posibilidad de reutilización futura para imágenes SAT, mantenimiento IT y otros documentos

## Integración con repair.order
El desarrollo debe incluir:
- acceso a consentimientos desde `repair.order`
- nuevo campo `descripción del dispositivo`
- nuevo notebook entre datos administrativos y el notebook ya existente de piezas/servicios/notas
- pestañas:
  - `Imágenes`
  - `Firmas`

## Documentos a firmar

### Recepción
Debe incluir:
- texto de protección de datos
- consentimientos email y WhatsApp, comerciales y no comerciales
- aceptación de condiciones de garantía
- descripción de la avería
- descripción del dispositivo
- firma del cliente

### Entrega
Debe incluir:
- descripción inicial de la avería
- notas de reparación si existen
- confirmación tipo “he revisado el dispositivo y todo está bien”
- firma del cliente

## Kiosko
- pantalla en espera
- al llegar solicitud, mostrar firma
- al terminar, volver a espera
- si llegan varias, cola
- una firma activa a la vez
- no bloquear `repair.order`
- no bloquear trabajo de otros usuarios

## Gestión documental
- Integración obligatoria con OCA DMS
- La estrategia de carpetas debe pensarse para futuro:
  - firmas
  - imágenes
  - documentos SAT
  - mantenimiento IT
- No guardar archivos de forma improvisada sin seguir la arquitectura decidida

## Dependencias y OCA
- Usar correctamente modelos y APIs de OCA DMS y repos relacionados
- Si falta contexto de OCA, pedir explícitamente qué repos se necesitan en local
- No asumir APIs sin comprobarlas
---

# Contexto específico: SAT reparación actual

## Arquitectura SAT consolidada
- `wexplay_repair` es la base SAT compartida
- `wexplay_repair_workflow` extiende presupuesto, transiciones internas y sincronización de ubicaciones
- `wexplay_repair_delivery` extiende entrega, cobro-entrega y notificación SAT
- Evitar meter reglas de workflow o entrega dentro de `wexplay_repair` salvo que sean infraestructura base compartida

## Límites funcionales SAT
- `wexplay_repair` debe concentrar:
  - campos SAT estables
  - helpers compartidos
  - configuración SAT por compañía
  - integración DMS base
  - integración factura/reportes SAT
- `wexplay_repair_workflow` debe concentrar:
  - estados de presupuesto
  - validación de transiciones
  - reglas de ubicación SAT ligadas al workflow
- `wexplay_repair_delivery` debe concentrar:
  - estado `delivered`
  - reglas de entrega
  - flujo pago -> entrega
  - filtros y UX de entrega

## Reglas SAT ya decididas
- La lógica fuerte de SAT debe vivir en Python; XML debe limitarse a visibilidad y acceso a acciones
- Si una factura SAT necesita una versión documental más completa que la estándar, debe resolverse como variante del mismo `account.move`, no como factura paralela
- Las facturas SAT deben poder convivir con la factura estándar de Odoo y ambas deben ser seleccionables desde el flujo nativo de `Send & Print`
- Los correos SAT al cliente pueden incluir datos operativos que aporten credibilidad y contexto:
  - referencia SAT
  - dispositivo
  - modelo
  - IMEI o número de serie
  - avería descrita por el cliente
- Los correos al cliente no deben incluir notas internas del técnico salvo decisión funcional explícita
- La acción `Entregado` debe estar alineada con validación Python y no depender solo de condiciones en XML

## Dependencias y acoplamientos SAT a vigilar
- OCA DMS es dependencia funcional real para la estrategia documental SAT
- `wexplay_sat_print` forma parte del ecosistema `Wexplay Print Core`; la integración SAT con ese stack es real, pero no debe tratarse como dependencia obligatoria del SAT
- Las reglas de notificación SAT basadas en canal o discuss deben tratarse como integración explícita y no como detalle invisible repartido por el sistema

## Reglas globales para integraciones configurables
- Si una integración, elección funcional o referencia externa puede quedar frágil por ir hardcodeada en código, debe moverse a ajustes del módulo correspondiente
- Los hardcodes temporales solo son aceptables en fases iniciales o pruebas; si una elección puede romper el sistema o volverlo ambiguo, debe pasar a configuración explícita
- En SAT, cualquier referencia al canal de discuss debe poder seleccionarse desde Ajustes SAT si su ausencia o cambio puede afectar al funcionamiento
- Cuando una integración con otro stack Wexplay sea opcional de verdad, el módulo debe degradar con comportamiento claro y predecible en lugar de asumir su presencia silenciosamente

## Reglas globales para variantes documentales y correo
- Si un mismo documento necesita varias representaciones coherentes, crear las variantes necesarias sobre el mismo registro funcional en lugar de duplicar flujos
- Si una factura SAT requiere plantilla de correo específica, crear las variantes necesarias para mantener coherencia documental, incluyendo casos como facturas, abonos u otros documentos equivalentes cuando proceda

## Criterio para siguientes iteraciones SAT
- Priorizar refactorizaciones que hagan más honestas las dependencias y más claro el reparto de responsabilidades
- No adelantar una reorganización masiva del ecosistema SAT si antes no está saneada la base actual
- Si una deuda afecta a instalación, envío de documentos o trazabilidad, priorizarla por encima de mejoras estéticas o estructurales menores

---

# Contexto específico: portal B2B clientes

## Arquitectura portal consolidada
- `wexplay_portal` es la capa puente entre portal/website y los modulos de negocio Wexplay
- no debe integrarse la logica portal directamente dentro de `wexplay_repair`
- el portal actual es solo B2B autenticado para clientes empresa
- `website` es dependencia obligatoria real del portal

## Limites funcionales del portal actual
- reutiliza el portal nativo de facturas de `account`
- expone SAT basados en `repair.order`
- prepara solo una entrada futura para mantenimiento IT
- no implementa portal B2C
- no implementa acceso por token
- no expone SAT en vistas publicas

## Reglas de seguridad portal ya decididas
- el usuario portal solo puede ver datos de su `commercial_partner_id`
- no confiar en filtros visuales; la seguridad debe vivir en ACL, record rules, dominios y controladores
- acceso manual por URL a SAT ajeno debe fallar
- no exponer chatter, followers, adjuntos genericos ni relaciones indirectas peligrosas
- no exponer DMS de forma directa en portal
- cualquier `sudo()` puntual debe estar encapsulado en modelo y solo tras validar acceso al SAT

## Reglas de datos SAT en portal
- `x_internal_notes` nunca debe mostrarse en portal
- `internal_notes` es el campo valido para diagnostico visible al cliente
- el detalle SAT puede mostrar informacion operativa util al cliente, pero no notas tecnicas internas ni datos pensados solo para backend

## Imagenes SAT en portal
- las fotografias del SAT se sirven por ruta segura ligada al SAT autorizado, no por rutas genericas de DMS
- el portal puede mostrar miniaturas, etiquetas, descripcion, modal y descarga
- no debe abrirse navegacion de carpetas DMS ni exponer ids genericos de repositorio

## Facturacion en portal
- el portal de facturas debe seguir siendo el nativo de Odoo `account`
- desde la ficha SAT solo se debe enlazar o contextualizar la facturacion relacionada
- no crear portal de facturas paralelo

## Integracion futura con mantenimiento IT
- la entrada de mantenimiento IT solo debe aparecer si el partner tiene `x_is_it_maintenance_customer = True`
- en esta fase no se debe acoplar funcionalidad real de mantenimiento IT dentro de `wexplay_portal`

## UX portal ya decidida
- el portal debe mantener una estetica Odoo reconocible, pero mas cuidada y profesional
- la home publica no debe quedar en blanco
- un usuario portal que entre en `/` debe terminar en `/my`
- `Activos` es el filtro por defecto del listado SAT
- la busqueda del listado SAT debe ser controlada por selector previo, no por dominios demasiado ambiciosos y fragiles

## Referencias de documentacion
- `wexplay_portal/ARCHITECTURE.md` debe tratarse como fuente principal de decisiones del portal
- si una iteracion cambia reglas de acceso, alcance B2B/B2C, exposicion de imagenes o diagnostico visible, debe actualizarse esa arquitectura

---

# Contexto específico: Wex Print

## Arquitectura actual consolidada
- `wex_print_core` es el núcleo técnico compartido de impresión local/QZ
- `wexplay_product_print` contiene exclusivamente impresión de etiquetas de producto
- `wexplay_sat_print` contiene exclusivamente impresión SAT (labels, ticket y acciones SAT reutilizables)
- `wexplay_repair` mantiene el reporte QWeb de factura SAT y dispara acciones QZ para A4 desde `account.move`

## Responsabilidades ya separadas
- `wex_print_core` concentra:
  - integración QZ Tray
  - assets y helpers JS comunes
  - configuración compartida QZ
  - router de impresión
  - trazas técnicas
  - perfiles y asignaciones
  - snapshots de diagnóstico de impresoras (`qz.printers.details()`)
- `wexplay_product_print` debe concentrar:
  - reportes/etiquetas de producto
  - modal y acciones de producto
  - controladores específicos de producto
- `wexplay_sat_print` debe concentrar:
  - reportes SAT de etiquetas/ticket
  - acciones cliente SAT
  - modal/centro de impresión SAT
- `wexplay_repair` mantiene:
  - reporte QWeb de factura SAT (`account.move`)
  - integración funcional de impresión A4 SAT desde factura

## Estado validado en producción
- El modo `Hybrid` está validado en producción
- La impresión SAT y producto sigue funcionando
- El camino híbrido con `Pilot new resolution` está probado
- La impresión A4 SAT a doble cara está validada en producción
- La resolución de impresora por usuario además de por empresa está implementada
- Existe ya un catálogo inicial de impresoras guardadas (`wex.print.device`)
- El rollback operativo sigue siendo:
  - cambiar `Modo de Resolución` a `Legacy`
  - o desactivar `Pilot new resolution` en la asignación concreta

## Configuración de producción validada
- Profiles activos:
  - `A4 Prod`
  - `Product Label Prod`
  - `SAT Accessory Label Prod`
  - `SAT Main Label Prod`
  - `SAT Ticket Prod`
- Assignments activos con `Pilot new resolution`:
  - `Product Label Default`
  - `SAT Main Label Default`
  - `SAT Accessory Label Default`
  - `SAT Ticket Default`
  - `SAT A4 Default`
- `duplex_mode` validado en A4:
  - `Double-sided (long edge)`
- Impresoras de producción validadas:
  - etiquetas: `Brother QL-710W`
  - térmica: `PRP-300 (Copiar 1)`
  - A4: `Brother MFC-L2800DW Printer`

## Fase actual del proyecto Wex Print
- La Fase 1 de separación arquitectónica está completada:
  - `wex_print_core` como núcleo técnico
  - `wexplay_product_print` como capa de producto
  - `wexplay_sat_print` como capa SAT
- La Fase 2 está en estado intermedio y funcional:
  - `Hybrid` validado
  - trazas y diagnósticos operativos
  - A4 SAT con duplex validado
  - configuración por usuario y por empresa operativa
  - catálogo inicial de impresoras guardadas introducido
- La siguiente gran fase pendiente sigue siendo la de configurabilidad documental:
  - variantes de impresión
  - relación formal entre documento lógico, QWeb, `ir.actions.report`, `report.paperformat` y medio físico

## Reglas de diseño ya decididas para Wex Print
- No introducir nuevas capacidades rompiendo el fallback a `legacy`
- En producción, probar primero mediante:
  - `Hybrid`
  - `Pilot new resolution`
- No activar de golpe nuevas rutas reales para muchos documentos a la vez si no hay motivo fuerte
- Las mejoras nuevas deben poder revertirse desde configuración sin migraciones destructivas
- Los perfiles de impresión son el sitio correcto para opciones avanzadas como `duplex_mode`
- La selección real de impresora no debe seguir creciendo con hardcodes por `kind`

## Diagnóstico y observabilidad
- `wex.print.trace` es la fuente de verdad para validar:
  - `requested_mode`
  - `execution_mode`
  - `resolution_source`
  - `shadow_matches_legacy`
  - `pilot_use_new_resolution`
  - `next_duplex_mode`
- `wex.print.device.snapshot` permite guardar snapshots técnicos desde `qz.printers.details()`
- Los snapshots sirven para investigar diferencias de driver/capacidades sin tocar el flujo real de impresión

## Estado actual de QZ
- `wex_print_core` encapsula la integración QZ compartida
- La comprobación desde Ajustes usa conexión websocket y lectura de versión
- Linux ya se ha investigado a nivel operativo:
  - si QZ está arrancado y escucha en `8181/8182`, el problema más probable ya no es de versión
  - en ese escenario, el foco de diagnóstico debe ponerse en navegador/certificado/websocket local seguro
- La firma/certificado de confianza de QZ sigue descartada por ahora como prioridad de proyecto

## Deuda técnica reconocida y no resuelta todavía
- Aún existe hardcoding fuerte entre:
  - tipo documental
  - nombre de reporte QWeb
  - tamaño/medio físico
- La selección de reporte sigue siendo parcialmente hardcodeada aunque ya existe metadata más rica en `wex.print.document.type`
- La resolución legacy sigue conviviendo con valores manuales por texto para mantener compatibilidad
- El catálogo de impresoras guardadas existe, pero todavía no gobierna toda la resolución documental final
- Falta una capa formal de variantes de impresión:
  - documento lógico
  - variante QWeb
  - medio/tamaño físico
  - tipo de salida
- Falta cerrar completamente la relación entre:
  - documento imprimible
  - modelo Odoo propietario
  - área funcional (`sat`, `product`, `sales`, `purchase`, `stock`, `project`, etc.)
  - `ir.actions.report`
  - `report.paperformat`
  - impresora/perfil/asignación
- Esa deuda no debe atacarse hasta que el modo híbrido esté suficientemente estable
- No abrir a la vez:
  - nuevas rutas reales
  - variantes de impresión
  - resolución por usuario/puesto

## Siguiente fase recomendada cuando se retome
- Diseñar la capa de variantes de impresión sin romper lo ya validado:
  - desacoplar `document_type` de `report_name`
  - modelar variante física/tamaño
  - mantener convivencia con el sistema actual durante la migración
