/** @odoo-module **/

import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

const PRESET_PREVIEWS = {
    custom: {
        className: "o_apps_menu_background_preview_custom",
        label: _t("Uploaded Image"),
    },
    wexplay_circuit: {
        image: "/web_responsive_app_customizer/static/src/img/backgrounds/wexplay-circuit.png",
    },
    wexplay_flow: {
        image: "/web_responsive_app_customizer/static/src/img/backgrounds/wexplay-flow.png",
    },
    wexplay_architecture: {
        image: "/web_responsive_app_customizer/static/src/img/backgrounds/wexplay-architecture.png",
    },
};

export class AppsMenuBackgroundPresetField extends Component {
    static template = "web_responsive_app_customizer.AppsMenuBackgroundPresetField";
    static props = {
        ...standardFieldProps,
    };

    get value() {
        return this.props.record.data[this.props.name];
    }

    get options() {
        const selection = this.props.record.fields[this.props.name].selection || [];
        return selection
            .filter(([value]) => value)
            .map(([value, label]) => ({
                value,
                label: PRESET_PREVIEWS[value]?.label || label,
                image: PRESET_PREVIEWS[value]?.image,
                className: PRESET_PREVIEWS[value]?.className || "",
            }));
    }

    selectPreset(value) {
        if (!this.props.readonly && value !== this.value) {
            this.props.record.update({ [this.props.name]: value });
        }
    }
}

export const appsMenuBackgroundPresetField = {
    component: AppsMenuBackgroundPresetField,
    displayName: _t("Apps Menu Background Preset"),
    supportedTypes: ["selection"],
};

registry.category("fields").add("apps_menu_background_preset", appsMenuBackgroundPresetField);
