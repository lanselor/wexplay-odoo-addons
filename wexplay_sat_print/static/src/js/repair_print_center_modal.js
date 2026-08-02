// wexplay_sat_print/static/src/js/repair_print_center_modal.js
/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { browser } from "@web/core/browser/browser";
import { printOdooDocument } from "@wex_print_core/js/qz_print";

// NOTA: mantenemos estas constantes por compatibilidad temporal,
// pero ya no se usan cuando migramos todo a ByKind.
const DEFAULT_LABEL_PRINTER = "Brother QL-710W";
const DEFAULT_TICKET_PRINTER = "Thermal 80mm";

export class SatPrintCenterModal extends Component {
    setup() {
        this.notification = useService("notification");
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.dialog = useService("dialog");

        // Estado de cantidad y progreso visible de los trabajos enviados a QZ.
        this.state = useState({
            accessoryQty: 1,
            isPrinting: false,
            totalTasks: 0,
            completedTasks: 0,
            currentTaskLabel: "",
        });
    }

    close() {
        if (this.state.isPrinting) {
            return;
        }
        this.props.close();
    }

    get progressPercentage() {
        if (!this.state.totalTasks) {
            return 0;
        }
        return Math.round((this.state.completedTasks / this.state.totalTasks) * 100);
    }

    _abs(url) {
        return new URL(url, browser.location.origin).toString();
    }

    _getActiveId() {
        return this.props.record?.resId;
    }

    _reportUrl(reportName) {
        const id = this._getActiveId();
        return this._abs(`/report/pdf/${reportName}/${id}`);
    }

    // ------------------------------
    // Qty helpers (mínimo 1)
    // ------------------------------
    _sanitizeQty(value) {
        const n = Number.parseInt(value, 10);
        if (Number.isNaN(n) || n < 1) return 1;
        return n;
    }

    onAccessoryQtyInput(ev) {
        this.state.accessoryQty = this._sanitizeQty(ev.target.value);
    }

    incrementAccessoryQty() {
        this.state.accessoryQty = this._sanitizeQty(this.state.accessoryQty + 1);
    }

    decrementAccessoryQty() {
        this.state.accessoryQty = this._sanitizeQty(this.state.accessoryQty - 1);
    }

    // ------------------------------
    // Acciones
    // ------------------------------
    async onPrintAll() {
        await this._runPrintBatch(
            [
                this._getMainLabelTask(),
                this._getAccessoryLabelTask(),
                this._getTicketTask(),
            ],
            "Impresión completa enviada a QZ Tray."
        );
    }
    
    async onPrintSat() {
        await this._runPrintBatch(
            [this._getMainLabelTask(), this._getTicketTask()],
            "Impresión de recogida enviada a QZ Tray."
        );
    }

    async onPrintLabel29x90() {
        await this._runPrintBatch([this._getMainLabelTask()]);
    }

    async onPrintLabel29x42() {
        await this._runPrintBatch([this._getAccessoryLabelTask()]);
    }

    async onPrintTicket80x170() {
        await this._runPrintBatch([this._getTicketTask()]);
    }

    _getMainLabelTask() {
        return {
            label: "etiqueta SAT completa",
            documentCode: "sat_label_main",
            reportName: "wexplay_sat_print.report_repair_label_29x90",
            options: { copies: 1 },
        };
    }

    _getAccessoryLabelTask() {
        return {
            label: "etiquetas de accesorios",
            documentCode: "sat_label_accessory",
            reportName: "wexplay_sat_print.report_repair_label_29x42",
            // La cantidad sigue siendo copias del mismo trabajo QZ, no tareas separadas.
            options: { copies: this._sanitizeQty(this.state.accessoryQty) },
        };
    }

    _getTicketTask() {
        return {
            label: "resguardo",
            documentCode: "sat_ticket",
            reportName: "wexplay_sat_print.report_repair_ticket_80x170",
            options: {},
        };
    }

    async _runPrintBatch(tasks, successMessage = false) {
        const id = this._getActiveId();
        if (!id || this.state.isPrinting) {
            if (!id) {
                this.notification.add("No se pudo determinar la orden de reparación.", { type: "danger" });
            }
            return;
        }

        this._startPrintBatch(tasks);
        let allTasksSucceeded = true;

        try {
            for (const task of tasks) {
                this.state.currentTaskLabel = task.label;
                const taskSucceeded = await this._printDocument(task);
                allTasksSucceeded = allTasksSucceeded && taskSucceeded;
                this.state.completedTasks += 1;
            }

            if (successMessage && allTasksSucceeded) {
                this.notification.add(successMessage, { type: "success" });
            }
        } finally {
            this._finishPrintBatch();
        }
    }

    _startPrintBatch(tasks) {
        this.state.isPrinting = true;
        this.state.totalTasks = tasks.length;
        this.state.completedTasks = 0;
        this.state.currentTaskLabel = tasks[0]?.label || "documentos";
    }

    _finishPrintBatch() {
        this.state.isPrinting = false;
        this.state.totalTasks = 0;
        this.state.completedTasks = 0;
        this.state.currentTaskLabel = "";
    }

    // API única de impresión en el modal: todo pasa por el documento lógico.
    async _printDocument(task) {
        const reportUrl = this._reportUrl(task.reportName);

        try {
            await printOdooDocument(task.documentCode, reportUrl, this.env, {
                ...task.options,
                reportName: task.reportName,
            });

            const copies = Number.isInteger(task.options.copies) && task.options.copies > 0
                ? task.options.copies
                : 1;
            const isLabel = task.documentCode === "sat_label_main" || task.documentCode === "sat_label_accessory";
            if (isLabel && copies > 1) {
                this.notification.add(`Impresión enviada a QZ Tray (${copies} copias).`, { type: "success" });
            } else {
                this.notification.add("Impresión enviada a QZ Tray.", { type: "success" });
            }
            return true;
        } catch (e) {
            this.notification.add(`Error imprimiendo: ${e?.message || e}`, { type: "danger" });
            return false;
        }
    }
}

SatPrintCenterModal.template = "wexplay_sat_print.SatPrintCenterModal";
