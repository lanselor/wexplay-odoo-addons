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

        if (qz.websocket.isActive()) {
            return true;
        }

        const timeoutMs = 4000;

        const connectPromise = qz.websocket.connect();

        const timeoutPromise = new Promise((_, reject) =>
            browser.setTimeout(
                () => reject(new Error("Timeout conectando con QZ Tray")),
                timeoutMs
            )
        );

        await Promise.race([connectPromise, timeoutPromise]);
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