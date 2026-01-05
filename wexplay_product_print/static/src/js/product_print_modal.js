/** @odoo-module **/

console.log("WEXPLAY_PRINT: JS cargado");

import { registry } from "@web/core/registry";  
import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { printImageBase64, printQzPdfFileUrl } from "./qz_print";
import { rpc } from "@web/core/network/rpc";

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
            product_tmpl_ids: [[6, 0, [productId]]], // many2many
            print_format: "2x7xprice",
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
        if (action?.type === "ir.actions.report") {
            const printerName = "Brother QL-710W";

            // Tu reporte custom (NO dependemos del report_name del wizard)
            const reportName = "wexplay_product_print.report_product_label_ql700_62x29";

            // IDs a imprimir (usa los del context si vienen; fallback a productId)
            const ids =
                action.context?.active_ids ||
                (action.context?.active_id ? [action.context.active_id] : []) ||
                (productId ? [productId] : []);

            if (!ids.length) {
                throw new Error("No se encontraron IDs para imprimir el reporte.");
            }

            // URL del PDF (puedes usar ids[0] o productId; aquí uso ids[0])
            // Pedir URL firmada al backend (requiere estar logueado; auth=user)
            const { pdf_url } = await rpc("/wexplay/label/signed_url", { product_id: ids[0] });

            console.log("WEXPLAY_PRINT signed pdf_url:", pdf_url, { reportName, ids, printerName });

            // Enviar a QZ usando URL pública tokenizada (auth=public)
            await printQzPdfFileUrl(pdf_url, printerName);

            this.notification.add("Etiqueta enviada a QZ correctamente.", { type: "success" });

        } else {
            await this.actionService.doAction(action);
            this.notification.add("Etiqueta generada correctamente.", { type: "success" });
        }
    } catch (error) {
        console.error("WEXPLAY_PRINT: error impresión", error);
        this.notification.add(`Error generando la etiqueta: ${error?.message || error}`, { type: "danger" });
    }
}


    async printTestQz() {
        try {
            // PNG 1x1 transparente (solo para comprobar canal de impresión)
            const tinyPng =
                "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgYAAAAAMAASsJTYQAAAAASUVORK5CYII=";

            const printerName = "Brother QL-710W";
            await printImageBase64(tinyPng, printerName);

            this.notification.add(`QZ: trabajo enviado a ${printerName}.`, { type: "success" });
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
});
