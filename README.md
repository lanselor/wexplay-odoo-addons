Apply
# Wexplay - Addons Odoo 18 Community

Este repositorio contiene una colección de módulos Odoo 18 Community desarrollados por Wexplay para extender y personalizar la funcionalidad estándar del ERP. El objetivo principal de estos módulos es adaptar Odoo a las necesidades específicas de la empresa, mejorando la eficiencia y la productividad en áreas clave.

## Contexto de Uso

Estos módulos están diseñados para ser utilizados en un entorno Odoo 18 Community. No se garantiza su compatibilidad con versiones anteriores o con la versión Enterprise. Se recomienda utilizarlos con una instalación limpia de Odoo 18 Community para evitar conflictos con otros módulos.

## Módulos Incluidos

Este repositorio contiene los siguientes módulos:

*   **`wexplay_repair`:** Extiende el módulo estándar de reparaciones (`repair`) para adaptarlo a los flujos de trabajo específicos de servicio y reparación de Wexplay para dispositivos electrónicos (móviles, portátiles, tablets, consolas, etc.). Proporciona una interfaz más estructurada para gestionar las órdenes de reparación, centrándose en los tipos de dispositivos, marcas y modelos.
*   **`wexplay_product_print`:** Proporciona una funcionalidad de "Centro de Impresión de Productos", que permite a los usuarios imprimir información relacionada con los productos directamente desde la vista de formulario de la plantilla de producto. Está diseñado para imprimir etiquetas, recibos u otros documentos relacionados con los productos.
*   **`wex_product_codes`:** Genera automáticamente referencias internas de productos (`default_code`) basadas en la categoría del producto y reglas de codificación predefinidas. Utiliza secuencias independientes por categoría para asegurar la unicidad de los códigos.

## Dependencias Principales

Los módulos en este repositorio dependen de los siguientes módulos estándar de Odoo:

*   `repair` (solo `wexplay_repair`)
*   `stock` (solo `wexplay_repair`)
*   `mail` (solo `wexplay_repair`)
*   `web` (solo `wexplay_product_print`)
*   `product` (todos los módulos)

## Filosofía de Desarrollo

Estos módulos se desarrollan siguiendo las mejores prácticas de Odoo y, en la medida de lo posible, las recomendaciones de la OCA (Odoo Community Association). Se prioriza la mantenibilidad del código, la claridad, y la compatibilidad con futuras versiones de Odoo. Se intenta evitar la sobreescritura de métodos estándar, utilizando la herencia prototípica (`_inherit`) siempre que sea posible.

## Estado del Proyecto

Este proyecto se encuentra en desarrollo activo. Si bien los módulos se utilizan en producción en Wexplay, es posible que contengan errores o funcionalidades incompletas. Se recomienda realizar pruebas exhaustivas antes de utilizarlos en un entorno de producción.

**Advertencias:**

*   El módulo `wexplay_product_print` utiliza la biblioteca `qz-tray.js` para la impresión directa desde el cliente. Esto puede introducir riesgos de seguridad y mantenimiento. Se recomienda evaluar alternativas antes de utilizar este módulo en un entorno de producción.
*   El módulo `wex_product_codes` sobrescribe algunos métodos del modelo `product.template`. Esto podría generar conflictos con otros módulos que también modifican este modelo. Se recomienda realizar pruebas exhaustivas para evitar problemas de compatibilidad.

## Estructura del Repositorio

El repositorio tiene la siguiente estructura:

```
/wexplay-odoo-addons/
├── wexplay_repair/
│   ├── __init__.py
│   ├── __manifest__.py
│   ├── models/
│   ├── views/
│   ├── ...
├── wexplay_product_print/
│   ├── __init__.py
│   ├── __manifest__.py
│   ├── static/
│   ├── views/
│   ├── ...
├── wex_product_codes/
│   ├── __init__.py
│   ├── __manifest__.py
│   ├── models/
│   ├── views/
│   ├── ...
├── INFORME_ANALISIS.md
└── README.md
```

Cada directorio con nombre de módulo contiene los archivos necesarios para su instalación en Odoo. El archivo `INFORME_ANALISIS.md` contiene un análisis técnico del workspace.

## Instalación

Para instalar estos módulos, siga estos pasos:

1.  Clona este repositorio en tu servidor Odoo.
2.  Asegúrate de que las dependencias estén instaladas.
3.  Añade la ruta del repositorio a la lista de rutas de addons de Odoo.
4.  Actualiza la lista de módulos en Odoo.
5.  Instala los módulos que desees utilizar.

## Compatibilidad

Estos módulos han sido probados en Odoo 18 Community. No se garantiza su compatibilidad con otras versiones de Odoo.

## Licencia

LGPL-3