/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { TextField } from "@web/views/fields/text/text_field";
import { confirmConsoleInspectionReset, confirmDeviceInspectionReset } from "./device_inspection_confirmation";
import { DeviceTypePicker } from "./repair_device_type_picker_field";

export class DeviceInspectionDialog extends Component {
    static template = "wexplay_repair.DeviceInspectionDialog";
    static components = { Dialog, DeviceTypePicker };
    static props = { record: Object, close: Function };

    setup() {
        this.orm = useService("orm");
        this.dialog = useService("dialog");
        const data = this.props.record.data;
        const marks = data.x_device_inspection_marks;
        this.marksDeviceType = marks?.device_type || "";
        this.state = useState({
            deviceType: data.x_device_type || "",
            consoleFormat: marks?.console_format || "",
            description: data.x_device_description || "",
            conditionIds: [...data.x_device_condition_ids.currentIds],
            front: marks ? JSON.parse(JSON.stringify(marks.front)) : [],
            back: marks ? JSON.parse(JSON.stringify(marks.back)) : [],
            conditions: [],
            diagrams: {},
            error: "",
            applying: false,
            changingType: false,
            activeView: "front",
        });
        this.pointer = null;
        onWillStart(async () => {
            const [conditions, diagrams] = await Promise.all([
                this.orm.searchRead(
                    "wex.repair.device.condition",
                    ["|", ["active", "=", true], ["id", "in", this.state.conditionIds]],
                    ["name", "device_type"],
                    { order: "sequence, name, id", context: { active_test: false } }
                ),
                this.orm.call("repair.order", "get_device_inspection_diagrams", []),
            ]);
            this.state.conditions = conditions;
            this.state.diagrams = diagrams;
        });
    }

    get deviceTypes() {
        return this.props.record.fields.x_device_type.selection;
    }

    get hasDiagram() {
        return !this.hasIncompatibleMarks && Boolean(this.state.diagrams[this.state.deviceType])
            && (this.state.deviceType !== "console" || Boolean(this.selectedConsoleFormat));
    }

    get consoleFormats() {
        return this.state.diagrams.console?.formats || [];
    }

    get selectedConsoleFormat() {
        return this.consoleFormats.find((format) => format.value === this.state.consoleFormat);
    }

    get canApply() {
        return Boolean(this.state.deviceType) && !this.hasIncompatibleMarks
            && !this.state.applying && !this.state.changingType
            && (this.state.deviceType !== "console" || Boolean(this.selectedConsoleFormat));
    }

    get hasMarks() {
        return Boolean(this.state.front.length || this.state.back.length);
    }

    get hasActiveMarks() {
        return Boolean(this.state[this.state.activeView].length);
    }

    get hasIncompatibleMarks() {
        return this.hasMarks && this.marksDeviceType !== this.state.deviceType;
    }

    get availableConditions() {
        return this.state.conditions.filter((condition) =>
            !condition.device_type || condition.device_type === this.state.deviceType
        );
    }

    get selectedConditions() {
        return this.state.conditions.filter((condition) => this.state.conditionIds.includes(condition.id));
    }

    async changeDeviceType(nextType) {
        if (nextType === this.state.deviceType || this.state.changingType || this.state.applying) {
            return;
        }
        this.state.changingType = true;
        try {
            if ((this.hasMarks || this.state.conditionIds.length)
                && !await confirmDeviceInspectionReset(this.dialog)) {
                return;
            }
            this.state.front = [];
            this.state.back = [];
            this.state.conditionIds = [];
            this.state.consoleFormat = "";
            this.pointer = null;
            this.marksDeviceType = nextType;
            this.state.deviceType = nextType;
            this.state.activeView = "front";
            this.state.error = "";
        } finally {
            this.state.changingType = false;
        }
    }

    async changeConsoleFormat(value) {
        if (value === this.state.consoleFormat || this.state.changingType || this.state.applying) {
            return;
        }
        this.state.changingType = true;
        try {
            if (this.hasMarks && !await confirmConsoleInspectionReset(this.dialog)) {
                return;
            }
            this.state.front = [];
            this.state.back = [];
            this.pointer = null;
            this.state.consoleFormat = value;
            this.state.activeView = "front";
            this.state.error = "";
        } finally {
            this.state.changingType = false;
        }
    }

    selectView(view) {
        if (!this.pointer && !this.state.applying) {
            this.state.activeView = view;
        }
    }

    toggleCondition(id) {
        const ids = this.state.conditionIds;
        this.state.conditionIds = ids.includes(id) ? ids.filter((value) => value !== id) : [...ids, id];
    }

    imageUrl(view) {
        const prefix = this.state.deviceType === "console"
            ? this.selectedConsoleFormat?.image_prefix : this.state.deviceType;
        return `/wexplay_repair/static/src/img/device_inspection/${prefix}_${view}.svg`;
    }

    consolePreviewUrl(format) {
        return `/wexplay_repair/static/src/img/device_inspection/${format.image_prefix}_front.svg`;
    }

    viewLabel(view) {
        return this.state.diagrams[this.state.deviceType]?.[view]
            || (view === "front" ? _t("Frontal") : _t("Trasera"));
    }

    pathFor(stroke) {
        const points = stroke.map(([x, y]) => `${x * 320},${y * 400}`);
        // Un clic aislado también debe dejar una marca visible.
        return `M ${points.join(" L ")}${points.length === 1 ? " l 0.1,0" : ""}`;
    }

    pointFor(event) {
        const bounds = event.currentTarget.getBoundingClientRect();
        return [
            Math.max(0, Math.min(1, (event.clientX - bounds.left) / bounds.width)),
            Math.max(0, Math.min(1, (event.clientY - bounds.top) / bounds.height)),
        ];
    }

    startStroke(event, view) {
        if (event.button !== 0 || this.pointer || this.state.applying) {
            return;
        }
        event.preventDefault();
        const pointCount = this.state[view].reduce((count, stroke) => count + stroke.length, 0);
        if (this.state[view].length >= 500 || pointCount >= 20000) {
            this.state.error = _t("Se ha alcanzado el límite de dibujo. Deshaz o borra algunas marcas.");
            return;
        }
        event.currentTarget.setPointerCapture(event.pointerId);
        this.marksDeviceType = this.state.deviceType;
        this.pointer = { id: event.pointerId, view };
        this.state[view].push([this.pointFor(event)]);
    }

    moveStroke(event) {
        if (this.pointer?.id !== event.pointerId) {
            return;
        }
        const strokes = this.state[this.pointer.view];
        const stroke = strokes[strokes.length - 1];
        const point = this.pointFor(event);
        const previous = stroke[stroke.length - 1];
        const pointCount = strokes.reduce((count, item) => count + item.length, 0);
        if (stroke.length >= 4000 || pointCount >= 20000) {
            this.state.error = _t("Se ha alcanzado el límite de puntos. Deshaz o simplifica las marcas.");
            this.endStroke(event);
            return;
        }
        if (Math.hypot(point[0] - previous[0], point[1] - previous[1]) > 0.002) {
            stroke.push(point);
        }
    }

    endStroke(event) {
        if (this.pointer?.id === event.pointerId) {
            this.pointer = null;
        }
    }

    undo() {
        if (this.pointer) {
            return;
        }
        this.state[this.state.activeView].pop();
    }

    clearMarks() {
        this.pointer = null;
        this.state[this.state.activeView] = [];
        this.state.error = "";
    }

    prepareInspectionMarks() {
        if (!this.hasMarks && this.state.deviceType !== "console") {
            return false;
        }
        const marks = {
            device_type: this.state.deviceType,
            front: JSON.parse(JSON.stringify(this.state.front)),
            back: JSON.parse(JSON.stringify(this.state.back)),
        };
        if (this.state.deviceType === "console") {
            marks.console_format = this.state.consoleFormat;
        }
        return marks;
    }

    async apply() {
        if (!this.canApply) {
            return;
        }
        this.state.applying = true;
        try {
            await this.props.record.update({
                x_device_type: this.state.deviceType,
                x_device_description: this.state.description || false,
                x_device_condition_ids: [[6, 0, [...this.state.conditionIds]]],
                x_device_inspection_marks: this.prepareInspectionMarks(),
            });
            this.props.close();
        } finally {
            this.state.applying = false;
        }
    }
}

export class RepairDeviceInspectionField extends Component {
    static template = "wexplay_repair.RepairDeviceInspectionField";
    static components = { TextField };
    static props = { ...standardFieldProps };

    setup() {
        this.dialog = useService("dialog");
    }

    get hasInspectionMarks() {
        const marks = this.props.record.data.x_device_inspection_marks;
        return Boolean(marks?.front?.length || marks?.back?.length);
    }

    async openInspection() {
        const model = this.props.record.model;
        const proms = [];
        model.bus.trigger("NEED_LOCAL_CHANGES", { proms });
        await Promise.all([...proms, model.mutex.getUnlockedDef()]);
        this.dialog.add(DeviceInspectionDialog, { record: this.props.record });
    }
}

registry.category("fields").add("wex_repair_device_inspection", {
    component: RepairDeviceInspectionField,
    supportedTypes: ["text"],
});
