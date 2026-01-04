/** @odoo-module **/

console.log("WEXPLAY_PRINT: JS cargado");

import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { printImageBase64 } from "./qz_print";


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

        try {
            // 1) Crear wizard product.label.layout
            const created = await this.orm.create("product.label.layout", [{
                product_tmpl_ids: [[6, 0, [productId]]],   // ✅ many2many
                print_format: "2x7xprice",                 // ✅ válido según tu selección
                custom_quantity: 1,
                move_quantity: "custom",
            }]);

            const wizardId = Array.isArray(created) ? created[0] : created;

            // 2) Ejecutar process
            const action = await this.orm.call(
                "product.label.layout",
                "process",
                [[wizardId]],
                {
                    context: {
                        active_model: "product.template",
                        active_id: productId,
                        active_ids: [productId],
                    },
                }
            );

            // 3) Ejecutar acción
            if (action) {
                await this.actionService.doAction(action);
                this.notification.add("Etiqueta generada correctamente.", { type: "success" });
            }
        } catch (error) {
            console.error("WEXPLAY_PRINT: error impresión", error);
            this.notification.add("Error generando la etiqueta.", { type: "danger" });
        }
    }

        async printTestQz() {
        try {
            // PNG 1x1 transparente (solo para comprobar canal de impresión)
            const tinyPng =
                "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgYAAAAAMAASsJTYQAAAAASUVORK5CYII=";

            await printImageBase64(tinyPng, "Brother QL-700");
            this.notification.add("QZ: trabajo enviado a la Brother QL-700.", { type: "success" });
        } catch (error) {
            console.error("WEXPLAY_PRINT: error QZ test", error);
            this.notification.add(
                "QZ: error enviando a impresora. Revisa QZ Tray abierto y nombre de impresora.",
                { type: "danger" }
            );
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
