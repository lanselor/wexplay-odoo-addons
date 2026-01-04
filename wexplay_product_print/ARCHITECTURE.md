# Arquitectura del módulo Wexplay Product Print Center

## 1. Propósito

Este módulo proporciona una funcionalidad de "Centro de Impresión de Productos", que permite a los usuarios imprimir información relacionada con los productos directamente desde la vista de formulario de la plantilla de producto. Parece estar diseñado para imprimir etiquetas, recibos u otros documentos relacionados con los productos.

## 2. Flujos de negocio principales

El flujo de negocio principal implica:

1.  Abrir una vista de formulario de plantilla de producto.
2.  Hacer clic en el botón "Impresión" en el encabezado.
3.  Este botón activa una acción de cliente que abre una interfaz de impresión personalizada basada en Javascript (el "Centro de Impresión de Productos").
4.  El usuario interactúa con la interfaz de impresión para seleccionar una impresora e imprimir los documentos deseados.

## 3. Modelos y responsabilidades

Este módulo extiende principalmente Odoo con funcionalidad del lado del cliente y no introduce nuevos modelos de Odoo. Interactúa con el modelo `product.template` existente a través de la interfaz de usuario.

## 4. Extensiones sobre el estándar de Odoo 18

Este módulo extiende la funcionalidad estándar de Odoo de las siguientes maneras:

*   **Acción de cliente:** Introduce una nueva acción de cliente (`action_wexplay_product_print_center`) que sirve como punto de entrada para la interfaz de impresión personalizada.
*   **Mejora de la interfaz de usuario:** Agrega un botón "Impresión" a la vista de formulario de plantilla de producto, lo que permite a los usuarios acceder a la funcionalidad de impresión directamente desde el formulario del producto.
*   **Interfaz de impresión basada en Javascript:** Proporciona una interfaz Javascript personalizada para seleccionar impresoras e imprimir documentos relacionados con el producto. Utiliza la biblioteca `qz-tray.js`, lo que sugiere capacidades de impresión directa desde el navegador.

## 5. Decisiones de diseño relevantes

*   **Implementación del lado del cliente:** La funcionalidad de impresión se implementa principalmente en el lado del cliente utilizando Javascript. Esto permite una experiencia de usuario más interactiva y receptiva. El uso de `qz-tray.js` sugiere la necesidad de acceso directo a la impresora, que a menudo es más fácil de lograr en el lado del cliente.
*   **Interfaz modal:** El archivo `product_print_modal.xml` indica que la interfaz de impresión probablemente se presenta en un cuadro de diálogo modal. Esto proporciona un entorno enfocado y autónomo para el proceso de impresión.
*   **Impresión directa:** El uso de `qz-tray.js` sugiere fuertemente que el módulo implementa la funcionalidad de impresión directa, evitando el proceso estándar de generación de informes de Odoo. Esto podría ser necesario por razones de rendimiento o para admitir configuraciones de impresora específicas.
