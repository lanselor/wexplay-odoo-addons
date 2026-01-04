/** @odoo-module **/

import { browser } from "@web/core/browser/browser";

const QZ_JS_URL = "https://qz.io/api/qz-tray.js";

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
 */
function configureUnsignedSecurity(qz) {
    if (_securityConfigured) return;
    if (!qz?.security) return;

    // Desactiva firma/certificado (modo unsigned)
    // En esta versión, pasar callbacks que devuelven null provoca "Failed to sign"
    qz.security.setCertificatePromise(null);
    qz.security.setSignaturePromise(null);

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
 * Nota: qz.printers.find(<nombre>) devuelve el nombre si existe; si no, lanza.
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
 * Configuración estándar para etiquetas 62x29 (Brother QL-7xx).
 */
export function buildQlLabelConfig(printer) {
    return window.qz.configs.create(printer, {
        units: "mm",
        size: { width: 62, height: 29 },
        margins: { top: 0, right: 0, bottom: 0, left: 0 },
        colorType: "blackwhite",
        copies: 1,
        density: 8,
        interpolation: "nearest",
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
 * Imprime una imagen base64 (PNG).
 */
export async function printImageBase64(base64png, printerName = "Brother QL-710W") {
    try {
        await connectQz();

        const printer = await getPrinter(printerName);
        const config = buildQlLabelConfig(printer);

        const data = [
            {
                type: "image",
                format: "png",
                data: `data:image/png;base64,${base64png}`,
            },
        ];

        await window.qz.print(config, data);
        return true;
    } catch (error) {
        console.error("[QZ] Error en impresión:", error);
        throw error;
    }
}

/**
 * NUEVO: imprime un PDF obtenido desde una URL de Odoo (con sesión) vía QZ.
 * reportUrl debe ser una URL accesible desde el navegador (misma sesión Odoo).
 */
export async function printOdooPdfUrl(reportUrl, printerName = "Brother QL-710W") {
    try {
        console.log("[QZ] PDF URL:", reportUrl);

        await connectQz();
        console.log("[QZ] Connected:", await isQzConnected());

        const printer = await getPrinter(printerName);
        console.log("[QZ] Printer OK:", printer);

        const config = buildQlLabelConfig(printer);

        const resp = await fetch(reportUrl, { credentials: "include", cache: "no-store" });
        console.log("[QZ] PDF fetch status:", resp.status);

        if (!resp.ok) {
            throw new Error(`No se pudo descargar el PDF (${resp.status}) desde ${reportUrl}`);
        }

        const buffer = await resp.arrayBuffer();
        console.log("[QZ] PDF bytes:", buffer.byteLength);

        const pdfBase64 = arrayBufferToBase64(buffer);
        console.log("[QZ] PDF base64 length:", pdfBase64.length);

        const data = [{
            type: "pdf",
            format: "base64",
            data: pdfBase64,
        }];

        console.log("[QZ] Sending print job...");
        await window.qz.print(config, data);
        console.log("[QZ] qz.print() enviado");

        return true;
    } catch (error) {
        console.error("[QZ] Error imprimiendo PDF Odoo:", error);
        throw error;
    }
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
        printOdooPdfUrl, // <- nuevo
    };
    console.log("WEXPLAY_QZ listo: usa WEXPLAY_QZ.connectQz()");
}
