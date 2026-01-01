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
            // 1) Buscar el ir.actions.report por report_name
            const reports = await this.orm.searchRead(
                "ir.actions.report",
                [["report_name", "=", reportName]],
                ["id", "name", "report_name", "report_type"]
            );

            if (!reports.length) {
                this.notification.add(`No se encontró el reporte: ${reportName}`, { type: "danger" });
                return;
            }

            const reportId = reports[0].id;

            // 2) Generar la acción de reporte (Sintaxis corregida para Odoo 18)
            // report_action(ids, data=None, context=None)
            const action = await this.orm.call(
                "ir.actions.report",
                "report_action",
                [[reportId], [productId]],
                {
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
                this.notification.add("Etiqueta enviada al generador.", { type: "success" });
            }
        } catch (error) {
            console.error("Error en impresión:", error);
            this.notification.add("Error al llamar al servicio de impresión.", { type: "danger" });
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
