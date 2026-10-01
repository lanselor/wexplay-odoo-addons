/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { browser } from "@web/core/browser/browser";
import { download } from "@web/core/network/download";
import { printOdooDocument } from "@wex_print_core/js/qz_print";

class TeardownBatchLabelPrintModal extends Component {
    setup() {
        this.notification = useService("notification");
        this.orm = useService("orm");
        this.state = useState({ qty: 1 });
    }

    close() {
        this.props.close();
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

    _reportPath(reportName) {
        return `/report/pdf/${reportName}/${this.props.batchId}`;
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

    async _getLabelPayload(batchId) {
        return this.orm.call("wex.teardown.batch", "action_get_zebra_batch_label_payload", [[batchId]]);
    }

    async downloadLabel() {
        const batchId = this.props.batchId;
        if (!batchId) {
            this.notification.add("No se pudo determinar el lote de despiece.", { type: "danger" });
            return;
        }
        try {
            const payload = await this._getLabelPayload(batchId);
            await this._downloadPdf(payload.report_name);
            this.notification.add("Etiqueta de lote descargada.", { type: "success" });
        } catch (error) {
            console.error("WEXPLAY_PRINT: error descargando etiqueta de lote", error);
            this.notification.add(`Error descargando la etiqueta: ${error?.message || error}`, { type: "danger" });
        }
    }

    async printLabel() {
        const batchId = this.props.batchId;
        if (!batchId) {
            this.notification.add("No se pudo determinar el lote de despiece.", { type: "danger" });
            return;
        }
        try {
            const payload = await this._getLabelPayload(batchId);
            const reportUrl = new URL(this._reportPath(payload.report_name), browser.location.origin).toString();
            await printOdooDocument(payload.document_code, reportUrl, this.env, {
                copies: this._sanitizeQty(this.state.qty),
                reportName: payload.report_name,
                requireNewResolution: true,
            });
            this.notification.add(`Etiqueta de lote enviada (${this.state.qty} copias).`, { type: "success" });
        } catch (error) {
            console.error("WEXPLAY_PRINT: error etiqueta de lote", error);
            this.notification.add(`Error imprimiendo la etiqueta: ${error?.message || error}`, { type: "danger" });
        }
    }
}

TeardownBatchLabelPrintModal.template = "wex_teardown.TeardownBatchLabelPrintModal";

registry.category("actions").add("wex_teardown.print_batch_label", async (env, action) => {
    env.services.dialog.add(TeardownBatchLabelPrintModal, {
        batchId: action?.context?.active_id,
    });
});