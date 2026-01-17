/** @odoo-module **/
console.log("🔥🔥🔥 QZ_PRINT VERSION 28 (FIX DEBUG) 🔥🔥🔥");

import { browser } from "@web/core/browser/browser";

const QZ_JS_URL = "https://qz.io/api/qz-tray.js";

// Debug: si true, siempre loguea la traza de ByKind aunque el setting debug esté apagado
const WEX_QZ_DEBUG_FORCE_LOG = true;
const WEX_QZ_DEBUG_TAG = "[WEX_QZ_BYKIND]";

// Evita reconfigurar security en cada llamada
let _securityConfigured = false;

/**
 * Carga un script externo UNA sola vez.
 */
function loadScriptOnce(src) {
    return new Promise((resolve, reject) => {
        try {
            const existing = [...document.getElementsByTagName("script")].find((s) => s.src === src);
            if (existing) return resolve();

            const s = document.createElement("script");
            s.src = src;
            s.async = true;

            s.onload = () => resolve();
            s.onerror = () => reject(new Error(`No se pudo cargar el script externo: ${src}`));

            document.head.appendChild(s);
        } catch (err) {
            reject(err);
        }
    });
}

/**
 * Configura seguridad para modo "unsigned" (sin firma).
 * Nota: sin firma NO podrás usar "Remember this decision" en QZ Tray (queda para más adelante).
 *
 * IMPORTANTE: no tocar la estrategia aquí.
 */
function configureUnsignedSecurity(qz) {
    if (_securityConfigured) return;
    if (!qz?.security) return;

    // Certificado vacío (permitido)
    qz.security.setCertificatePromise(() => Promise.resolve(""));

    // Mantener estrategia actual (no tocar): si más adelante ajustas firma, se hará con criterio.
    // qz.security.setSignaturePromise(...)  ← NO SE MODIFICA AQUÍ

    _securityConfigured = true;
}

/**
 * Asegura que QZ está disponible.
 */
export async function ensureQz() {
    try {
        if (window.qz) {
            configureUnsignedSecurity(window.qz);
            return window.qz;
        }

        await loadScriptOnce(QZ_JS_URL);

        if (!window.qz) {
            throw new Error("QZ Tray no está disponible tras cargar qz-tray.js");
        }

        configureUnsignedSecurity(window.qz);
        return window.qz;
    } catch (error) {
        console.error("[QZ] Error asegurando QZ:", error);
        throw error;
    }
}

/**
 * Devuelve true si el websocket de QZ está activo.
 */
export async function isQzConnected() {
    try {
        const qz = await ensureQz();
        return !!qz.websocket.isActive();
    } catch (error) {
        console.error("[QZ] Error comprobando conexión:", error);
        return false;
    }
}

/**
 * Conecta con QZ Tray.
 */
export async function connectQz() {
    try {
        const qz = await ensureQz();

        // Intento de forzar WS (puede no existir en algunas builds); si no, usa default.
        if (qz.websocket && typeof qz.websocket.setConnectionOptions === "function") {
            qz.websocket.setConnectionOptions({
                host: "127.0.0.1",
                usingSecure: false, // ws:// (si QZ/entorno lo permite)
                port: 8182,
            });
        } else {
            console.warn("[QZ] setConnectionOptions no disponible; usando configuración por defecto.");
        }

        if (qz.websocket.isActive()) return true;

        await qz.websocket.connect();
        return true;
    } catch (error) {
        console.error("[QZ] Error conectando con QZ Tray:", error);
        throw error;
    }
}

/**
 * Desconecta de QZ Tray (opcional).
 */
export async function disconnectQz() {
    try {
        const qz = await ensureQz();
        if (qz.websocket.isActive()) {
            await qz.websocket.disconnect();
        }
    } catch (error) {
        console.warn("[QZ] Error al desconectar:", error);
    }
}

/**
 * Busca una impresora por nombre exacto.
 * Nota: qz.printers.find(<nombre>) puede lanzar si no encuentra.
 */
export async function getPrinter(printerName) {
    try {
        const qz = await ensureQz();
        const printer = await qz.printers.find(printerName);
        if (!printer) throw new Error(`Impresora no encontrada: ${printerName}`);
        return printer;
    } catch (error) {
        console.error("[QZ] Error buscando impresora:", error);
        throw error;
    }
}

/**
 * Configuración estándar para etiquetas (Brother QL-7xx).
 */
export function buildQlLabelConfig(printer) {
    return window.qz.configs.create(printer, {
        units: "mm",
        // IMPORTANTE: Para Brother QL, 'width' es siempre el ancho físico del rollo (29)
        size: { width: 29, height: 42 },
        margins: { top: 0, right: 0, bottom: 0, left: 0 },
        scaleContent: false,
        orientation: "landscape",
        colorType: "blackwhite",
        copies: 1,
        density: 8,
        interpolation: "nearest",
        rasterize: true,
        forceDetailed: true,
    });
}

/**
 * Utilidad: ArrayBuffer -> base64
 */
function arrayBufferToBase64(buffer) {
    const bytes = new Uint8Array(buffer);
    let binary = "";
    const chunkSize = 0x8000;
    for (let i = 0; i < bytes.length; i += chunkSize) {
        binary += String.fromCharCode.apply(null, bytes.subarray(i, i + chunkSize));
    }
    return btoa(binary);
}

/**
 * Imprime una imagen base64 (PDF base64).
 * (Nombre mantenido para compatibilidad; internamente imprime PDF base64.)
 */
export async function printImageBase64(base64png, printerName = "Brother QL-710W") {
    try {
        await connectQz();
        const qz = await ensureQz();
        const printer = await getPrinter(printerName);
        const config = buildQlLabelConfig(printer);

        // Limpieza de cabecera por si viene con data URL
        const cleanBase64 = base64png.replace(/^data:application\/pdf;base64,/, "");

        const data = [
            {
                type: "pixel",
                format: "pdf",
                flavor: "base64",
                data: cleanBase64,
            },
        ];

        await qz.print(config, data);
        return true;
    } catch (error) {
        console.error("[QZ] Error en impresión:", error);
        throw error;
    }
}

export async function fetchPdfAsBase64(url) {
    const res = await fetch(url, { credentials: "include" });
    if (!res.ok) {
        throw new Error(`No se pudo descargar el PDF (${res.status})`);
    }

    const blob = await res.blob();
    const buffer = await blob.arrayBuffer();
    const bytes = new Uint8Array(buffer);

    let binary = "";
    for (let i = 0; i < bytes.length; i++) {
        binary += String.fromCharCode(bytes[i]);
    }
    return btoa(binary);
}

export async function printQzPdfFileUrl(pdfUrl, printerName = "Brother QL-710W") {
    console.log("[QZ] ENTER printQzPdfFileUrl()", { pdfUrl, printerName });

    await connectQz();
    const qz = await ensureQz();

    const printer = await getPrinter(printerName);
    const config = buildQlLabelConfig(printer);

    const data = [
        {
            type: "pixel",
            format: "pdf",
            flavor: "file",
            data: pdfUrl,
        },
    ];

    console.log("[QZ] printing PDF URL via QZ:", pdfUrl);
    await qz.print(config, data);
    return true;
}

/**
 * Imprime un PDF obtenido desde una URL de Odoo (con sesión) vía QZ.
 */
export async function printOdooPdfUrl(reportUrl, printerName = "Brother QL-710W") {
    console.log("[QZ] ENTER printOdooPdfUrl()", { reportUrl, printerName });

    try {
        await connectQz();
        console.log("[QZ] Connected:", await isQzConnected());

        const qz = await ensureQz();

        let printer;
        try {
            printer = await getPrinter(printerName);
        } catch (e) {
            console.warn("[QZ] getPrinter() no encontró impresora:", printerName, e);
            printer = await qz.printers.getDefault();
            console.warn("[QZ] Usando impresora por defecto:", printer);
        }
        console.log("[QZ] Printer OK:", printer);

        const config = buildQlLabelConfig(printer);

        const absUrl = new URL(reportUrl, browser.location.origin).toString();
        console.log("[QZ] PDF URL (abs):", absUrl);

        const resp = await fetch(absUrl, { credentials: "include", cache: "no-store" });
        console.log("[QZ] PDF fetch status:", resp.status);

        const contentType = (resp.headers.get("content-type") || "").toLowerCase();
        console.log("[QZ] PDF content-type:", contentType);

        if (!resp.ok) {
            throw new Error(`No se pudo descargar el PDF (${resp.status}) desde ${absUrl}`);
        }

        if (!contentType.includes("application/pdf")) {
            const textPreview = await resp.text();
            console.error("[QZ] Respuesta no es PDF. Primeros 200 chars:", textPreview.slice(0, 200));
            throw new Error("La respuesta del servidor no es un PDF. Posible sesión/cookie inválida o redirección a login.");
        }

        const buffer = await resp.arrayBuffer();
        console.log("[QZ] PDF bytes:", buffer.byteLength);

        const pdfBase64 = arrayBufferToBase64(buffer);
        console.log("[QZ] PDF base64 length:", pdfBase64.length);

        const data = [
            {
                type: "pixel",
                format: "pdf",
                flavor: "base64",
                data: pdfBase64,
            },
        ];

        console.log("[QZ] Sending print job...");
        await qz.print(config, data);
        console.log("[QZ] qz.print() enviado");

        return true;
    } catch (error) {
        console.error("[QZ] Error imprimiendo PDF Odoo:", error);
        throw error;
    }
}

//######################################################
// Funciones necesarias para SETTINGS / UI
//######################################################

export async function getAllPrinters() {
    try {
        await connectQz();
        const qz = await ensureQz();
        const printers = await qz.printers.find();
        return Array.isArray(printers) ? printers : [];
    } catch (error) {
        console.error("[QZ] Error obteniendo lista de impresoras:", error);
        throw error;
    }
}

export async function getDefaultPrinter() {
    try {
        await connectQz();
        const qz = await ensureQz();
        const printer = await qz.printers.getDefault();
        return printer || "";
    } catch (error) {
        console.error("[QZ] Error obteniendo impresora por defecto:", error);
        throw error;
    }
}

export async function testQzConnection() {
    try {
        await connectQz();
        const ok = await isQzConnected();
        return ok
            ? { ok: true, message: "Conectado a QZ Tray." }
            : { ok: false, message: "No se pudo activar el websocket de QZ." };
    } catch (error) {
        return { ok: false, message: error?.message || String(error) };
    }
}

//######################################################
// NUEVA API ESTABLE: resolución por tipo (kind)
//######################################################

const WEX_QZ_PARAM_KEYS = {
    label: "wexplay_sat_print.wex_qz_label_printer",
    thermal: "wexplay_sat_print.wex_qz_thermal_printer",
    a4: "wexplay_sat_print.wex_qz_a4_printer",
    debug: "wexplay_sat_print.wex_qz_debug",
    allowFallback: "wexplay_sat_print.wex_qz_allow_fallback",
};

// (Se mantiene por compatibilidad futura; hoy la fuente real es config_parameter)
const WEX_QZ_COMPANY_FIELDS = {
    label: "wex_qz_label_printer",
    thermal: "wex_qz_thermal_printer",
    a4: "wex_qz_a4_printer",
    debug: "wex_qz_debug",
    allowFallback: "wex_qz_allow_fallback",
};

function _getOrmFromEnv(env) {
    return env?.services?.orm || null;
}

function _toBool(value, defaultValue = false) {
    if (typeof value === "boolean") return value;
    if (typeof value === "number") return value !== 0;
    if (typeof value === "string") {
        const v = value.trim().toLowerCase();
        if (["true", "1", "yes", "y", "on"].includes(v)) return true;
        if (["false", "0", "no", "n", "off", ""].includes(v)) return false;
    }
    return defaultValue;
}

async function _getConfigParam(env, key, defaultValue = "") {
    const orm = _getOrmFromEnv(env);
    if (!orm) return defaultValue;

    try {
        const val = await orm.call("ir.config_parameter", "get_param", [key, defaultValue]);
        return val ?? defaultValue;
    } catch (e) {
        console.warn("[QZ] No se pudo leer ir.config_parameter.get_param:", key, e);
        return defaultValue;
    }
}

async function _readCompanyField(env, fieldName) {
    const orm = _getOrmFromEnv(env);
    const companySrv = env?.services?.company;
    const companyId = companySrv?.currentCompany?.id;

    if (!orm || !companyId) return null;

    try {
        const recs = await orm.read("res.company", [companyId], [fieldName]);
        return recs?.[0]?.[fieldName] ?? null;
    } catch (e) {
        console.warn("[QZ] No se pudo leer res.company:", fieldName, e);
        return null;
    }
}

export async function resolvePrinterName(kind, env) {
    if (!["label", "thermal", "a4"].includes(kind)) {
        throw new Error(`resolvePrinterName: kind inválido: ${kind}`);
    }

    const debugRaw = await _getConfigParam(env, WEX_QZ_PARAM_KEYS.debug, "false");
    const allowFallbackRaw = await _getConfigParam(env, WEX_QZ_PARAM_KEYS.allowFallback, "true");

    const debug = _toBool(debugRaw, false);
    const allowFallback = _toBool(allowFallbackRaw, true);

    if (debug || WEX_QZ_DEBUG_FORCE_LOG) {
        console.log(WEX_QZ_DEBUG_TAG, "resolvePrinterName ENTER", {
            kind,
            hasEnv: !!env,
            hasOrm: !!env?.services?.orm,
            allowFallback,
            debug,
        });
    }

    const key = WEX_QZ_PARAM_KEYS[kind];
    const fromParam = String((await _getConfigParam(env, key, "")) || "").trim();
    if (fromParam) {
        if (debug || WEX_QZ_DEBUG_FORCE_LOG) {
            console.log(WEX_QZ_DEBUG_TAG, "resolvePrinterName RESOLVED", {
                kind,
                source: "config_parameter",
                printerName: fromParam,
            });
        }
        return { printerName: fromParam, allowFallback, debug, source: "config_parameter" };
    }

    // Fallback opcional a company (solo si existiera valor)
    const field = WEX_QZ_COMPANY_FIELDS[kind];
    const fromCompany = String((await _readCompanyField(env, field)) || "").trim();
    if (fromCompany) {
        if (debug || WEX_QZ_DEBUG_FORCE_LOG) {
            console.log(WEX_QZ_DEBUG_TAG, "resolvePrinterName RESOLVED", {
                kind,
                source: "company",
                printerName: fromCompany,
            });
        }
        return { printerName: fromCompany, allowFallback, debug, source: "company" };
    }

    if (debug || WEX_QZ_DEBUG_FORCE_LOG) {
        console.log(WEX_QZ_DEBUG_TAG, "resolvePrinterName RESOLVED", {
            kind,
            source: "none",
            printerName: "",
        });
    }
    return { printerName: "", allowFallback, debug, source: "none" };
}

export async function printOdooPdfUrlByKind(kind, reportUrl, env) {
    console.log(WEX_QZ_DEBUG_TAG, "printOdooPdfUrlByKind ENTER", {
        kind,
        reportUrl,
        hasEnv: !!env,
        hasOrm: !!env?.services?.orm,
    });

    const info = await resolvePrinterName(kind, env);

    if (info.debug || WEX_QZ_DEBUG_FORCE_LOG) {
        console.log(WEX_QZ_DEBUG_TAG, "printOdooPdfUrlByKind RESOLUTION", info);
    }

    if (info.printerName) {
        if (info.debug || WEX_QZ_DEBUG_FORCE_LOG) {
            console.log(WEX_QZ_DEBUG_TAG, "printOdooPdfUrlByKind DELEGATE -> printOdooPdfUrl", {
                kind,
                reportUrl,
                printerName: info.printerName,
            });
        }
        return printOdooPdfUrl(reportUrl, info.printerName);
    }

    if (!info.allowFallback) {
        if (info.debug || WEX_QZ_DEBUG_FORCE_LOG) {
            console.log(WEX_QZ_DEBUG_TAG, "printOdooPdfUrlByKind ABORT (no printer, no fallback)", {
                kind,
                reportUrl,
            });
        }
        throw new Error(`No hay impresora configurada para '${kind}' y el fallback está desactivado.`);
    }

    await connectQz();
    const qz = await ensureQz();
    const defaultPrinter = await qz.printers.getDefault();

    if (!defaultPrinter) {
        throw new Error("Fallback activado, pero QZ no devolvió impresora por defecto del sistema.");
    }

    if (info.debug || WEX_QZ_DEBUG_FORCE_LOG) {
        console.log(WEX_QZ_DEBUG_TAG, "printOdooPdfUrlByKind FALLBACK -> defaultPrinter", {
            kind,
            reportUrl,
            printerName: defaultPrinter,
        });
    }

    return printOdooPdfUrl(reportUrl, defaultPrinter);
}

// --- DEBUG helper (solo para consola) ---
if (browser.location.search.includes("debug")) {
    window.WEXPLAY_QZ = {
        ensureQz,
        isQzConnected,
        connectQz,
        disconnectQz,
        getPrinter,
        printImageBase64,
        printOdooPdfUrl,
        resolvePrinterName,
        printOdooPdfUrlByKind,
    };
    console.log("WEXPLAY_QZ listo: usa WEXPLAY_QZ.connectQz()");
}
