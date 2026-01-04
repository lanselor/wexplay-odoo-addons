# Arquitectura del módulo Wexplay Repair Management

## 1. Propósito

Este módulo extiende el módulo estándar `repair` de Odoo para adaptarlo a los flujos de trabajo específicos de servicio y reparación de Wexplay para dispositivos electrónicos como móviles, portátiles, tablets y consolas. Proporciona una interfaz más estructurada y fácil de usar para gestionar las órdenes de reparación, centrándose particularmente en los tipos de dispositivos, marcas y modelos.

## 2. Flujos de negocio principales

El flujo de negocio principal implica la creación y gestión de órdenes de reparación para dispositivos electrónicos. El módulo mejora este flujo al:

*   **Identificación del dispositivo:** Proporcionar una forma estandarizada de especificar el tipo, la marca y el modelo del dispositivo que se está reparando.
*   **Información de desbloqueo:** Capturar detalles sobre el método de desbloqueo del dispositivo (PIN, patrón, contraseña) para los técnicos.
*   **Comunicación con el cliente:** Mostrar la información de contacto del cliente (móvil, teléfono) directamente en la orden de reparación.
*   **Informes:** Generar informes y etiquetas adaptados a las necesidades de Wexplay.

## 3. Modelos y responsabilidades

*   **`repair.order` (Heredado):** El modelo central para gestionar las órdenes de reparación. Este módulo lo extiende con los siguientes campos:
    *   `x_device_type`: El tipo de dispositivo que se está reparando (móvil, tablet, etc.).
    *   `x_partner_mobile`, `x_partner_phone`: Información de contacto del cliente.
    *   `x_brand_id`: La marca del dispositivo (hace referencia a `wex.repair.brand`).
    *   `x_model_id`: El modelo del dispositivo (hace referencia a `wex.repair.device_model`).
    *   Campos relacionados con el desbloqueo (`x_unlock_type`, `x_unlock_code`, `x_unlock_pattern`, `x_unlock_notes`).
    *   `x_accessories`, `x_reported_issue`, `x_internal_notes`: Campos de información adicional.
*   **`wex.repair.brand`:** Almacena las marcas de dispositivos. Tiene un `name` y un indicador `active`.
*   **`wex.repair.device_model`:** Almacena los modelos de dispositivos, vinculados a una marca y un tipo de dispositivo. Tiene un `name`, `device_type`, `brand_id` y un indicador `active`.

## 4. Extensiones sobre el estándar de Odoo 18

Este módulo extiende la funcionalidad estándar de Odoo de las siguientes maneras:

*   **Nuevos modelos:** Introduce `wex.repair.brand` y `wex.repair.device_model` para normalizar la información de la marca y el modelo del dispositivo.
*   **Extensiones de campo:** Agrega varios campos nuevos al modelo `repair.order` para capturar información específica del dispositivo.
*   **Mejoras de la interfaz de usuario:** Modifica las vistas de la orden de reparación para mostrar los nuevos campos y mejorar la experiencia del usuario.
*   **Informes:** Agrega informes y etiquetas personalizadas para las órdenes de reparación.

## 5. Decisiones de diseño relevantes

*   **Normalización de la marca y el modelo:** La decisión de crear modelos separados `wex.repair.brand` y `wex.repair.device_model` fue impulsada por la necesidad de estandarizar la información del dispositivo y evitar la duplicación de datos. Esto permite una mejor generación de informes y filtrado de las órdenes de reparación.
*   **Campos de compatibilidad:** Los campos `x_brand`, `x_model` y `x_imei` se conservan por compatibilidad con datos anteriores. La intención es migrar los datos existentes a los campos normalizados `x_brand_id` y `x_model_id` y, finalmente, eliminar estos campos de compatibilidad.
*   **`ondelete="restrict"` en `x_model_id`:** Esto evita la eliminación de un modelo de dispositivo si se está utilizando actualmente en alguna orden de reparación, lo que garantiza la integridad de los datos.
*   **`store=True` en `x_brand_id`:** Esto almacena la marca en el registro `repair.order`, lo cual es necesario para una búsqueda y agrupación eficientes por marca. Se completa automáticamente a través del campo `related` de `x_model_id`.
*   **Post-init hook:** El manifiesto incluye un `post_init_hook`, lo que sugiere que puede haber una lógica de migración o inicialización de datos que se ejecuta después de instalar el módulo. Se necesita una mayor investigación del archivo `hooks.py`.
