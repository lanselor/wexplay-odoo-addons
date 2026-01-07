/** @odoo-module **/

import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { printOdooPdfUrl } from "wexplay_product_print/static/src/js/qz_print";

export class RepairPrintCenterModal extends Component {
    static template = "wexplay_repair.RepairPrintCenterModal";
    static props = {
        repairId: { type: Number, optional: true },
    };

    setup() {
        this.notification = useService("notification");
        this.dialog = useService("dialog");
    }

    _ensureRepairId() {
        if (!this.props.repairId) {
            this.notification.add("No se pudo determinar la reparación activa.", { type: "danger" });
            return false;
        }
        return true;
    }

    async onPrintFullLabel() {
        if (!this._ensureRepairId()) return;

        const reportName = "wexplay_repair.report_sat_label_29x90";
        const url = `/report/pdf/${reportName}/${this.props.repairId}`;

        await printOdooPdfUrl(url, "Brother QL-710W");
        this.notification.add("Impresión enviada (Etiqueta completa).", { type: "success" });
    }

    async onPrintAccessoriesLabel() {
        if (!this._ensureRepairId()) return;

        const reportName = "wexplay_repair.report_sat_label_29x42";
        const url = `/report/pdf/${reportName}/${this.props.repairId}`;

        await printOdooPdfUrl(url, "Brother QL-710W");
        this.notification.add("Impresión enviada (Etiqueta accesorios).", { type: "success" });
    }

    async onPrintTicket() {
        if (!this._ensureRepairId()) return;

        const reportName = "wexplay_repair.report_sat_ticket_80x170";
        const url = `/report/pdf/${reportName}/${this.props.repairId}`;

        // Aquí normalmente usarías una impresora distinta
        await printOdooPdfUrl(url, "Thermal 80mm");
        this.notification.add("Impresión enviada (Resguardo).", { type: "success" });
    }

    onClose() {
        this.dialog.close();
    }
}
