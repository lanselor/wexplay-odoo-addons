/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { deserializeDateTime, formatDate } from "@web/core/l10n/dates";
import { registry } from "@web/core/registry";
import { useBus, useService } from "@web/core/utils/hooks";
import { RelationalModel } from "@web/model/relational_model/relational_model";
import { KanbanArchParser } from "@web/views/kanban/kanban_arch_parser";
import { KanbanCompiler } from "@web/views/kanban/kanban_compiler";
import { KanbanController } from "@web/views/kanban/kanban_controller";
import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { Component, onMounted, onWillStart, onWillUnmount, useState } from "@odoo/owl";

const PRIORITY_CLASS_BY_VALUE = {
    normal: "is-priority-normal",
    urgent: "is-priority-urgent",
    company: "is-priority-company",
    warranty: "is-priority-warranty",
    budget: "is-priority-company",
    budget_extended: "is-priority-company",
    express: "is-priority-urgent",
};

const AUTOREFRESH_MS = 5 * 60 * 1000;
const REPAIR_ORDER_VIEW_MODE = "repair_card,list,kanban,graph,pivot,form,activity";

export class RepairOrderCardRenderer extends Component {
    static template = "wexplay_repair.RepairOrderCardView.Renderer";
    static viewType = "repair_card";
    static props = KanbanRenderer.props;
    static defaultProps = KanbanRenderer.defaultProps;

    setup() {
        this.orm = useService("orm");
        this.sidebarState = useState({
            loading: true,
            sections: [],
            groups: [],
            generatedAt: null,
        });
        this.heroState = useState({
            loading: true,
            sections: [],
            indicators: [],
        });
        this._autoRefreshTimer = null;

        onWillStart(async () => {
            await Promise.all([this.loadSidebar(), this.loadHero()]);
        });
        if (this.env.searchModel) {
            useBus(this.env.searchModel, "update", () => {
                this.loadSidebar();
                this.loadHero();
            });
        }
        onMounted(() => {
            this._autoRefreshTimer = setInterval(() => {
                this.loadSidebar();
                this.loadHero();
            }, AUTOREFRESH_MS);
        });
        onWillUnmount(() => {
            if (this._autoRefreshTimer) {
                clearInterval(this._autoRefreshTimer);
                this._autoRefreshTimer = null;
            }
        });
    }

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

    get sidebarSections() {
        return this.sidebarState.sections || [];
    }

    get sidebarGroups() {
        return this.sidebarState.groups || [];
    }

    get sidebarGeneratedAt() {
        return this.sidebarState.generatedAt
            ? this.formatServerDate(this.sidebarState.generatedAt)
            : "";
    }

    get heroSections() {
        return this.heroState.sections || [];
    }

    get heroIndicators() {
        return this.heroState.indicators || [];
    }

    get repairCardViewType() {
        return this.constructor.viewType || "repair_card";
    }

    getRepairOrderViews() {
        return [
            [false, this.repairCardViewType],
            [false, "list"],
            [false, "kanban"],
            [false, "graph"],
            [false, "pivot"],
            [false, "form"],
            [false, "activity"],
        ].filter((view, index, views) =>
            index === views.findIndex((candidate) => candidate[1] === view[1])
        );
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

    async loadSidebar() {
        this.sidebarState.loading = true;
        try {
            const data = await this.orm.call(
                "repair.order",
                "get_repair_card_sidebar_metrics_data",
                [this.getPanelBaseDomain()],
                {}
            );
            this.sidebarState.groups = data.groups || [];
            this.sidebarState.generatedAt = data.generated_at || null;
        } finally {
            this.sidebarState.loading = false;
        }
    }

    async loadHero() {
        this.heroState.loading = true;
        try {
            const data = await this.orm.call(
                "repair.order",
                "get_repair_card_hero_data",
                [this.getPanelBaseDomain()],
                {}
            );
            this.heroState.sections = data.sections || [];
            this.heroState.indicators = data.indicators || [];
        } finally {
            this.heroState.loading = false;
        }
    }

    getActiveSearchDomain() {
        if (this.env.searchModel) {
            return this.env.searchModel.searchDomain || this.env.searchModel.domain || [];
        }
        return this.props.list?.model?.root?.domain || [];
    }

    getPanelBaseDomain() {
        return this.env.searchModel?.globalContext?.wex_repair_panel_base_domain || this.getActiveSearchDomain();
    }

    getActiveHeroKey() {
        return this.env.searchModel?.globalContext?.wex_repair_active_hero || "";
    }

    getHeroTabClass(section) {
        const classes = ["wex_v2_hero_tab"];
        if (section?.key && section.key === this.getActiveHeroKey()) {
            classes.push("is-active");
        }
        return classes.join(" ");
    }

    getHeroIndicatorClass(indicator) {
        const classes = ["wex_v2_hero_indicator", `is-severity-${indicator.severity || "muted"}`];
        if (!indicator.enabled) {
            classes.push("is-disabled");
        }
        return classes.join(" ");
    }

    getSidebarMetricClass(metric) {
        const classes = ["wex_v2_sidebar_metric", `is-severity-${metric.severity || "muted"}`];
        if (!metric.enabled) {
            classes.push("is-disabled");
        }
        return classes.join(" ");
    }

    getSidebarGroupClass(group) {
        return `wex_v2_sidebar_metric_group is-severity-${group.severity || "muted"}`;
    }

    getCurrentSearchDefaultsContext() {
        const globalContext = this.env.searchModel?.globalContext || {};
        const defaultsFromContext = Object.fromEntries(
            Object.entries(globalContext).filter(([key, value]) =>
                key.startsWith("search_default_") && value
            )
        );
        const defaultsFromActiveFilters = {};
        const searchModel = this.env.searchModel;
        for (const queryElement of searchModel?.query || []) {
            const searchItem = searchModel.searchItems?.[queryElement.searchItemId];
            if (searchItem?.name) {
                defaultsFromActiveFilters[`search_default_${searchItem.name}`] = 1;
            }
        }
        return {
            ...defaultsFromContext,
            ...defaultsFromActiveFilters,
        };
    }

    async openSidebarRecord(item) {
        await this.env.services.action.doAction({
            type: "ir.actions.act_window",
            res_model: "repair.order",
            res_id: item.id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    async openHeroSection(section) {
        if (!section.domain?.length) {
            return;
        }
        await this.env.services.action.doAction({
            type: "ir.actions.act_window",
            name: _t("Ordenes de reparacion"),
            res_model: "repair.order",
            views: this.getRepairOrderViews(),
            view_mode: REPAIR_ORDER_VIEW_MODE,
            domain: section.domain,
            target: "current",
            context: {
                ...this.getCurrentSearchDefaultsContext(),
                search_default_group_by_create_date_day: 1,
                wex_repair_panel_base_domain: this.getPanelBaseDomain(),
                wex_repair_active_hero: section.key,
            },
        }, {
            clearBreadcrumbs: true,
        });
    }

    async openHeroIndicator(indicator) {
        if (!indicator.enabled || !indicator.domain?.length) {
            return;
        }
        await this.openMetricDomain(indicator.title || _t("Ordenes de reparacion"), indicator.domain);
    }

    async openSidebarMetric(metric) {
        if (!metric.enabled || !metric.domain?.length) {
            return;
        }
        await this.openMetricDomain(metric.title || _t("Ordenes de reparacion"), metric.domain);
    }

    async openMetricDomain(title, domain) {
        await this.env.services.action.doAction({
            type: "ir.actions.act_window",
            name: title,
            res_model: "repair.order",
            views: this.getRepairOrderViews(),
            view_mode: REPAIR_ORDER_VIEW_MODE,
            domain,
            target: "current",
            context: {
                ...this.getCurrentSearchDefaultsContext(),
                search_default_group_by_create_date_day: 1,
                wex_repair_panel_base_domain: this.getPanelBaseDomain(),
            },
        }, {
            clearBreadcrumbs: true,
        });
    }

    async openSidebarSection(section) {
        if (!section.domain?.length) {
            return;
        }
        await this.env.services.action.doAction({
            type: "ir.actions.act_window",
            name: section.title || _t("Repair Orders"),
            res_model: "repair.order",
            views: this.getRepairOrderViews(),
            view_mode: REPAIR_ORDER_VIEW_MODE,
            domain: section.domain,
            target: "current",
            context: {
                ...this.getCurrentSearchDefaultsContext(),
                search_default_group_by_create_date_day: 1,
                wex_repair_panel_base_domain: this.getPanelBaseDomain(),
            },
        });
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

    getSidebarItemAgeLabel(item) {
        if (item?.alert_label) {
            return item.alert_label;
        }
        if (!item?.age_days) {
            return _t("Hoy");
        }
        if (item.age_days === 1) {
            return _t("1 dia sin movimiento");
        }
        return _t("%s dias sin movimiento").replace("%s", item.age_days);
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
