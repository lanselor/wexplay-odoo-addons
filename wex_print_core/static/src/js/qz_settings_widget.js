/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { getAllPrinters, testQzConnection } from "@wex_print_core/js/qz_print";


class WexQzSettingsWidget extends Component {
    static template = "wex_print_core.WexQzSettingsWidget";

    setup() {
        this.state = useState({
            status: "idle",
            message: "",
            printers: [],
        });

        this.onChangeLabel = (ev) => this.setPrinter("wex_qz_label_printer", ev);
        this.onChangeThermal = (ev) => this.setPrinter("wex_qz_thermal_printer", ev);
        this.onChangeA4 = (ev) => this.setPrinter("wex_qz_a4_printer", ev);
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
        } catch (error) {
            this.state.status = "error";
            this.state.message = `No se pudieron cargar impresoras: ${error?.message || error}`;
        }
    }

    setPrinter(fieldName, ev) {
        const value = ev.target.value || "";
        this.props.record.update({ [fieldName]: value });
    }

    async _writeLastTestSnapshot(ok) {
        // Persistimos el snapshot en compañía sin cambiar el flujo actual.
        try {
            const companyId = this.props.record.data.company_id?.[0];
            if (!companyId) {
                return;
            }

            await this.env.services.orm.write("res.company", [companyId], {
                wex_qz_last_test_ok: ok,
                wex_qz_last_test_at: new Date().toISOString(),
                wex_qz_last_test_user_id: this.env.services.user.userId,
            });
        } catch {
            // Silencioso: no bloqueamos la UI de Ajustes.
        }
    }
}

registry.category("fields").add("wex_qz_settings_widget", {
    component: WexQzSettingsWidget,
});
