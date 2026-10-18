/** @odoo-module **/
import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

class AdvanceNotice extends Component {
    static template = "wexplay_repair_advances.Notice";
    static props = { ...standardFieldProps };
}

registry.category("fields").add("wex_advance_notice", {
    component: AdvanceNotice,
    supportedTypes: ["char"],
});
