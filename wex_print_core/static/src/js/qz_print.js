/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { resolvePrintRoute, tracePrintDecision } from "@wex_print_core/js/print_router";

// El asset backend ya carga la librería local; mantenemos la URL oficial como fallback.
const QZ_JS_URL = "https://qz.io/api/qz-tray.js";
const WEX_QZ_DEBUG_FORCE_LOG = true;
const WEX_QZ_DEBUG_TAG = "[WEX_QZ_BYKIND]";

let _securityConfigured = false;

function loadScriptOnce(src) {
    return new Promise((resolve, reject) => {
        const existing = [...document.getElementsByTagName("script")].find((script) => script.src === src);
        if (existing) {
            return resolve();
        }

        const script = document.createElement("script");
        script.src = src;
        script.async = true;
        script.onload = () => resolve();
        script.onerror = () => reject(new Error(`No se pudo cargar ${src}`));
        document.head.appendChild(script);
    });
}

function configureUnsignedSecurity(qz) {
    if (_securityConfigured || !qz?.security) {
        return;
    }
    qz.security.setCertificatePromise(() => Promise.resolve(""));
    _securityConfigured = true;
}

export async function ensureQz() {
    if (window.qz) {
        configureUnsignedSecurity(window.qz);
        return window.qz;
    }
    await loadScriptOnce(QZ_JS_URL);
    if (!window.qz) {
        throw new Error("QZ Tray no disponible");
    }
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
    if (!printer) {
        throw new Error(`Impresora no encontrada: ${printerName}`);
    }
    return printer;
}

export async function getAllPrinters() {
    await connectQz();
    const qz = await ensureQz();
    return qz.printers.find();
}

export async function getPrinterDetailsSnapshot() {
    await connectQz();
    const qz = await ensureQz();
    const details = await qz.printers.details();
    if (Array.isArray(details)) {
        return details;
    }
    return details ? [details] : [];
}

export async function testQzConnection() {
    try {
        await connectQz();
        const qz = await ensureQz();
        const version = await qz.api.getVersion();
        return {
            ok: true,
            message: `Conexión OK (${version})`,
        };
    } catch (error) {
        return {
            ok: false,
            message: error?.message || String(error),
        };
    }
}

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
        interpolation: "nearest",
        forceDetailed: true,
        copies: 1,
    });
}

export function buildA4Config(printer, opts = {}) {
    const configOptions = {
        units: "mm",
        size: { width: 210, height: 297 },
        orientation: "portrait",
        scaleContent: true,
        colorType: "color",
        rasterize: true,
        copies: 1,
    };

    if (opts.duplexMode && opts.duplexMode !== "default") {
        configOptions.duplex = opts.duplexMode;
    }

    return window.qz.configs.create(printer, configOptions);
}

function getConfigBuilderByKind(kind, opts = {}) {
    switch (kind) {
        case "label":
            return buildQlLabelConfig;
        case "thermal":
            return buildThermalConfig;
        case "a4":
            return (printer) => buildA4Config(printer, opts);
        default:
            return buildQlLabelConfig;
    }
}

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
        } catch (error) {
            reject(error);
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

    const resp = await fetch(absUrl, { credentials: "include", cache: "no-store" });
    if (!resp.ok) {
        throw new Error(`No se pudo descargar PDF (${resp.status})`);
    }

    const contentType = resp.headers.get("content-type") || "";
    if (!contentType.includes("application/pdf")) {
        throw new Error("La respuesta no es un PDF");
    }

    const buffer = await resp.arrayBuffer();
    const pdfBase64 = await arrayBufferToBase64(buffer);

    await qz.print(config, [
        {
            type: "pixel",
            format: "pdf",
            flavor: "base64",
            data: pdfBase64,
        },
    ]);

    return true;
}

export async function printOdooPdfUrl(reportUrl, printerName = "Brother QL-710W") {
    return _printOdooPdfUrlWithConfig(reportUrl, printerName, (printer) =>
        buildQlLabelConfig(printer, { copies: 1 })
    );
}

export async function resolvePrinterName(kind, env) {
    const orm = env?.services?.orm;
    const get = (key, defaultValue = "") => orm?.call("ir.config_parameter", "get_param", [key, defaultValue]);

    const printerName = await get(`wexplay_sat_print.wex_qz_${kind}_printer`, "");
    const allowFallback = (await get("wexplay_sat_print.wex_qz_allow_fallback", "true")) !== "false";
    const debug = (await get("wexplay_sat_print.wex_qz_debug", "false")) === "true";

    return { printerName, allowFallback, debug };
}

async function _tracePrint(env, payload) {
    await tracePrintDecision(env, {
        name: payload.documentCode || payload.reportName || "Print Trace",
        document_type_id: payload.documentTypeId || false,
        document_code: payload.documentCode || false,
        report_name: payload.reportName || false,
        report_url: payload.reportUrl || false,
        requested_mode: payload.requestedMode || "legacy",
        execution_mode: payload.executionMode || payload.requestedMode || "legacy",
        resolution_source: payload.resolutionSource || "legacy",
        legacy_kind: payload.kind || false,
        printer_name: payload.printerName || false,
        allow_fallback: !!payload.allowFallback,
        copies: payload.copies || 1,
        next_resolution_found: !!payload.nextResolutionFound,
        next_profile_id: payload.nextProfileId || false,
        next_printer_name: payload.nextPrinterName || false,
        next_allow_fallback: !!payload.nextAllowFallback,
        next_duplex_mode: payload.nextDuplexMode || false,
        pilot_use_new_resolution: !!payload.pilotUseNewResolution,
        shadow_matches_legacy: !!payload.shadowMatchesLegacy,
        next_message: payload.nextMessage || false,
        success: !!payload.success,
        message: payload.message || false,
    });
}

export async function printOdooPdfUrlByKind(kind, reportUrl, env, opts = {}) {
    const info = await resolvePrinterName(kind, env);
    const copies = kind === "label" && Number.isInteger(opts.copies) && opts.copies > 0 ? opts.copies : 1;
    const baseBuilder = getConfigBuilderByKind(kind, opts);
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

    await connectQz();
    const qz = await ensureQz();
    const defaultPrinter = await qz.printers.getDefault();

    return _printOdooPdfUrlWithConfig(reportUrl, defaultPrinter, buildConfigFn);
}

export async function printOdooDocument(documentCode, reportUrl, env, opts = {}) {
    const route = await resolvePrintRoute(documentCode, env, opts);
    const info = await resolvePrinterName(route.kind, env);
    const copies = route.kind === "label" && Number.isInteger(opts.copies) && opts.copies > 0 ? opts.copies : 1;
    const nextResolution = route.nextResolution || {};
    const effectiveOpts = { ...opts };
    const useNewResolution = route.resolutionSource === "new" && nextResolution.found;

    if (useNewResolution) {
        effectiveOpts.printerName = nextResolution.printer_name || "";
        effectiveOpts.allowFallback = nextResolution.allow_fallback;
        effectiveOpts.duplexMode = nextResolution.duplex_mode || "default";
    }
    const shadowMatchesLegacy =
        !!nextResolution.found &&
        nextResolution.legacy_kind === route.kind &&
        (!nextResolution.printer_name || nextResolution.printer_name === info.printerName);

    try {
        if (useNewResolution) {
            const buildConfigFn = (printer) => {
                if (route.kind === "label") {
                    return buildQlLabelConfig(printer, { copies });
                }
                if (route.kind === "thermal") {
                    return buildThermalConfig(printer);
                }
                return buildA4Config(printer, { duplexMode: effectiveOpts.duplexMode });
            };

            await _printOdooPdfUrlWithConfig(
                reportUrl,
                nextResolution.printer_name || info.printerName,
                buildConfigFn
            );
        } else {
            await printOdooPdfUrlByKind(route.kind, reportUrl, env, opts);
        }
        await _tracePrint(env, {
            documentTypeId: route.documentType?.id,
            documentCode: route.documentCode,
            reportName: route.reportName,
            reportUrl,
            requestedMode: route.requestedMode,
            executionMode: route.executionMode,
            resolutionSource: route.resolutionSource,
            kind: route.kind,
            printerName: info.printerName || false,
            allowFallback: info.allowFallback,
            copies,
            nextResolutionFound: nextResolution.found,
            nextProfileId: nextResolution.profile_id,
            nextPrinterName: nextResolution.printer_name,
            nextAllowFallback: nextResolution.allow_fallback,
            nextDuplexMode: nextResolution.duplex_mode,
            pilotUseNewResolution: nextResolution.pilot_use_new_resolution,
            shadowMatchesLegacy,
            nextMessage: nextResolution.message,
            success: true,
            message: "Printed using legacy-compatible routing.",
        });
        return true;
    } catch (error) {
        if (useNewResolution && route.requestedMode === "hybrid") {
            try {
                await printOdooPdfUrlByKind(route.kind, reportUrl, env, opts);
                await _tracePrint(env, {
                    documentTypeId: route.documentType?.id,
                    documentCode: route.documentCode,
                    reportName: route.reportName,
                    reportUrl,
                    requestedMode: route.requestedMode,
                    executionMode: "legacy",
                    resolutionSource: "fallback_legacy",
                    kind: route.kind,
                    printerName: info.printerName || false,
                    allowFallback: info.allowFallback,
                    copies,
                    nextResolutionFound: nextResolution.found,
                    nextProfileId: nextResolution.profile_id,
                    nextPrinterName: nextResolution.printer_name,
                    nextAllowFallback: nextResolution.allow_fallback,
                    nextDuplexMode: nextResolution.duplex_mode,
                    pilotUseNewResolution: nextResolution.pilot_use_new_resolution,
                    shadowMatchesLegacy,
                    nextMessage: `New path failed and fell back to legacy: ${error?.message || error}`,
                    success: true,
                    message: "Printed using legacy fallback after new path failure.",
                });
                return true;
            } catch {
                // Si también falla legacy, seguimos con la traza de error final.
            }
        }

        await _tracePrint(env, {
            documentTypeId: route.documentType?.id,
            documentCode: route.documentCode,
            reportName: route.reportName,
            reportUrl,
            requestedMode: route.requestedMode,
            executionMode: route.executionMode,
            resolutionSource: route.resolutionSource,
            kind: route.kind,
            printerName: info.printerName || false,
            allowFallback: info.allowFallback,
            copies,
            nextResolutionFound: nextResolution.found,
            nextProfileId: nextResolution.profile_id,
            nextPrinterName: nextResolution.printer_name,
            nextAllowFallback: nextResolution.allow_fallback,
            nextDuplexMode: nextResolution.duplex_mode,
            pilotUseNewResolution: nextResolution.pilot_use_new_resolution,
            shadowMatchesLegacy,
            nextMessage: nextResolution.message,
            success: false,
            message: error?.message || String(error),
        });
        throw error;
    }
}

if (browser.location.search.includes("debug")) {
    window.WEXPLAY_QZ = {
        printOdooDocument,
        printOdooPdfUrl,
        printOdooPdfUrlByKind,
        resolvePrinterName,
        getAllPrinters,
        getPrinterDetailsSnapshot,
        testQzConnection,
    };
}
