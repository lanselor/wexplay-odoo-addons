/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { confirmDeviceInspectionReset } from "./device_inspection_confirmation";

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

export class DeviceTypePicker extends Component {
    static template = "wexplay_repair.DeviceTypePicker";
    static props = {
        value: String,
        options: Array,
        onSelect: Function,
        readonly: { type: Boolean, optional: true },
        required: { type: Boolean, optional: true },
    };

    setup() {
        this.state = useState({ isOpen: false });
    }

    get value() {
        return this.props.value;
    }

    get options() {
        return this.props.options;
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
        this.state.isOpen = false;
        if (this.props.readonly || value === this.value) {
            return;
        }
        await this.props.onSelect(value);
    }
}

class RepairDeviceTypePickerField extends Component {
    static template = "wexplay_repair.RepairDeviceTypePickerField";
    static components = { DeviceTypePicker };
    static props = { ...standardFieldProps };

    setup() {
        this.state = useState({ changing: false });
        this.dialog = useService("dialog");
    }

    get value() {
        return this.props.record.data[this.props.name] || "";
    }

    get options() {
        return this.props.record.fields[this.props.name]?.selection || [];
    }

    async selectValue(value) {
        if (this.props.readonly || this.state.changing || value === this.value) {
            return;
        }
        this.state.changing = true;
        try {
            const data = this.props.record.data;
            const marks = data.x_device_inspection_marks;
            const hasEvidence = marks?.front?.length || marks?.back?.length
                || data.x_device_condition_ids?.currentIds.length;
            if (hasEvidence && !await confirmDeviceInspectionReset(this.dialog)) {
                return;
            }
            await this.props.record.update({
                [this.props.name]: value,
                x_device_inspection_marks: false,
                x_device_condition_ids: [[6, 0, []]],
            });
        } finally {
            this.state.changing = false;
        }
    }
}

export const repairDeviceTypePickerField = {
    component: RepairDeviceTypePickerField,
    displayName: "Repair Device Type Picker",
    supportedTypes: ["selection"],
};

registry.category("fields").add("wex_repair_device_type_picker", repairDeviceTypePickerField);
