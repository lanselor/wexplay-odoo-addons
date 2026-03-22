/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { deserializeDateTime, formatDate } from "@web/core/l10n/dates";
import { registry } from "@web/core/registry";
import { RelationalModel } from "@web/model/relational_model/relational_model";
import { KanbanArchParser } from "@web/views/kanban/kanban_arch_parser";
import { KanbanCompiler } from "@web/views/kanban/kanban_compiler";
import { KanbanController } from "@web/views/kanban/kanban_controller";
import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { Component } from "@odoo/owl";

const PRIORITY_CLASS_BY_VALUE = {
    normal: "is-priority-normal",
    urgent: "is-priority-urgent",
    company: "is-priority-company",
    warranty: "is-priority-warranty",
};

export class RepairOrderCardRenderer extends Component {
    static template = "wexplay_repair.RepairOrderCardView.Renderer";
    static props = KanbanRenderer.props;
    static defaultProps = KanbanRenderer.defaultProps;

    get hasContent() {
        return this.props.list.isGrouped
            ? this.props.list.groups.length > 0
            : this.props.list.records.length > 0;
    }

    get groups() {
        return this.props.list.groups || [];
    }

    get records() {
        return this.props.list.records || [];
    }

    async openRecord(record) {
        await this.props.openRecord(record);
    }

    async openSaleOrder(record) {
        const saleOrder = record.data.sale_order_id;
        if (!Array.isArray(saleOrder) || !saleOrder[0]) {
            return;
        }
        await this.env.services.action.doAction({
            type: "ir.actions.act_window",
            res_model: "sale.order",
            res_id: saleOrder[0],
            views: [[false, "form"]],
            target: "current",
        });
    }

    async toggleGroup(group) {
        await group.toggle();
    }

    async loadMore(group) {
        await group.list.load({ limit: group.list.records.length + group.model.initialLimit });
    }

    getGroupLabel(group) {
        if (Array.isArray(group.value)) {
            return group.value[1];
        }
        return group.displayName || group.value || _t("Sin grupo");
    }

    getGroupMetaLabel() {
        const groupByFieldName = this.props.list.groupByField?.name;
        if (groupByFieldName === "create_date") {
            return _t("Creado el");
        }
        if (groupByFieldName === "schedule_date") {
            return _t("Fecha prevista");
        }
        return _t("Agrupado por");
    }

    getText(value) {
        if (Array.isArray(value)) {
            return value[1] || "";
        }
        if (value === false || value === null || value === undefined) {
            return "";
        }
        return String(value);
    }

    getSelectionLabel(record, fieldName) {
        const value = record.data[fieldName];
        const selection = record.fields[fieldName]?.selection || [];
        return selection.find(([key]) => key === value)?.[1] || this.getText(value);
    }

    formatServerDate(value) {
        if (!value) {
            return "";
        }
        if (value.isLuxonDateTime) {
            return formatDate(value);
        }
        if (typeof value === "string") {
            const normalized = value.replace("T", " ").replace(/\.\d+(?:\+\d+)?$/, "");
            try {
                return formatDate(deserializeDateTime(normalized));
            } catch {
                const isoDate = luxon.DateTime.fromISO(value);
                if (isoDate.isValid) {
                    return formatDate(isoDate);
                }
            }
        }
        return this.getText(value);
    }

    getUnlockSummary(record) {
        const unlockType = record.data.x_unlock_type;
        if (!unlockType || unlockType === "none" || unlockType === "unknown") {
            return "";
        }
        const label = this.getSelectionLabel(record, "x_unlock_type");
        const extra = record.data.x_unlock_code || record.data.x_unlock_pattern || "";
        return extra ? `${label}: ${extra}` : label;
    }

    getDeviceTitle(record) {
        return (
            this.getText(record.data.x_model_id) ||
            this.getText(record.data.product_id) ||
            _t("Sin modelo")
        );
    }

    getDeviceSubtitle(record) {
        const parts = [
            this.getText(record.data.x_device_type),
            this.getText(record.data.x_brand_id),
        ].filter(Boolean);
        return parts.join(" · ");
    }

    getPriorityClass(record) {
        return PRIORITY_CLASS_BY_VALUE[record.data.x_sat_priority] || "is-priority-normal";
    }

    getStateClass(record) {
        return `is-state-${record.data.state || "draft"}`;
    }

    hasMore(group) {
        return group.count > group.list.records.length;
    }
}

export class RepairOrderCardController extends KanbanController {
    static components = {
        ...KanbanController.components,
        KanbanRenderer: RepairOrderCardRenderer,
    };

    get modelParams() {
        return {
            ...super.modelParams,
            config: {
                ...super.modelParams.config,
                openGroupsByDefault: false,
            },
        };
    }

    get showWexGroupToggle() {
        return this.model.root.isGrouped && this.model.root.groups.length > 0;
    }

    get wexHasFoldedGroups() {
        return this.model.root.groups.some((group) => group.isFolded);
    }

    get wexGroupToggleLabel() {
        return this.wexHasFoldedGroups ? _t("Expandir grupos") : _t("Plegar grupos");
    }

    get wexGroupToggleIcon() {
        return this.wexHasFoldedGroups ? "fa-expand" : "fa-compress";
    }

    async wexToggleGroups() {
        const groups = this.model.root.groups || [];
        if (!groups.length) {
            return;
        }
        const shouldExpand = this.wexHasFoldedGroups;
        for (const group of groups) {
            if (group.isFolded === shouldExpand) {
                await group.toggle();
            }
        }
    }
}

export const repairOrderCardView = {
    type: "repair_card",
    display_name: _t("SAT Cards"),
    icon: "fa fa-window-maximize",
    multiRecord: true,
    ArchParser: KanbanArchParser,
    Controller: RepairOrderCardController,
    Model: RelationalModel,
    Renderer: RepairOrderCardRenderer,
    Compiler: KanbanCompiler,
    buttonTemplate: "wexplay_repair.RepairOrderCardView.Buttons",
    props: (genericProps, view) => {
        const { arch, relatedModels, resModel } = genericProps;
        const archInfo = new view.ArchParser().parse(arch, relatedModels, resModel);
        const defaultGroupBy =
            genericProps.searchMenuTypes.includes("groupBy") && archInfo.defaultGroupBy;

        return {
            ...genericProps,
            Model: view.Model,
            Renderer: view.Renderer,
            buttonTemplate: view.buttonTemplate,
            archInfo,
            defaultGroupBy,
        };
    },
};

registry.category("views").add("repair_card", repairOrderCardView);
