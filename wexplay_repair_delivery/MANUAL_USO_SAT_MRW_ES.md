# Manual de Uso - Envíos MRW desde SAT

Este manual explica cómo usar MRW desde el flujo SAT en `repair.order`,
apoyándose en `wexplay_repair_delivery`.

## 1. Objetivo del flujo

Desde SAT puedes gestionar dos operaciones logísticas por reparación:

- `Recogida del cliente`
- `Entrega al cliente`

Cada reparación admite como máximo:

- una recogida
- una entrega

## 2. Dónde se usa

Ruta:

```text
SAT / Reparaciones > abrir reparación > pestaña Envíos
```

En esta pestaña verás:

- bloque de activación logística
- tarjeta de recogida
- tarjeta de entrega
- tabla de seguimiento logístico

## 3. Activar la logística en la reparación

Marca:

```text
Requiere envío / recogida
```

Sin ese flag:

- no podrás crear operaciones logísticas
- la pestaña seguirá visible, pero bloqueada para edición operativa

## 4. Recogida del cliente

Usa este flujo cuando el equipo debe viajar:

```text
Cliente -> Wexplay
```

### Crear la recogida

Pulsa:

```text
Crear recogida
```

Se abrirá una `Operación logística SAT`.

### Revisar datos

Comprueba:

- cliente / dirección
- transportista
- producto
- cantidad
- teléfono y dirección completos

Si el transportista es MRW:

- la operación puede crear directamente un `mrw.shipping.shipment`
- no necesita primero un albarán saliente

### Enviar a MRW

Pulsa:

```text
Solicitar al transportista
```

Si todo va bien:

- se crea el envío MRW
- se guarda la referencia MRW
- se intenta obtener la etiqueta
- queda disponible el tracking

### Abrir tracking

Desde la operación o desde la tabla de `Envíos` en la reparación puedes abrir:

```text
Abrir tracking
```

o el icono de enlace externo de la línea.

## 5. Albarán entrante en recogidas

Si el caso lo necesita, la operación puede crear un albarán entrante para
esperar la entrada física del equipo.

Eso permite:

- trazabilidad de stock
- recepción posterior en inventario
- enlace con la operación SAT y con el envío MRW

## 6. Entrega al cliente

Usa este flujo cuando el equipo debe viajar:

```text
Wexplay -> Cliente
```

### Crear la entrega

Pulsa:

```text
Crear entrega
```

Se abrirá la operación logística SAT.

### Crear albarán

Para la entrega, primero crea el albarán:

```text
Crear albarán
```

Después:

- confirma el albarán si aplica
- asegúrate de que tenga carrier MRW

### Solicitar al transportista

Pulsa:

```text
Solicitar al transportista
```

En este caso la operación reutiliza el flujo nativo de Odoo con
`delivery.carrier`.

Resultado esperado:

- tracking en el albarán
- envío MRW enlazado
- etiqueta disponible si MRW la devuelve

## 7. Tabla de seguimiento logístico en la reparación

En la pestaña `Envíos`, la tabla final resume:

- tipo de operación
- estado
- cliente
- transportista
- albarán
- envío MRW
- referencia de tracking
- enlace de tracking
- etiqueta
- facturación asociada

Esta tabla es la vista rápida más cómoda para el seguimiento SAT.

## 8. Costes logísticos

Cada operación logística puede definir política de facturación:

- añadir a venta si es editable
- factura de gastos
- no facturar

Esto permite separar:

- la gestión logística
- la imputación económica

## 9. Qué hacer si algo falla

### Si falla la solicitud al transportista

Revisa:

- dirección del cliente
- teléfono
- carrier configurado
- configuración MRW
- logs del envío MRW si existe

### Si no aparece etiqueta

Usa:

```text
Obtener etiqueta
```

desde la operación logística o desde el envío MRW enlazado.

### Si necesitas más detalle técnico

Abre:

- la operación logística SAT
- el envío MRW enlazado
- los logs técnicos MRW

## 10. Recomendación operativa

Para casos SAT, trabaja siempre desde la reparación y no desde `MRW Shipments`,
salvo que estés haciendo una prueba manual o una operación técnica aislada.

Así consigues:

- trazabilidad por expediente
- enlace con picking
- enlace con MRW
- enlace con facturación logística
