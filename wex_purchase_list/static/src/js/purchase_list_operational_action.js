/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { KanbanArchParser } from "@web/views/kanban/kanban_arch_parser";
import { KanbanController } from "@web/views/kanban/kanban_controller";
import { kanbanView } from "@web/views/kanban/kanban_view";
import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";

class WexPurchaseListOperationalArchParser extends KanbanArchParser {
    parse(xmlDoc, models, modelName) {
        if (!xmlDoc.querySelector('[t-name="card"]')) {
            const templates = xmlDoc.ownerDocument.createElement("templates");
            const card = xmlDoc.ownerDocument.createElement("t");
            const placeholder = xmlDoc.ownerDocument.createElement("div");
            card.setAttribute("t-name", "card");
            card.appendChild(placeholder);
            templates.appendChild(card);
            xmlDoc.appendChild(templates);
        }
        return super.parse(xmlDoc, models, modelName);
    }
}

class WexPurchaseListOperationalRenderer extends Component {
    static template = "wex_purchase_list.OperationalListRenderer";
    static props = KanbanRenderer.props;

    setup() {
        this.action = useService("action");
        this.notification = useService("notification");
        this.orm = useService("orm");
        this.state = useState({ selected: {} });
    }

    get records() {
        return this.props.list.records || [];
    }

    get isGrouped() {
        return Boolean(this.props.list.isGrouped);
    }

    get groups() {
        return this.props.list.groups || [];
    }

    get selectedIds() {
        return Object.entries(this.state.selected)
            .filter((entry) => entry[1])
            .map((entry) => Number(entry[0]));
    }

    get selectedCount() {
        return this.selectedIds.length;
    }

    get visibleRecords() {
        return this.isGrouped ? this.collectGroupRecords(this.groups) : this.records;
    }

    get selectedRecords() {
        const selectedIds = new Set(this.selectedIds);
        return this.visibleRecords.filter((record) => selectedIds.has(record.resId));
    }

    get selectedLinkCount() {
        return this.selectedRecords.filter((record) => record.data.vendor_url).length;
    }

    m2oName(value) {
        return Array.isArray(value) ? value[1] : "";
    }

    value(record, fieldName) {
        return record.data[fieldName];
    }

    stateLabel(value) {
        return {
            draft_wait_customer: "Espera",
            to_purchase: "Pendiente",
            ordered: "Pedido",
            received: "Recibido",
            cancelled: "Cancelado",
        }[value] || value || "-";
    }

    followupLabel(value) {
        return {
            not_reservation: "No reserva",
            waiting_arrival: "Esperando llegada",
            pending_notification: "Pendiente aviso",
            overdue: "Con retraso",
            notified: "Avisado",
        }[value] || "-";
    }

    rowClass(record, depth = 0) {
        const data = record.data;
        const classes = ["wex_pl_row", `is-depth-${depth}`];
        if (
            data.is_notification_overdue ||
            data.is_request_overdue ||
            data.reservation_followup_state === "overdue"
        ) {
            classes.push("is-overdue");
        }
        if (data.state) {
            classes.push(`is-state-${data.state}`);
        }
        return classes.join(" ");
    }

    reservationClass(record) {
        return record.data.is_reservation ? "wex_pl_badge is-reservation" : "wex_pl_badge is-normal";
    }

    followupClass(record) {
        return `wex_pl_badge is-followup is-${record.data.reservation_followup_state || "not_reservation"}`;
    }

    collectGroupRecords(groups) {
        return groups.flatMap((group) => {
            const childGroups = this.groupGroups(group);
            return childGroups.length ? this.collectGroupRecords(childGroups) : this.groupRecords(group);
        });
    }

    groupClass(depth = 0) {
        return `wex_pl_group is-depth-${depth}`;
    }

    groupGroups(group) {
        return group.list?.groups || [];
    }

    groupRecords(group) {
        return group.records || [];
    }

    async toggleGroup(group, ev) {
        ev.stopPropagation();
        await group.toggle();
    }

    openRecord(record) {
        this.props.openRecord(record);
    }

    isSelected(record) {
        return Boolean(this.state.selected[record.resId]);
    }

    toggleRecord(record, ev) {
        ev.stopPropagation();
        this.state.selected[record.resId] = !this.state.selected[record.resId];
    }

    async createRfqs() {
        const selectedIds = this.selectedIds;
        if (!selectedIds.length) {
            return;
        }
        const result = await this.orm.call("wex_purchase_list.line", "action_create_rfqs", [selectedIds]);
        this.state.selected = {};
        if (result) {
            await this.action.doAction(result);
        } else {
            this.notification.add("RFQ creado desde la vista operativa.", { type: "success" });
        }
    }

    openSelectedLinks() {
        for (const record of this.selectedRecords) {
            const url = record.data.vendor_url;
            if (url) {
                window.open(url, "_blank", "noopener");
            }
        }
    }

    stopClick(ev) {
        ev.stopPropagation();
    }
}

class WexPurchaseListOperationalController extends KanbanController {
    get modelParams() {
        return {
            ...super.modelParams,
            maxGroupByDepth: 2,
        };
    }
}

export const wexPurchaseListOperationalView = {
    ...kanbanView,
    type: "wex_operational_list",
    ArchParser: WexPurchaseListOperationalArchParser,
    Controller: WexPurchaseListOperationalController,
    Renderer: WexPurchaseListOperationalRenderer,
};

registry.category("views").add("wex_purchase_list_operational", wexPurchaseListOperationalView);
