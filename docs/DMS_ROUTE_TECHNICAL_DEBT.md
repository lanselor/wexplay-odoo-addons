# Deuda tecnica aceptada: rutas DMS SAT entre Repair y Consent

Fecha de documentacion: 2026-05-03

## Resumen

Actualmente existe un acoplamiento tecnico entre `wexplay_repair` y `wex_consent` alrededor de la configuracion y resolucion de rutas DMS SAT.

Esta deuda se acepta de forma consciente en esta fase porque:

- el contexto funcional esta acotado al binomio SAT reparacion + consentimientos;
- `wex_consent` tiene un alcance funcional cerrado;
- el guardado de firmas no deberia crecer mas alla de ajustes concretos;
- mover ahora la infraestructura DMS a un modulo nuevo aumentaria el riesgo antes de produccion;
- las carpetas y datos ya creados en DMS funcionan correctamente y no requieren migracion inmediata.

No se considera una deuda urgente.

## Estado actual

### `wexplay_repair`

`wexplay_repair` contiene los helpers de ruta DMS SAT en:

```text
wexplay_repair/models/repair_order_dms.py
```

Responsabilidades actuales:

- sanitizar nombres de carpetas DMS SAT;
- localizar o crear la raiz `SAT`;
- localizar o crear la carpeta propia de una reparacion;
- localizar o crear subcarpetas funcionales:
  - `IMAGES`
  - `DOCUMENTS`
  - `SIGNATURES`

Metodo compartido principal:

```python
repair_order._get_or_create_sat_directory(folder_name, create_defaults=False)
```

### `wex_consent`

`wex_consent` aporta actualmente la configuracion DMS por compania:

```text
wex_consent/models/res_company.py
wex_consent/models/res_config_settings.py
```

Campos relevantes:

```python
x_wex_consent_dms_storage_id
x_wex_consent_dms_root_directory_id
```

Tambien consume la ruta SAT de `repair.order` para guardar PDFs firmados:

```python
repair_order._get_or_create_sat_directory("SIGNATURES", create_defaults=True)
```

### `wexplay_repair_images`

`wexplay_repair_images` consume la misma infraestructura para guardar fotos SAT:

```python
repair_order._get_or_create_sat_directory("IMAGES", create_defaults=True)
```

Aunque participa en el uso de la ruta, la deuda conceptual principal esta entre:

- la base SAT (`wexplay_repair`);
- la configuracion documental nacida en consentimientos (`wex_consent`).

## Deuda concreta

El nombre de los campos de configuracion DMS contiene `consent`, pero la ruta ya se usa como infraestructura SAT general.

Ejemplo:

```python
company.x_wex_consent_dms_storage_id
company.x_wex_consent_dms_root_directory_id
```

Sin embargo, esos campos gobiernan realmente la estructura:

```text
SAT/<REPAIR_NAME>/
  IMAGES/
  DOCUMENTS/
  SIGNATURES/
```

Esto hace que la propiedad funcional sea algo ambigua:

- la configuracion vive en `wex_consent`;
- los helpers viven en `wexplay_repair`;
- las firmas y las imagenes SAT consumen la misma estructura.

## Por que no se refactoriza ahora

No se crea `wex_dms_core` en esta fase porque el coste/riesgo no compensa el beneficio inmediato.

Riesgos de moverlo ahora:

- renombrar campos de `res.company` puede provocar errores de upgrade si el codigo carga antes que la columna;
- mover configuracion puede obligar a migrar valores existentes;
- tocar rutas DMS antes de produccion aumenta el riesgo de romper firmas o imagenes ya validadas;
- una abstraccion nueva podria introducir mas superficie tecnica que el problema actual.

La regla actual es: mantener la ruta existente estable y documentada.

## Criterio de aceptacion actual

Se acepta mantener esta deuda mientras se cumplan estas condiciones:

- `wex_consent` no crece hacia nuevos dominios documentales;
- las firmas siguen limitadas a recepcion/entrega SAT;
- las imagenes SAT siguen usando la carpeta `IMAGES` de la reparacion;
- no aparecen nuevos modulos que necesiten reutilizar rutas SAT fuera de repair/consent/images;
- no se necesita instalar `wexplay_repair_images` de forma independiente de `wex_consent`;
- no se crean nuevos tipos documentales DMS de SAT que requieran configuracion propia.

## Cuando reabrir esta deuda

Reabrir esta decision si ocurre cualquiera de estos casos:

- se necesita crear mas carpetas DMS SAT aparte de `IMAGES`, `DOCUMENTS` y `SIGNATURES`;
- consentimientos empieza a gestionar documentos no SAT;
- imagenes SAT deben poder instalarse sin instalar firmas/consentimientos;
- producto, mantenimiento IT o knowledge empiezan a reutilizar rutas SAT;
- se necesita una configuracion DMS comun para varios dominios Wexplay;
- aparece necesidad real de multiempresa con rutas documentales diferenciadas por dominio;
- se planifica una migracion mayor de almacenamiento/documentacion.

## Opcion futura recomendada

Si esta deuda se reabre, la opcion preferida seria una extraccion conservadora:

1. Crear `wex_dms_core`.
2. Mover ahi solo infraestructura comun DMS, no logica de negocio.
3. Mantener compatibilidad con nombres/metodos actuales.
4. No mover fisicamente carpetas DMS existentes.
5. Evitar renombrados destructivos de campos en la primera iteracion.
6. Hacer que `wexplay_repair`, `wex_consent` y `wexplay_repair_images` dependan de esa base comun.

No se recomienda incluir `wexplay_knowledge_images` en esa extraccion inicial. Knowledge ya tiene una ruta DMS paralela (`KNOWLEDGE/...`) y debe evaluarse aparte.

## Regla para futuros cambios

Hasta que esta deuda se reabra formalmente:

- no duplicar helpers de rutas SAT en otros modulos;
- no anadir mas logica DMS de consentimientos dentro de `wexplay_repair_images`;
- no renombrar campos DMS existentes sin migracion;
- no mover carpetas DMS fisicas manualmente;
- documentar cualquier nueva carpeta SAT creada bajo esta estructura.
