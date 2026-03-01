/** @odoo-module **/
console.log("🔥🔥🔥 QZ_PRINT VERSION 31 (CONFIG BY KIND) 🔥🔥🔥");

import { browser } from "@web/core/browser/browser";

const QZ_JS_URL = "https://qz.io/api/qz-tray.js";

const WEX_QZ_DEBUG_FORCE_LOG = true;
const WEX_QZ_DEBUG_TAG = "[WEX_QZ_BYKIND]";

let _securityConfigured = false;

/* =========================================================
 * QZ BOOTSTRAP
 * ========================================================= */

function loadScriptOnce(src) {
    return new Promise((resolve, reject) => {
        const existing = [...document.getElementsByTagName("script")].find((s) => s.src === src);
        if (existing) return resolve();

        const s = document.createElement("script");
        s.src = src;
        s.async = true;
        s.onload = () => resolve();
        s.onerror = () => reject(new Error(`No se pudo cargar ${src}`));
        document.head.appendChild(s);
    });
}

function configureUnsignedSecurity(qz) {
    if (_securityConfigured || !qz?.security) return;
    qz.security.setCertificatePromise(() => Promise.resolve(""));
    _securityConfigured = true;
}

export async function ensureQz() {
    if (window.qz) {
        configureUnsignedSecurity(window.qz);
        return window.qz;
    }
    await loadScriptOnce(QZ_JS_URL);
    if (!window.qz) throw new Error("QZ Tray no disponible");
    configureUnsignedSecurity(window.qz);
    return window.qz;
}

export async function connectQz() {
    const qz = await ensureQz();
    if (!qz.websocket.isActive()) {
        await qz.websocket.connect();
    }
    return true;
}

export async function isQzConnected() {
    const qz = await ensureQz();
    return !!qz.websocket.isActive();
}

export async function disconnectQz() {
    const qz = await ensureQz();
    if (qz.websocket.isActive()) {
        await qz.websocket.disconnect();
    }
}

export async function getPrinter(printerName) {
    const qz = await ensureQz();
    const printer = await qz.printers.find(printerName);
    if (!printer) throw new Error(`Impresora no encontrada: ${printerName}`);
    return printer;
}

/* =========================================================
 * CONFIG BUILDERS (POR TIPO)
 * ========================================================= */

/**
 * Etiquetas Brother QL:
 * - ancho fijo por rollo (29mm)
 * - altura variable (no se fija)
 * - copies configurable via opts
 */
export function buildQlLabelConfig(printer, opts = {}) {
    const copies = Number.isInteger(opts.copies) && opts.copies > 0 ? opts.copies : 1;

    return window.qz.configs.create(printer, {
        units: "mm",
        size: { width: 29 },
        margins: { top: 0, right: 0, bottom: 0, left: 0 },
        orientation: "landscape",
        scaleContent: false,
        colorType: "blackwhite",
        density: 8,
        interpolation: "nearest",
        rasterize: false,
        forceDetailed: true,
        copies,
    });
}

export function buildThermalConfig(printer) {
    return window.qz.configs.create(printer, {
        units: "mm",
        margins: { top: 0, right: 3, bottom: 0, left: 0 },
        scaleContent: false,
        colorType: "grayscale",
        rasterize: false,
       // rasterize: true,
        interpolation: "nearest",
        forceDetailed: true,
        copies: 1,
    });
}

export function buildA4Config(printer) {
    return window.qz.configs.create(printer, {
        units: "mm",
        size: { width: 210, height: 297 },
        orientation: "portrait",
        scaleContent: true,
        colorType: "color",
        rasterize: false,
        copies: 1,
    });
}

function getConfigBuilderByKind(kind) {
    switch (kind) {
        case "label":
            return buildQlLabelConfig;
        case "thermal":
            return buildThermalConfig;
        case "a4":
            return buildA4Config;
        default:
            return buildQlLabelConfig;
    }
}

/* =========================================================
 * CORE PRINT HELPER (ÚNICO)
 * ========================================================= */

function arrayBufferToBase64(buffer) {
    return new Promise((resolve, reject) => {
        try {
            const blob = new Blob([buffer], { type: "application/pdf" });
            const reader = new FileReader();

            reader.onloadend = function () {
                const result = reader.result || "";
                const base64 = result.split(",")[1] || "";
                resolve(base64);
            };

            reader.onerror = function () {
                reject(reader.error || new Error("FileReader error"));
            };

            reader.readAsDataURL(blob);
        } catch (e) {
            reject(e);
        }
    });
}

async function _printOdooPdfUrlWithConfig(reportUrl, printerName, buildConfigFn) {
    await connectQz();
    const qz = await ensureQz();

    let printer;
    try {
        printer = await getPrinter(printerName);
    } catch {
        printer = await qz.printers.getDefault();
    }

    const config = buildConfigFn(printer);

    const absUrl = new URL(reportUrl, browser.location.origin).toString();

    console.time("[QZ] fetch pdf");
    const resp = await fetch(absUrl, { credentials: "include", cache: "no-store" });
    console.timeEnd("[QZ] fetch pdf");

    if (!resp.ok) throw new Error(`No se pudo descargar PDF (${resp.status})`);

    const contentType = resp.headers.get("content-type") || "";
    if (!contentType.includes("application/pdf")) {
        throw new Error("La respuesta no es un PDF");
    }

    console.time("[QZ] to base64");
    const buffer = await resp.arrayBuffer();
    const pdfBase64 = await arrayBufferToBase64(buffer);
    console.timeEnd("[QZ] to base64");

    console.time("[QZ] qz.print");
    await qz.print(config, [
        {
            type: "pixel",
            format: "pdf",
            flavor: "base64",
            data: pdfBase64,
        },
    ]);
    console.timeEnd("[QZ] qz.print");

    return true;
}

/* =========================================================
 * API LEGACY (LABEL SIEMPRE)
 * ========================================================= */

export async function printOdooPdfUrl(reportUrl, printerName = "Brother QL-710W") {
    // Legacy: etiqueta con 1 copia
    return _printOdooPdfUrlWithConfig(reportUrl, printerName, (printer) => buildQlLabelConfig(printer, { copies: 1 }));
}

/* =========================================================
 * RESOLUCIÓN POR TIPO + API MODERNA
 * ========================================================= */

export async function resolvePrinterName(kind, env) {
    const orm = env?.services?.orm;
    const get = (k, d = "") => orm?.call("ir.config_parameter", "get_param", [k, d]);

    const printerName = await get(`wexplay_sat_print.wex_qz_${kind}_printer`, "");
    const allowFallback = (await get("wexplay_sat_print.wex_qz_allow_fallback", "true")) !== "false";
    const debug = (await get("wexplay_sat_print.wex_qz_debug", "false")) === "true";

    return { printerName, allowFallback, debug };
}

export async function printOdooPdfUrlByKind(kind, reportUrl, env, opts = {}) {
    const info = await resolvePrinterName(kind, env);

    const copies = kind === "label" && Number.isInteger(opts.copies) && opts.copies > 0 ? opts.copies : 1;

    const baseBuilder = getConfigBuilderByKind(kind);

    // wrapper para pasar copies solo a label
    const buildConfigFn =
        kind === "label" ? (printer) => baseBuilder(printer, { copies }) : (printer) => baseBuilder(printer);

    if (info.debug || WEX_QZ_DEBUG_FORCE_LOG) {
        console.log(WEX_QZ_DEBUG_TAG, { kind, reportUrl, copies, ...info });
    }

    if (info.printerName) {
        return _printOdooPdfUrlWithConfig(reportUrl, info.printerName, buildConfigFn);
    }

    if (!info.allowFallback) {
        throw new Error(`No hay impresora configurada para ${kind}`);
    }

    // Asegurar conexión antes de consultar defaultPrinter
    await connectQz();
    const qz = await ensureQz();
    const defaultPrinter = await qz.printers.getDefault();

    return _printOdooPdfUrlWithConfig(reportUrl, defaultPrinter, buildConfigFn);
}

/* =========================================================
 * DEBUG
 * ========================================================= */

if (browser.location.search.includes("debug")) {
    window.WEXPLAY_QZ = {
        printOdooPdfUrl,
        printOdooPdfUrlByKind,
        resolvePrinterName,
    };
}
