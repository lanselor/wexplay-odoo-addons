// Ejecutar: node --experimental-vm-modules verify_return_view_modifiers.mjs <ruta-server-odoo>
// Usa el evaluador del cliente web instalado: Python Form no detecta todos sus errores.
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import { fileURLToPath } from "node:url";

if (!process.argv[2]) {
    throw new Error("Indica la ruta del servidor Odoo instalado.");
}
const root = path.join(process.argv[2], "odoo/addons/web/static/src/core/py_js");
const modules = new Map();
for (const name of fs.readdirSync(root).filter(name => name.endsWith(".js"))) {
    modules.set(name, new vm.SourceTextModule(fs.readFileSync(path.join(root, name), "utf8"), { identifier: name }));
}
const entry = modules.get("py.js");
await entry.link(specifier => modules.get(specifier.replace("./", "") + ".js"));
await entry.evaluate();
const evaluate = entry.namespace.evaluateBooleanExpr;
const addon = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const expressions = [];
for (const file of ["wizard/return_prepare_views.xml", "wizard/return_resolve_views.xml", "views/purchase_return_views.xml"]) {
    const xml = fs.readFileSync(path.join(addon, file), "utf8");
    for (const match of xml.matchAll(/(?:invisible|required|readonly|decoration-\w+)="([^"]+)"/g)) {
        expressions.push(match[1].replaceAll("&lt;", "<").replaceAll("&gt;", ">").replaceAll("&amp;", "&"));
    }
}
const flags = ["has_multiple_receipt_moves", "has_multiple_repair_moves", "has_origin_document", "origin_is_repair", "requires_origin_change", "blocking_reason", "can_request_replacement", "request_replacement"];
let checked = 0;
for (let mask = 0; mask < 256; mask++) {
    for (const tracking of ["none", "lot", "serial"]) {
        for (const disposition of [false, "recover", "hold", "scrap"]) {
            const context = {
                tracking, disposition, return_reason: mask % 2 ? "other" : false,
                remaining_quantity: mask % 2, prepared_quantity: mask % 2,
                state: mask % 2 ? "partial" : "resolved", return_picking_ids: [],
                picking_id: false, scrap_ids: [], wex_vendor_return_ids: [], wex_return_resolution_id: false,
            };
            flags.forEach((flag, bit) => { context[flag] = Boolean(mask & (1 << bit)); });
            for (const expression of expressions) {
                evaluate(expression, context);
                checked++;
            }
        }
    }
}
console.log(`ODOO_NATIVE_MODIFIERS_VERIFIED: ${checked} evaluations`);
