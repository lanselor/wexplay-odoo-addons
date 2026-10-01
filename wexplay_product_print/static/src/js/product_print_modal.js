/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { browser } from "@web/core/browser/browser";
import { download } from "@web/core/network/download";
import { printOdooDocument } from "@wex_print_core/js/qz_print";

class PrintCenterModal extends Component {
    setup() {
        this.notification = useService("notification");
        this.orm = useService("orm");
        this.state = useState({ qty: 1 });
    }

    close() {
        this.props.close();
    }

    _getActiveId() {
        return this.props.record?.resId;
    }

    _reportPath(reportName) {
        return `/report/pdf/${reportName}/${this._getActiveId()}`;
    }

    _reportUrl(reportName) {
        return new URL(this._reportPath(reportName), browser.location.origin).toString();
    }

    async _downloadPdf(reportName) {
        await download({
            url: "/report/download",
            data: {
                data: JSON.stringify([this._reportPath(reportName), "qweb-pdf"]),
                context: JSON.stringify(this.env.services?.user?.context || {}),
            },
        });
    }

    _sanitizeQty(value) {
        const quantity = Number.parseInt(value, 10);
        return Number.isNaN(quantity) || quantity < 1 ? 1 : quantity;
    }

    onQtyInput(event) {
        this.state.qty = this._sanitizeQty(event.target.value);
    }

    incrementQty() {
        this.state.qty = this._sanitizeQty(this.state.qty + 1);
    }

    decrementQty() {
        this.state.qty = this._sanitizeQty(this.state.qty - 1);
    }

    async _getZebraPayload(productId) {
        return this.orm.call("product.template", "action_get_zebra_label_payload", [[productId]]);
    }

    async downloadZebraLabel() {
        const productId = this._getActiveId();
        if (!productId) {
            this.notification.add("No se pudo determinar el producto actual.", { type: "danger" });
            return;
        }
        try {
            const payload = await this._getZebraPayload(productId);
            await this._downloadPdf(payload.report_name);
            this.notification.add("Etiqueta Zebra descargada.", { type: "success" });
        } catch (error) {
            console.error("WEXPLAY_PRINT: error descargando etiqueta Zebra", error);
            this.notification.add(`Error descargando la etiqueta Zebra: ${error?.message || error}`, { type: "danger" });
        }
    }

    async printZebraLabel() {
        const productId = this._getActiveId();
        if (!productId) {
            this.notification.add("No se pudo determinar el producto actual.", { type: "danger" });
            return;
        }
        try {
            const payload = await this._getZebraPayload(productId);
            await printOdooDocument(payload.document_code, this._reportUrl(payload.report_name), this.env, {
                copies: this._sanitizeQty(this.state.qty),
                reportName: payload.report_name,
                requireNewResolution: true,
            });
            this.notification.add(`Etiqueta Zebra enviada (${this.state.qty} copias).`, { type: "success" });
        } catch (error) {
            console.error("WEXPLAY_PRINT: error etiqueta Zebra", error);
            this.notification.add(`Error imprimiendo la etiqueta Zebra: ${error?.message || error}`, { type: "danger" });
        }
    }

    async printBrotherLabel() {
        const productId = this._getActiveId();
        if (!productId) {
            this.notification.add("No se pudo determinar el producto actual.", { type: "danger" });
            return;
        }
        const reportName = "wexplay_product_print.report_product_label_ql700_62x29";
        try {
            await printOdooDocument("product_label", this._reportUrl(reportName), this.env, {
                copies: this._sanitizeQty(this.state.qty),
                reportName,
            });
            this.notification.add(`Etiqueta Brother enviada (${this.state.qty} copias).`, { type: "success" });
        } catch (error) {
            console.error("WEXPLAY_PRINT: error etiqueta Brother", error);
            this.notification.add(`Error imprimiendo la etiqueta Brother: ${error?.message || error}`, { type: "danger" });
        }
    }
}

PrintCenterModal.template = "wexplay_product_print.PrintCenterModal";

registry.category("actions").add("wexplay_product_print.print_center", async (env, action) => {
    const activeId = action?.context?.active_id;
    env.services.dialog.add(PrintCenterModal, { record: activeId ? { resId: activeId } : null });
});