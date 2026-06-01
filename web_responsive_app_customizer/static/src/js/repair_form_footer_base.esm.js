/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { FormRenderer } from "@web/views/form/form_renderer";
import { FormCompiler } from "@web/views/form/form_compiler";
import { append, createElement, setAttributes } from "@web/core/utils/xml";
import { onMounted, onPatched } from "@odoo/owl";

const FOOTER_ZONES = ["left", "center", "right"];

function buildFooterZone(zone) {
    const zoneNode = createElement("div");
    setAttributes(zoneNode, {
        "t-att-class": `__comp__._getWexRepairFormFooterBodyClassNames('${zone}')`,
    });
    const callNode = createElement("t");
    setAttributes(callNode, {
        "t-call": `web_responsive_app_customizer.RepairFormFooter.${
            zone.charAt(0).toUpperCase() + zone.slice(1)
        }`,
    });
    append(zoneNode, callNode);
    return zoneNode;
}

patch(FormRenderer.prototype, {
    setup() {
        super.setup(...arguments);

        onMounted(() => {
            this._updateWexRepairContainerClass();
        });
        onPatched(() => {
            this._updateWexRepairContainerClass();
        });
    },

    _updateWexRepairContainerClass() {
        const sheetBg = this.el?.querySelector(".o_form_sheet_bg");
        if (sheetBg) {
            sheetBg.classList.toggle(
                "o_wex_repair_form_footer_container",
                this._isWexRepairFormFooterEnabled()
            );
        }
    },

    _isWexRepairFormFooterEnabled() {
        return !this.env.inDialog && this.props.record.resModel === "repair.order";
    },

    _getWexRepairFormFooterClassNames() {
        const classes = ["wex-repair-form-footer", "d-print-none"];
        if (this.props.record.isInEdition) {
            classes.push("is-editing");
        }
        return classes.join(" ");
    },

    _getWexRepairFormFooterBodyClassNames(zone) {
        const zoneName = FOOTER_ZONES.includes(zone) ? zone : "center";
        return `wex-repair-form-footer__zone wex-repair-form-footer__zone--${zoneName}`;
    },
});

patch(FormCompiler.prototype, {
    compile(node, params = {}) {
        const res = super.compile(node, params);
        if (params.isSubView) {
            return res;
        }
        const formSheetBg = res.querySelector(".o_form_sheet_bg");
        if (!formSheetBg || formSheetBg.querySelector(".wex-repair-form-footer")) {
            return res;
        }
        const footerNode = createElement("div");
        setAttributes(footerNode, {
            "t-if": "__comp__._isWexRepairFormFooterEnabled()",
            "t-att-class": "__comp__._getWexRepairFormFooterClassNames()",
        });
        for (const zone of FOOTER_ZONES) {
            append(footerNode, buildFooterZone(zone));
        }
        append(formSheetBg, footerNode);
        return res;
    },
});
