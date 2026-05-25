/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { RelationalModel } from "@web/model/relational_model/relational_model";
import { KanbanArchParser } from "@web/views/kanban/kanban_arch_parser";
import { KanbanCompiler } from "@web/views/kanban/kanban_compiler";
import { RepairOrderCardRenderer, RepairOrderCardController } from "./repair_order_card_view";

export class RepairOrderCardV2Renderer extends RepairOrderCardRenderer {
    static template = "wexplay_repair.RepairOrderCardV2.Renderer";
    static viewType = "repair_card_v2";
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
