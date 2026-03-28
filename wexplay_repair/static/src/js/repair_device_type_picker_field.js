/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Component, useState } from "@odoo/owl";

const DEVICE_TYPE_ICONS = {
    all_in_one: "fa fa-desktop",
    console: "fa fa-gamepad",
    desktop: "fa fa-desktop",
    gpu: "fa fa-microchip",
    imac: "fa fa-apple",
    laptop: "fa fa-laptop",
    mini_pc: "fa fa-hdd-o",
    mobile: "fa fa-mobile",
    monitor: "fa fa-television",
    motherboard: "fa fa-th-large",
    other: "fa fa-ellipsis-h",
    pos: "fa fa-shopping-cart",
    smartwatch: "fa fa-clock-o",
    tablet: "fa fa-tablet",
};

class RepairDeviceTypePickerField extends Component {
    static template = "wexplay_repair.RepairDeviceTypePickerField";
    static props = {
        ...standardFieldProps,
    };

    setup() {
        this.state = useState({ isOpen: false });
    }

    get value() {
        return this.props.record.data[this.props.name] || false;
    }

    get options() {
        return this.props.record.fields[this.props.name]?.selection || [];
    }

    get currentOption() {
        return this.options.find((option) => option[0] === this.value) || false;
    }

    get currentLabel() {
        return this.currentOption ? this.currentOption[1] : "Selecciona el tipo";
    }

    get currentIcon() {
        return DEVICE_TYPE_ICONS[this.value] || "fa fa-hdd-o";
    }

    iconFor(value) {
        return DEVICE_TYPE_ICONS[value] || "fa fa-hdd-o";
    }

    togglePicker() {
        if (this.props.readonly) {
            return;
        }
        this.state.isOpen = !this.state.isOpen;
    }

    async selectValue(value) {
        await this.props.record.update({ [this.props.name]: value });
        this.state.isOpen = false;
    }
}

export const repairDeviceTypePickerField = {
    component: RepairDeviceTypePickerField,
    displayName: "Repair Device Type Picker",
    supportedTypes: ["selection"],
};

registry.category("fields").add("wex_repair_device_type_picker", repairDeviceTypePickerField);
