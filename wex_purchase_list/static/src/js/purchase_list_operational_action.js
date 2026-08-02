/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onMounted, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { KanbanArchParser } from "@web/views/kanban/kanban_arch_parser";
import { KanbanController } from "@web/views/kanban/kanban_controller";
import { kanbanView } from "@web/views/kanban/kanban_view";
import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";

const SELECTION_STORAGE_KEY = "wex_purchase_list.operational.selected";
const SELECTION_TTL_MS = 5 * 60 * 1000;
const RESERVATION_HERO_SECTIONS = [
    { key: "overdue", label: "Con retraso", icon: "fa-exclamation-triangle" },
    { key: "waiting_arrival", label: "Esperando llegada", icon: "fa-truck" },
    { key: "pending_notification", label: "Pendientes de aviso", icon: "fa-bell" },
    { key: "notified", label: "Ya avisadas", icon: "fa-check" },
];

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
        this.state = useState({
            selected: this.loadStoredSelection(),
        });
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
        return this.selectedRecords.map((record) => record.resId);
    }

    get selectedCount() {
        return this.selectedIds.length;
    }

    get visibleRecords() {
        return this.isGrouped ? this.collectGroupRecords(this.groups) : this.records;
    }

    get selectedRecords() {
        const selectedIds = new Set(
            Object.entries(this.state.selected)
                .filter((entry) => entry[1])
                .map((entry) => Number(entry[0]))
        );
        return this.visibleRecords.filter((record) => selectedIds.has(record.resId));
    }

    get allVisibleRecordsSelected() {
        return this.visibleRecords.length && this.visibleRecords.every((record) => this.isSelected(record));
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
        return group?.list?.groups || [];
    }

    groupRecords(group) {
        return group?.records || [];
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
        this.persistSelection();
    }

    selectVisibleRecords() {
        for (const record of this.visibleRecords) {
            this.state.selected[record.resId] = true;
        }
        this.persistSelection();
    }

    clearSelection() {
        this.state.selected = {};
        this.persistSelection();
    }

    loadStoredSelection() {
        try {
            const storedSelection = JSON.parse(
                window.sessionStorage.getItem(SELECTION_STORAGE_KEY) || "null"
            );
            window.sessionStorage.removeItem(SELECTION_STORAGE_KEY);
            if (
                this.isPageReload() ||
                !Array.isArray(storedSelection?.ids) ||
                Date.now() - storedSelection.savedAt > SELECTION_TTL_MS
            ) {
                return {};
            }
            return Object.fromEntries(storedSelection.ids.map((id) => [Number(id), true]));
        } catch {
            return {};
        }
    }

    persistSelection() {
        try {
            if (!this.selectedIds.length) {
                window.sessionStorage.removeItem(SELECTION_STORAGE_KEY);
                return;
            }
            window.sessionStorage.setItem(
                SELECTION_STORAGE_KEY,
                JSON.stringify({ ids: this.selectedIds, savedAt: Date.now() })
            );
        } catch {
            // La selección sigue funcionando aunque el navegador no permita almacenamiento de sesión.
        }
    }

    isPageReload() {
        return performance.getEntriesByType("navigation")[0]?.type === "reload";
    }

    async createRfqs() {
        const selectedIds = this.selectedIds;
        if (!selectedIds.length) {
            return;
        }
        const result = await this.orm.call("wex_purchase_list.line", "action_create_rfqs", [selectedIds]);
        this.clearSelection();
        if (result) {
            await this.action.doAction(result);
        } else {
            this.notification.add("RFQ creado desde la vista operativa.", { type: "success" });
        }
    }

    async markCustomerNotified(record, ev) {
        ev.stopPropagation();
        await this.orm.call("wex_purchase_list.line", "action_mark_customer_notified", [[record.resId]]);
        await this.props.list.model.load();
    }

    async openCustomerWhatsapp(record, ev) {
        ev.stopPropagation();
        const action = await this.orm.call(
            "wex_purchase_list.line",
            "action_open_customer_whatsapp",
            [[record.resId]]
        );
        if (action) {
            await this.action.doAction(action);
        }
    }

    canOpenCustomerWhatsapp(record) {
        return Boolean(record.data.is_reservation && record.data.customer_id);
    }

    canMarkCustomerNotified(record) {
        return Boolean(
            this.canOpenCustomerWhatsapp(record) &&
            !record.data.customer_notified &&
            record.data.state === "received"
        );
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

class WexPurchaseReservationRenderer extends WexPurchaseListOperationalRenderer {
    static template = "wex_purchase_list.ReservationListRenderer";

    setup() {
        super.setup();
        this.state.activeHeroSection = null;
        onMounted(() => this.selectHeroSection(this.activeHeroSection));
    }

    get visibleRecords() {
        return this.activeHeroRecords;
    }

    get heroSections() {
        return RESERVATION_HERO_SECTIONS.map((section) => {
            const group = this.getHeroGroup(section.key);
            return {
                ...section,
                count: group?.count || 0,
            };
        });
    }

    get activeHeroSection() {
        if (this.state.activeHeroSection) {
            return this.state.activeHeroSection;
        }
        return this.heroSections.find((section) => section.count)?.key || "waiting_arrival";
    }

    get activeHeroGroup() {
        return this.getHeroGroup(this.activeHeroSection);
    }

    get activeHeroRecords() {
        return this.groupRecords(this.activeHeroGroup);
    }

    getHeroGroup(sectionKey) {
        return this.groups.find((group) => this.getHeroGroupKey(group) === sectionKey);
    }

    getHeroGroupKey(group) {
        const candidates = [
            group.value,
            group.rawValue,
            group.data?.reservation_board_section,
            group.values?.reservation_board_section,
        ];
        for (const candidate of candidates) {
            if (RESERVATION_HERO_SECTIONS.some((section) => section.key === candidate)) {
                return candidate;
            }
            if (
                Array.isArray(candidate) &&
                RESERVATION_HERO_SECTIONS.some((section) => section.key === candidate[0])
            ) {
                return candidate[0];
            }
            if (
                candidate?.reservation_board_section &&
                RESERVATION_HERO_SECTIONS.some(
                    (section) => section.key === candidate.reservation_board_section
                )
            ) {
                return candidate.reservation_board_section;
            }
        }
        const normalizedName = (group.displayName || "").toLowerCase();
        return RESERVATION_HERO_SECTIONS.find((section) =>
            normalizedName.includes(section.label.toLowerCase())
        )?.key;
    }

    async selectHeroSection(sectionKey) {
        this.state.activeHeroSection = sectionKey;
        const group = this.getHeroGroup(sectionKey);
        if (group?.isFolded) {
            await group.toggle();
        }
    }

    async markCustomerNotified(record, ev) {
        await super.markCustomerNotified(record, ev);
        this.state.activeHeroSection = null;
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

registry.category("views").add("wex_purchase_list_reservations", {
    ...wexPurchaseListOperationalView,
    Renderer: WexPurchaseReservationRenderer,
});
