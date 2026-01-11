/** @odoo-module **/

// wexplay_sat_print/static/src/js/qz_settings_widget.js
import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { testQzConnection, getAllPrinters } from "@wexplay_product_print/js/qz_print";
/**
 * AJUSTA ESTA RUTA al path real de tu core:
 * - Si qz_print.js está en este mismo módulo: "wexplay_sat_print/static/src/js/qz_print"
 * - Si está en otro módulo: "wexplay_product_print/static/src/js/qz_print"
 */


class WexQzSettingsWidget extends Component {
    static template = "wexplay_sat_print.WexQzSettingsWidget";

    setup() {
        this.state = useState({
            status: "idle", // idle | ok | error | loading
            message: "",
            printers: [],
        });
    }

    async onTestConnection() {
        this.state.status = "loading";
        this.state.message = "Probando conexión con QZ Tray...";
        this.state.printers = [];

        const result = await testQzConnection();
        if (result.ok) {
            this.state.status = "ok";
            this.state.message = result.message;
            await this._writeLastTestSnapshot(true);
        } else {
            this.state.status = "error";
            this.state.message = `Error QZ: ${result.message}`;
            await this._writeLastTestSnapshot(false);
        }
    }

    async onLoadPrinters() {
        this.state.status = "loading";
        this.state.message = "Cargando impresoras detectadas...";

        try {
            const printers = await getAllPrinters();
            this.state.printers = printers;
            this.state.status = "ok";
            this.state.message = `Impresoras detectadas: ${printers.length}`;
        } catch (e) {
            this.state.status = "error";
            this.state.message = `No se pudieron cargar impresoras: ${e?.message || e}`;
        }
    }

    setPrinter(fieldName, ev) {
        const value = ev.target.value || "";
        this.props.record.update({ [fieldName]: value });
    }

    async _writeLastTestSnapshot(ok) {
        // Persistir snapshot en res.company (campos: wex_qz_last_test_ok, wex_qz_last_test_at, wex_qz_last_test_user_id)
        // Nota: este write es opcional; si falla no debe romper la UI.
        try {
            const companyId = this.props.record.data.company_id?.[0];
            if (!companyId) return;

            const orm = this.env.services.orm;
            await orm.write("res.company", [companyId], {
                wex_qz_last_test_ok: ok,
                // Mejor guardar server-side (fase 2) con método Python; por ahora ISO es suficiente.
                wex_qz_last_test_at: new Date().toISOString(),
                wex_qz_last_test_user_id: this.env.services.user.userId,
            });
        } catch (e) {
            // silencioso
        }
    }
}

registry.category("fields").add("wex_qz_settings_widget", {
    component: WexQzSettingsWidget,
});
