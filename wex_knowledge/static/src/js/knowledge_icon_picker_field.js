/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Component, useState } from "@odoo/owl";

class KnowledgeIconPickerField extends Component {
    static template = "wex_knowledge.KnowledgeIconPickerField";
    static props = {
        ...standardFieldProps,
    };

    setup() {
        this.state = useState({ isOpen: false });
    }

    get value() {
        return this.props.record.data[this.props.name] || "fa fa-folder-open";
    }

    get options() {
        return this.props.record.fields.icon_preset?.selection || [];
    }

    togglePicker() {
        if (this.props.readonly) {
            return;
        }
        this.state.isOpen = !this.state.isOpen;
    }

    async selectIcon(value) {
        const changes = { [this.props.name]: value };
        if (this.props.record.fields.icon_preset) {
            changes.icon_preset = value;
        }
        await this.props.record.update(changes);
        this.state.isOpen = false;
    }
}

export const knowledgeIconPickerField = {
    component: KnowledgeIconPickerField,
    displayName: "Knowledge Icon Picker",
    supportedTypes: ["char"],
};

registry.category("fields").add("wex_kb_icon_picker", knowledgeIconPickerField);
