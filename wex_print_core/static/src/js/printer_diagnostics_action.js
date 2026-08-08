/** @odoo-module **/

import { registry } from "@web/core/registry";
import { getPrinterDetailsSnapshot } from "@wex_print_core/js/qz_print";

registry.category("actions").add("wex_print_core.load_printer_diagnostics", async (env) => {
    const notification = env.services.notification;
    const orm = env.services.orm;

    try {
        const details = await getPrinterDetailsSnapshot();
        if (!details.length) {
            notification.add("No se detectaron impresoras desde QZ Tray.", { type: "warning" });
            return;
        }

        const companyId = env.services.company?.currentCompany?.id || false;
        const payload = details.map((printer) => ({
            name: printer.name || "Unnamed printer",
            printer_name: printer.name || "",
            driver: printer.driver || "",
            density: Array.isArray(printer.density)
                ? printer.density.join(", ")
                : printer.density || "",
            trays_text: Array.isArray(printer.trays) ? printer.trays.join(", ") : printer.trays || "",
            is_default: !!printer.default,
            is_physical: printer.physical !== false,
            printer_type: printer.type || "",
            raw_details_json: JSON.stringify(printer, null, 2),
            company_id: companyId,
        }));

        await orm.create("wex.print.device.snapshot", payload);
        notification.add(`Se encontraron ${payload.length} impresoras desde QZ Tray.`, { type: "success" });
        env.services.action.doAction("wex_print_core.action_wex_print_device_snapshots");
    } catch (error) {
        notification.add(`No se pudieron buscar impresoras: ${error?.message || error}`, {
            type: "danger",
        });
    }
});
