/** @odoo-module **/

console.log("WEXPLAY_PRINT: JS cargado");

import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

class PrintCenterModal extends Component {
    setup() {
        
        this.notification = useService("notification");
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.dialog = useService("dialog");
        
        console.log("WEXPLAY_PRINT: setup ejecutado", {
        orm: this.orm,
        hasOrmCall: !!this.orm?.call,
        });

    }
    close() {
        this.props.close();
    }
   async printProductLabel() {
        const productId = this.props.record?.resId;
        if (!productId) {
            this.notification.add("No se pudo determinar el producto actual.", { type: "danger" });
            return;
        }

        const reportName = "product.report_producttemplatelabel2x7";

        try {
            // 1) Buscamos el reporte
            const reports = await this.orm.searchRead(
                "ir.actions.report",
                [["report_name", "=", reportName]],
                ["id", "report_name"]
            );

            if (!reports.length) {
                this.notification.add(`No se encontró el reporte: ${reportName}`, { type: "danger" });
                return;
            }

            // 2) Llamada simplificada
            // Pasamos productId directamente como una lista en el segundo argumento
            const action = await this.orm.call(
                "ir.actions.report",
                "report_action",
                [[productId]], // docids debe ser el primer argumento (una lista de IDs)
                {
                    data: {
                        report_name: reportName,
                        report_type: 'qweb-pdf'
                    },
                    context: {
                        active_model: "product.template",
                        active_ids: [productId],
                        active_id: productId,
                    },
                }
            );

            // 3) Ejecutar acción
            if (action) {
                await this.actionService.doAction(action);
            }
        } catch (error) {
            // Esto imprimirá en la consola de Chrome el error real de Python
            console.error("Detalle del error de Odoo:", error);
            this.notification.add("Error en el servidor Odoo. Revisa el log.", { type: "danger" });
        }
    }
}

PrintCenterModal.template = "wexplay_product_print.PrintCenterModal";

registry.category("actions").add("wexplay_product_print.print_center", async (env, action) => {
    console.log("WEXPLAY_PRINT: handler ejecutado");

    env.services.notification.add("Wexplay Print: acción ejecutada", { type: "info" });

    // active_id viene del botón type="action" en la vista del producto
    const activeId = action?.context?.active_id;

    env.services.dialog.add(PrintCenterModal, {
        record: activeId ? { resId: activeId } : null,
    });

    // En algunas versiones add() devuelve una función close, en otras un id.
    // Para hacerlo universal, volvemos a abrir de forma simple:
});
