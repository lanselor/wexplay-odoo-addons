/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useBus } from "@web/core/utils/hooks";
import { RelationalModel } from "@web/model/relational_model/relational_model";
import { KanbanArchParser } from "@web/views/kanban/kanban_arch_parser";
import { KanbanCompiler } from "@web/views/kanban/kanban_compiler";
import { onMounted, onWillStart, onWillUnmount, useState } from "@odoo/owl";
import { RepairOrderCardRenderer, RepairOrderCardController } from "./repair_order_card_view";

const AUTOREFRESH_MS = 5 * 60 * 1000;

export class RepairOrderCardV2Renderer extends RepairOrderCardRenderer {
    static template = "wexplay_repair.RepairOrderCardV2.Renderer";

    setup() {
        super.setup();
        this.heroState = useState({
            loading: true,
            sections: [],
        });
        this._autoRefreshTimer = null;
        onWillStart(async () => {
            await this.loadHero();
        });
        if (this.env.searchModel) {
            useBus(this.env.searchModel, "update", () => {
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

    getSidebarSectionSeverityClass(section) {
        if (!section.count) return "is-severity-ok";
        if (section.count > 5) return "is-severity-critical";
        return "is-severity-warning";
    }

    getSidebarProgressWidth(section) {
        if (!section.count) return "0%";
        return Math.round((section.shown_count / section.count) * 100) + "%";
    }

    get heroSections() {
        return this.heroState.sections || [];
    }

    getActiveHeroKey() {
        return this.env.searchModel?.globalContext?.wex_v2_active_hero || "";
    }

    getHeroTabClass(section) {
        const classes = ["wex_v2_hero_tab"];
        if (section?.key && section.key === this.getActiveHeroKey()) {
            classes.push("is-active");
        }
        return classes.join(" ");
    }

    getActiveSearchDomain() {
        if (this.env.searchModel) {
            return this.env.searchModel.searchDomain || this.env.searchModel.domain || [];
        }
        return this.props.list?.model?.root?.domain || [];
    }

    async loadHero() {
        this.heroState.loading = true;
        try {
            const data = await this.orm.call(
                "repair.order",
                "get_repair_card_v2_hero_data",
                [this.getActiveSearchDomain()],
                {}
            );
            this.heroState.sections = data.sections || [];
        } finally {
            this.heroState.loading = false;
        }
    }

    async openHeroSection(section) {
        if (!section.domain?.length) {
            return;
        }
        await this.env.services.action.doAction({
            type: "ir.actions.act_window",
            name: _t("Ordenes de reparacion"),
            res_model: "repair.order",
            views: [
                [false, "repair_card_v2"],
                [false, "list"],
                [false, "form"],
            ],
            view_mode: "repair_card_v2,list,form",
            domain: section.domain,
            target: "current",
            context: {
                ...this.getCurrentSearchDefaultsContext(),
                search_default_group_by_create_date_day: 1,
                wex_v2_active_hero: section.key,
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
            name: section.title || _t("Ordenes de reparacion"),
            res_model: "repair.order",
            views: [
                [false, "repair_card_v2"],
                [false, "list"],
                [false, "form"],
            ],
            view_mode: "repair_card_v2,list,form",
            domain: section.domain,
            target: "current",
            context: {
                ...this.getCurrentSearchDefaultsContext(),
                search_default_group_by_create_date_day: 1,
            },
        }, {
            clearBreadcrumbs: true,
        });
    }
}

export class RepairOrderCardV2Controller extends RepairOrderCardController {
    static components = {
        ...RepairOrderCardController.components,
        KanbanRenderer: RepairOrderCardV2Renderer,
    };
}

export const repairOrderCardV2View = {
    type: "repair_card_v2",
    display_name: _t("SAT Compact"),
    icon: "fa fa-th-list",
    multiRecord: true,
    ArchParser: KanbanArchParser,
    Controller: RepairOrderCardV2Controller,
    Model: RelationalModel,
    Renderer: RepairOrderCardV2Renderer,
    Compiler: KanbanCompiler,
    buttonTemplate: "wexplay_repair.RepairOrderCardV2.Buttons",
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

registry.category("views").add("repair_card_v2", repairOrderCardV2View);
