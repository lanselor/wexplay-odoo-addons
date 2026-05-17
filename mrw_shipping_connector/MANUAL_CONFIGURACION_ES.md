# Manual de Configuración - MRW Shipping Connector

Este manual explica cómo dejar configurado `mrw_shipping_connector` para empezar
a trabajar con MRW en Odoo.

## 1. Requisitos previos

Antes de configurar MRW, comprueba:

- módulo instalado: `mrw_shipping_connector`
- módulos base disponibles:
  - `delivery`
  - `stock_delivery`
- credenciales MRW disponibles:
  - código de franquicia
  - código de abonado
  - código de departamento, si aplica
  - usuario
  - contraseña
- decisión operativa sobre si se trabajará en:
  - `Pruebas`
  - `Producción`

## 2. Instalar o actualizar el módulo

Desde Odoo:

```text
Aplicaciones > buscar "MRW"
```

Instala o actualiza:

```text
mrw_shipping_connector
```

## 3. Crear la configuración MRW

Ruta:

```text
Envíos MRW > Configuración > Configuraciones MRW
```

Crea una nueva configuración o edita una existente.

### Campos principales

- `Nombre`: identificador interno, por ejemplo `MRW Main`
- `Compañía`: empresa Odoo que usará esta cuenta MRW
- `Entorno`:
  - `Pruebas` para validación
  - `Producción` para uso real
- `URL WSDL pruebas`:
  - `https://sagec-test.mrw.es/MRWEnvio.asmx?WSDL`
- `URL WSDL producción`:
  - `https://sagec.mrw.es/MRWEnvio.asmx?WSDL`
- `Código de franquicia`
- `Código de abonado`
- `Código de departamento`
- `Usuario`
- `Contraseña`

### Servicios por defecto

Define al menos:

- `Servicio nacional por defecto`

Y, solo si se va a trabajar con ello más adelante:

- `Servicio internacional por defecto`

## 4. Ejecutar comprobaciones

En la propia configuración MRW usa estos botones:

- `Probar conexión`
- `Inspeccionar WSDL`
- `Ejecutar diagnóstico`

Qué valida el diagnóstico:

- que existan credenciales
- que haya servicios por defecto coherentes
- que el WSDL responda
- que las operaciones esperadas estén disponibles

Si el informe sale limpio, la configuración base está correcta.

## 5. Activar o no producción

La producción está protegida por dos condiciones:

- `Entorno = Producción`
- `Permitir llamadas reales de producción = activado`

No actives producción hasta haber validado:

- creación de envío en TEST
- obtención de etiqueta
- apertura de tracking
- cancelación
- direcciones y teléfonos reales con formato correcto

## 6. Crear los servicios MRW visibles en Odoo

Ruta típica:

```text
Inventario o Ventas > Configuración > Métodos de envío
```

Crea un transportista por cada servicio operativo que quieras usar, por ejemplo:

- `MRW Bag 19`
- `MRW Urgente 19`

### Campos recomendados del transportista

- `Proveedor`: `MRW`
- `Configuración MRW`: la configuración creada antes
- `Servicio MRW`: el servicio MRW correspondiente
- `Producto de transporte`: producto usado por Odoo para el coste
- `Obtener etiqueta MRW al enviar`: activado si quieres intentar traer la
  etiqueta automáticamente

## 7. Política de precio

Este conector no calcula tarifa real en vivo contra MRW.

El importe del transporte en Odoo sale del:

- producto del transportista
- precio fijo configurado en el método de envío

Recomendación:

- usar ese precio como precio comercial interno
- no asumir que coincide exactamente con la facturación final de MRW

## 8. Configuración mínima recomendada para arrancar

Para una salida controlada a producción, la configuración mínima recomendada es:

- una configuración MRW activa
- un transportista nacional MRW operativo
- etiqueta automática activada
- pruebas de diagnóstico correctas
- pruebas reales controladas con una expedición sencilla

## 9. Qué no configura este módulo

Este módulo no resuelve por sí solo:

- tarifas vivas MRW
- timeline de tracking por SOAP
- POD o justificante enriquecido en Odoo
- automatización genérica de RMA/devoluciones
- validación internacional real

Esas piezas siguen documentadas como deuda o evolución futura.
