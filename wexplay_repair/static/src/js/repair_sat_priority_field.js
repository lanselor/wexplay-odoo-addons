/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Component } from "@odoo/owl";

const PRIORITY_ICONS = {
    normal: "fa fa-circle-o",
    urgent: "fa fa-bolt",
    company: "fa fa-building-o",
    warranty: "fa fa-shield",
};

class RepairSatPriorityField extends Component {
    static template = "wexplay_repair.RepairSatPriorityField";
    static props = {
        ...standardFieldProps,
    };

    get value() {
        return this.props.record.data[this.props.name] || false;
    }

    get options() {
        return this.props.record.fields[this.props.name]?.selection || [];
    }

    iconFor(value) {
        return PRIORITY_ICONS[value] || "fa fa-circle-o";
    }

    async selectValue(value) {
        if (this.props.readonly) {
            return;
        }
        await this.props.record.update({ [this.props.name]: value });
    }
}

export const repairSatPriorityField = {
    component: RepairSatPriorityField,
    displayName: "Repair SAT Priority",
    supportedTypes: ["selection"],
};

registry.category("fields").add("wex_repair_sat_priority", repairSatPriorityField);
