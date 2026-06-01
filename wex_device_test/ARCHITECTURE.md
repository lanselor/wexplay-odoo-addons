# Wex Device Test Architecture

## Objetivo del módulo

`wex_device_test` introduce la base de ApiTest para que una app Android pueda comprobar conectividad contra Odoo 18 Community usando JSON sobre HTTP(S), sin depender de XML-RPC ni JSON-RPC, y además alimentar la operativa de test dentro de `repair.order`.

La fase 1 queda orientada a validar el camino completo Android -> endpoint personalizado -> persistencia de sesión en Odoo, manteniendo el alcance reducido a una prueba de conexión autenticada.

## Modelos

### `wex.device.test.session`

Modelo operativo mínimo para registrar el último ping conocido por `device_uuid`.

Campos principales:

- `name`
- `device_uuid`
- `manufacturer`
- `model`
- `android_version`
- `sdk_int`
- `app_version`
- `first_ping_at`
- `last_ping_at`
- `last_diagnostic_at`
- `ping_count`
- `last_seen_ip`
- `last_user_agent`
- `last_battery_level`
- `last_network_type`
- `last_storage_free_mb`
- `last_storage_total_mb`
- `last_status`
- `last_message`
- `active`
- `company_id`

En fase 2 la unicidad funcional de la sesión queda por `device_uuid + company_id`, para no mezclar trazabilidad entre compañías.

En fase 3 la sesión sigue siendo la cabecera del dispositivo y concentra solo el último estado agregado útil para operar.

### `wex.device.test.log`

Modelo de trazabilidad sobrio para eventos backend y warnings recibidos del cliente.

Campos principales:

- `session_id`
- `event_type`
- `status`
- `message`
- `technical_details`
- `payload_json`
- `company_id`
- `create_date`

### `wex.device.test.result`

Modelo funcional para registrar resultados concretos de pruebas guiadas y sensores.

Campos principales:

- `session_id`
- `test_type`
- `status`
- `message`
- `technical_details`
- `measurement_json`
- `executed_at`
- `company_id`

### `wex.device.test.run`

Modelo operativo para representar una revisión real de test vinculada a una `repair.order`.

Campos principales:

- `repair_order_id`
- `session_id`
- `user_id`
- `state`
- `pairing_token`
- `pairing_code`
- `started_at`
- `paired_at`
- `completed_at`
- `cancelled_at`
- `last_message`
- `company_id`

## Endpoint

- Ruta: `POST /wex/device-test/session/ping`
- Ruta: `POST /wex/device-test/session/diagnostic`
- Ruta: `POST /wex/device-test/session/result`
- Ruta: `POST /wex/device-test/run/pair`
- Entrada: JSON puro
- Autenticación: header `Authorization: Bearer <token>`
- Salida: JSON puro con `ok`, `code`, `message`, `session_id`, `server_time` y bloque `session`

El controlador valida token y payload antes de escribir. La creación o actualización de la sesión queda concentrada en el modelo.

### Criterio de contrato en fase 2

- `message` sigue siendo un texto humano legible.
- `code` pasa a ser la clave estable para decisiones del cliente Android.
- Se conserva `session_id` para compatibilidad con la fase 1.
- Los datos de trazabilidad HTTP útiles se guardan en la propia sesión cuando existen.

### Criterio de transporte en fase 1

- En despliegue real, el objetivo es usar HTTPS con dominio válido.
- En pruebas locales de desarrollo, el backend también puede validarse por HTTP dentro de red privada si el entorno Android lo permite de forma explícita.
- El contrato funcional del endpoint no cambia entre HTTP y HTTPS; solo cambia el medio de acceso según entorno.

## Seguridad

- No hay endpoint abierto sin comprobación de token.
- El token se guarda en `ir.config_parameter` bajo `wex_device_test.api_token`.
- La URL pública que debe viajar en el QR se guarda en `ir.config_parameter` bajo `wex_device_test.public_base_url`.
- El backend usa un grupo propio `Device Test Manager` para consultar sesiones.
- Las sesiones quedan limitadas por `company_id` mediante record rule.
- El uso de `sudo()` queda acotado al acceso técnico necesario tras validar el Bearer token.

## Alcance de fase 2

Esta iteración se limita a:

- reforzar el modelo de sesión
- estabilizar el contrato HTTP
- mejorar la trazabilidad mínima operativa
- añadir vistas backend más útiles
- cubrir reglas críticas con tests

## Alcance de fase 3

Esta iteración amplía la base con:

- un endpoint mínimo de diagnóstico básico
- un modelo de logs auditable
- resumen del último diagnóstico en la propia sesión
- warnings del cliente registrados como eventos estructurados

## Alcance de la fase actual SAT

Esta iteración empieza la integración operativa con `repair.order`:

- `wex_device_test` introduce la primera especialización operativa dentro de `Test` para móvil y tablet
- se introduce `wex.device.test.run` como revisión concreta
- la reparación consume datos de ApiTest sin volverse dueña de la lógica técnica
- resultados y logs quedan preparados para colgar también del run

## Posicionamiento funcional dentro de `repair.order`

`Test` no debe modelarse como una pestaña exclusiva de la app Android.

`Test` es un dominio funcional general del SAT y debe seguir viviendo como una única entrada operativa dentro de `repair.order`.

La app Android de `wex_device_test` resuelve solo una especialización concreta:

- dispositivos `Móvil`
- dispositivos `Tablet`

Por tanto, el criterio de arquitectura queda así:

- debe existir una sola pestaña `Test` en la ficha técnica y diagnóstico
- esa pestaña debe adaptarse al tipo de dispositivo
- `wex_device_test` no debe apropiarse de todos los test posibles del SAT
- `wex_device_test` sí puede inyectar bloques o subzonas específicas para móvil y tablet

## Regla funcional de una sola pestaña `Test`

No debe haber dos pestañas `Test` visibles para el técnico.

Si existen piezas reservadas o placeholders previos dentro de `repair.order`, deben converger hacia una única pestaña operativa.

La estructura objetivo no es:

- una pestaña `Test` para Android
- otra pestaña `Test` para la reparación

La estructura objetivo sí es:

- una sola pestaña `Test`
- varios bloques internos condicionados por tipo de dispositivo y por motor de test disponible

## Criterio por tipo de dispositivo

La experiencia de `Test` debe depender del tipo de dispositivo registrado en la reparación.

Ejemplos esperados:

- `Móvil` o `Tablet`: integración con app Android, pairing, resultados automáticos y pruebas guiadas
- `Portátil`: flujo futuro específico de portátil
- `Consola`: flujo futuro específico de consola
- otros tipos: experiencia propia cuando exista una necesidad funcional real

Esto significa que la pestaña `Test` debe ser extensible por especializaciones, pero sin duplicar la navegación principal del técnico.

## Reparto de responsabilidades SAT vs. especialización móvil

La responsabilidad general de `Test` pertenece al dominio SAT de la reparación.

La responsabilidad específica de `wex_device_test` queda acotada a:

- conectar una app Android con Odoo
- gestionar pairing y runs de móvil/tablet
- recibir diagnóstico y resultados automáticos del dispositivo
- alimentar la experiencia de `Test` cuando la reparación sea de móvil o tablet

No queda decidido todavía:

- cómo se modelarán los motores futuros de portátil o consola
- si existirán módulos especializados por familia de dispositivo
- qué parte del resultado final seguirá siendo manual y cuál automática en cada familia

## Criterio UX de la pestaña `Test`

Dentro de una única pestaña `Test`, la fase actual debe distinguir al menos dos capas funcionales cuando el dispositivo sea móvil o tablet:

- preparación técnica de la conexión con la app
- lectura operativa de resultados y estado del dispositivo

La zona de conexión no debe crecer sin control hasta convertirse también en pantalla de resultados completa.

La intención funcional es mantener separadas dentro de la misma pestaña:

- la preparación del canal técnico
- la explotación de la información recibida desde la app

## Estado actual de la UX Odoo para móvil y tablet

La implementación actual de Odoo ya dispone de una primera experiencia operativa para `Móvil` y `Tablet`:

- creación de `Test Run` desde `repair.order`
- reinicio de pairing desde la propia reparación
- QR de descarga de APK
- QR de pairing del run activo
- acceso rápido al `run` activo
- control visual de si la fase visible es de preparación o de sesión activa

La UX actual no debe considerarse la forma definitiva del dominio `Test`, sino una especialización inicial centrada en la integración Android.

## Criterio del QR en Odoo

La generación visual de QR en Odoo se apoya en el generador nativo accesible por:

- `/report/barcode/QR/<value>?width=<w>&height=<h>`

No debe asumirse como estable en este proyecto la variante con query string `?type=QR`, ya que en el entorno validado dio error y la forma funcional fue la ruta anterior.

Los QR actuales cubren dos necesidades distintas:

- QR de descarga de la APK
- QR de pairing de una reparación concreta

## Mini web de descarga fuera de Odoo

La descarga de la APK no vive dentro de Odoo.

La mini web de descarga queda separada para despliegue manual desde:

- `C:\odoo18\test`

El destino funcional previsto es:

- `https://www.wexplay.com/test`

La contraseña temporal de depuración decidida para esa mini web es:

- `1337`

## Estado actual del backend SAT + Android

El flujo ya validado funcionalmente queda así:

- Odoo crea un `wex.device.test.run`
- Odoo genera `pairing_token` y `pairing_code`
- Odoo expone un QR con `base_url`, `pairing_token`, `pairing_code`, `repair_order_ref` y `run_id`
- Android escanea ese QR o introduce datos manualmente
- Android ejecuta `POST /wex/device-test/run/pair`
- Odoo vincula el `run` con una `session`
- Android envía `ping`, `diagnostic` y `result` ya contextualizados con `run_id` y `pairing_token`
- Odoo actualiza sesión, logs, resultados y estado del `run`

## Incidencias reales ya detectadas en la implementación

Durante la fase actual ya aparecieron varios problemas que deben tratarse como conocimiento del proyecto y no como accidentes aislados:

- confusión operativa entre `pairing_token` y `pairing_code`
- necesidad de ocultar el token por defecto y mostrarlo solo con botón explícito
- necesidad de una `public_base_url` específica, distinta de `web.base.url` cuando esta última apunte a `localhost`
- error de Android con tráfico `CLEARTEXT` si el dispositivo no permite HTTP local por política de red
- necesidad de separar en Android el contexto de conectividad básica del contexto operativo con `run_id` y `pairing_token`

## Estado actual de Android

La app Android ya no está en una fase puramente experimental de ping.

Quedan ya introducidas, al menos a nivel de funcionalidad base:

- configuración manual de `base_url` y `api_token`
- ping contra Odoo
- pairing manual
- pairing por QR
- persistencia local del estado de pairing
- envío de diagnóstico básico
- envío de resultados de pruebas guiadas
- dashboard inicial
- menú de pruebas
- integración de lector QR

La UX Android sigue en evolución y no debe tomarse todavía como diseño final cerrado.

## Alcance de la siguiente fase funcional

Esta iteración añade:

- un modelo de resultados funcionales de prueba
- un endpoint genérico de resultados de test
- soporte inicial para audio guiado
- soporte inicial para sensores y térmico informativo

## Criterio de reparto de responsabilidades en fase 3

- `wex.device.test.session`: último estado útil del dispositivo
- `wex.device.test.log`: histórico de eventos y trazas útiles
- `wex.device.test.result`: histórico funcional de pruebas concretas
- controlador: autenticación, validación, orquestación y respuesta JSON

No se introduce todavía:

- pairing end-to-end completo
- QR operativos en Odoo
- cola kiosko
- captura de imágenes
- firma
- suite amplia de sensores

## Criterio funcional de los nuevos resultados

- audio no se trata como validación automática de hardware, sino como test guiado con confirmación humana
- sensores reflejan disponibilidad o detección real, no conclusiones exageradas
- térmico se trata como dato informativo cuando exista, no como veredicto concluyente

## Validación funcional de fase 1

Flujo validado en entorno de pruebas:

- Configuración manual del token compartido en Odoo.
- Prueba manual del endpoint desde terminal contra `localhost:8069`.
- Prueba real desde Android Studio contra Odoo en red local usando la IP privada del PC.
- Persistencia correcta de `device_uuid`, fabricante, modelo, versión Android, SDK y versión de app en `wex.device.test.session`.

## Fuera de fase 1

Esta versión no implementa:

- Sensores Android.
- Pruebas de audio.
- Giroscopio.
- Proximidad.
- Diagnóstico de hardware.
- Flujos SAT.
- QR.
- Gestión documental.
