# Manual de Uso - MRW Shipping Connector

Este manual cubre el uso directo del módulo MRW desde su propia interfaz,
sin pasar por SAT.

## 1. Cuándo usar este flujo

Usa `MRW Shipments` cuando quieras:

- crear un envío manual directamente en MRW
- crear una recogida manual al cliente
- hacer pruebas operativas sin depender de ventas o SAT
- revisar la traza técnica de un envío MRW

Ruta:

```text
Envíos MRW > Operaciones > Envíos MRW
```

## 2. Crear un envío manual

Pulsa:

```text
Nuevo
```

Rellena como mínimo:

- `Compañía`
- `Configuración`
- `Transportista`
- `Tipo de operación`
- `Tipo de envío`
- `Servicio`
- `Cliente / dirección`
- `Fecha de envío`

### Referencia

La referencia ya no es obligatoria manualmente:

- si la dejas vacía, el módulo la genera automáticamente al guardar

## 3. Elegir el tipo de operación

Hay dos casos principales:

### Entrega al cliente

Uso normal de expedición desde Wexplay hacia cliente.

### Recogida en cliente

Uso inverso:

- MRW recoge en la dirección del cliente
- MRW entrega en la dirección configurada en la compañía MRW

## 4. Bultos

En el apartado `Bultos` el módulo crea por defecto:

- 1 bulto
- 1 kg

Debes revisar y ajustar:

- peso
- alto
- ancho
- largo

solo si hace falta.

## 5. Secuencia operativa recomendada

### Paso 1. Guardar

Guarda el envío para que se genere nombre y referencia automática si aplica.

### Paso 2. Preparar

Pulsa:

```text
Preparar
```

Esto valida la consistencia interna antes de enviar a MRW.

### Paso 3. Previsualizar petición MRW

Pulsa:

```text
Previsualizar petición MRW
```

Sirve para revisar el payload antes de una llamada real.

### Paso 4. Enviar a MRW

Pulsa:

```text
Enviar a MRW
```

Si la llamada es correcta, el envío guardará:

- número de envío MRW
- número de solicitud MRW
- URL de respuesta MRW

### Paso 5. Obtener etiqueta

Pulsa:

```text
Obtener / actualizar etiqueta
```

Si MRW devuelve la etiqueta:

- se adjunta el PDF
- podrás abrirla o descargarla desde la pestaña `Etiqueta`

## 6. Tracking

Si el envío ya tiene número MRW, puedes usar:

```text
Abrir tracking MRW
```

Esto abre el tracking público histórico de MRW en una pestaña nueva.

## 7. Cancelación

Hay dos escenarios:

### Cancelación interna

Si el envío aún no ha salido realmente hacia MRW o está en fase previa, puedes
usar:

```text
Cancelar
```

### Cancelación contra MRW

Si ya existe expedición MRW, usa:

```text
Solicitar cancelación
```

Puedes revisar antes:

```text
Previsualizar cancelación
```

Importante:

- MRW puede rechazar la cancelación
- si la rechaza, el módulo conserva el estado y deja traza en logs

## 8. Recogidas con albarán entrante opcional

En una recogida en cliente puedes crear un albarán entrante opcional para que
Odoo espere la entrada física del material.

Eso sirve para:

- trazabilidad de inventario
- recepción posterior en almacén

No crea por sí mismo un RMA genérico.

## 9. Logs y revisión técnica

Para usuarios administradores, el envío MRW permite abrir:

- logs técnicos
- payloads saneados
- respuestas MRW

Úsalo cuando necesites revisar:

- errores SOAP
- cancelaciones rechazadas
- respuestas inconsistentes

## 10. Cuándo no usar este flujo

No uses este flujo manual cuando el caso ya pertenece claramente a SAT y debe
quedar ligado a la reparación.

En esos casos conviene trabajar desde:

- `repair.order`
- pestaña `Envíos`

porque así el envío queda unido al expediente SAT.
