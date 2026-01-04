/** @odoo-module **/

import { browser } from "@web/core/browser/browser";

const QZ_JS_URL = "https://qz.io/api/qz-tray.js";


/**
 * Carga un script externo UNA sola vez.
 */
function loadScriptOnce(src) {
    return new Promise((resolve, reject) => {
        try {
            const existing = [...document.getElementsByTagName("script")]
                .find(s => s.src === src);

            if (existing) {
                return resolve();
            }

            const s = document.createElement("script");
            s.src = src;
            s.async = true;

            s.onload = () => resolve();
            s.onerror = () =>
                reject(new Error(`No se pudo cargar el script externo: ${src}`));

            document.head.appendChild(s);
        } catch (err) {
            reject(err);
        }
    });
}

/**
 * Asegura que QZ está disponible.
 */
export async function ensureQz() {
    try {
        if (window.qz) {
            return window.qz;
        }

        await loadScriptOnce(QZ_JS_URL);

        if (!window.qz) {
            throw new Error(
                "QZ Tray no está disponible tras cargar qz-tray.js"
            );
        }

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

        // Forzar conexión sin TLS (ws) para evitar problemas de certificado
        if (qz.websocket && typeof qz.websocket.setConnectionOptions === "function") {
            qz.websocket.setConnectionOptions({
                host: "127.0.0.1",
                usingSecure: false,  // ws://
                port: 8182,
            });
        } else {
            console.warn("[QZ] setConnectionOptions no disponible; usando configuración por defecto.");
        }

        if (qz.websocket.isActive()) {
            return true;
        }

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

// --- DEBUG helper (solo para consola) ---
if (browser.location.search.includes("debug")) {
    window.WEXPLAY_QZ = {
        ensureQz,
        isQzConnected,
        connectQz,
        disconnectQz,
    };
    console.log("WEXPLAY_QZ listo: usa WEXPLAY_QZ.connectQz()");
}
/**
 * Busca una impresora por nombre exacto.
 */
export async function getPrinter(printerName) {
    try {
        const qz = await ensureQz();
        const printer = await qz.printers.find(printerName);
        if (!printer) {
            throw new Error(`Impresora no encontrada: ${printerName}`);
        }
        return printer;
    } catch (error) {
        console.error("[QZ] Error buscando impresora:", error);
        throw error;
    }
}

/**
 * Configuración estándar para Brother QL-700 (62x29).
 */
export function buildQl700Config(printer) {
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
 * Imprime una imagen base64 (PNG).
 */
export async function printImageBase64(base64png, printerName = "Brother QL-710W") {
    try {
        await connectQz();

        const printer = await getPrinter(printerName);
        const config = buildQl700Config(printer);

        const data = [{
            type: "image",
            format: "png",
            data: base64png,
        }];

        await window.qz.print(config, data);
        return true;

    } catch (error) {
        console.error("[QZ] Error en impresión:", error);
        throw error;
    }
}