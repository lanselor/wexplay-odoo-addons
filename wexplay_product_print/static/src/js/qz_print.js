/** @odoo-module **/
console.log("🔥🔥🔥 QZ_PRINT VERSION 2026-01-04 🔥🔥🔥");

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
 *
 * IMPORTANTE: no tocar la estrategia aquí (punto 2).
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
 * Mantenemos el if (!printer) por robustez (punto 2).
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
 * (No refactorizamos buildQlLabelConfig para mantener cambios mínimos.)
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

        const qz = await ensureQz(); // ✅ usar instancia consistente (evitar window.qz.print)
        const printer = await getPrinter(printerName);
        const config = buildQlLabelConfig(printer);

        const data = [
            {
                type: 'pixel',    // Siempre 'pixel' para PDF
                format: 'pdf',   // El formato real del archivo
                flavor: 'base64', // Indica que 'data' es un string base64
                data: cleanBase64 // Solo el string binario
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
  const res = await fetch(url, {
    credentials: "include", // usa la sesión Odoo del navegador
  });
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
        type: 'pixel',   // Indica que es un formato gráfico (PDF/Imagen)
        format: 'pdf',   // Indica la extensión del archivo
        flavor: 'file',  // Indica que los datos vienen de una URL o ruta de archivo
        data: pdfUrl     // Tu URL firmada: http://sat.wexplay.com/...
    },
];

    console.log("[QZ] printing PDF URL via QZ:", pdfUrl);
    await qz.print(config, data);
    return true;
}



/**
 * Imprime un PDF obtenido desde una URL de Odoo (con sesión) vía QZ.
 * reportUrl debe ser una URL accesible desde el navegador (misma sesión Odoo).
 */
export async function printOdooPdfUrl(reportUrl, printerName = "Brother QL-710W") {
    console.log("[QZ] ENTER printOdooPdfUrl()", { reportUrl, printerName });

    try {
        // 1) Asegurar conexión QZ
        await connectQz();
        console.log("[QZ] Connected:", await isQzConnected());

        // 2) Instancia consistente de QZ (evita mezclar window.qz y otras refs)
        const qz = await ensureQz();

        // 3) Resolver impresora (exact match o fallback)
        let printer;
        try {
            printer = await getPrinter(printerName);
        } catch (e) {
            console.warn("[QZ] getPrinter() no encontró impresora:", printerName, e);
            // fallback seguro si tu getPrinter no lo hace internamente
            printer = await qz.printers.getDefault();
            console.warn("[QZ] Usando impresora por defecto:", printer);
        }
        console.log("[QZ] Printer OK:", printer);

        // 4) Config de etiqueta (tu builder)
        const config = buildQlLabelConfig(printer);

        // 5) URL absoluta coherente con Odoo (importantísimo para fetch con sesión)
        const absUrl = new URL(reportUrl, browser.location.origin).toString();
        console.log("[QZ] PDF URL (abs):", absUrl);

        // 6) Descargar PDF con la sesión del navegador (credenciales incluidas)
        const resp = await fetch(absUrl, { credentials: "include", cache: "no-store" });
        console.log("[QZ] PDF fetch status:", resp.status);

        // Odoo a veces devuelve HTML (login) con 200; validamos content-type
        const contentType = (resp.headers.get("content-type") || "").toLowerCase();
        console.log("[QZ] PDF content-type:", contentType);

        if (!resp.ok) {
            throw new Error(`No se pudo descargar el PDF (${resp.status}) desde ${absUrl}`);
        }

        // Si no es PDF, casi seguro es página de login o error HTML
        if (!contentType.includes("application/pdf")) {
            const textPreview = await resp.text();
            console.error("[QZ] Respuesta no es PDF. Primeros 200 chars:", textPreview.slice(0, 200));
            throw new Error("La respuesta del servidor no es un PDF. Posible sesión/cookie inválida o redirección a login.");
        }

        // 7) Convertir a base64
        const buffer = await resp.arrayBuffer();
        console.log("[QZ] PDF bytes:", buffer.byteLength);

        const pdfBase64 = arrayBufferToBase64(buffer);
        console.log("[QZ] PDF base64 length:", pdfBase64.length);

        // 8) Enviar job a QZ
        const data = [
        {
            type: "pdf",
            format: "data",
            data: "data:application/pdf;base64," + pdfBase64,
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
    };
    console.log("WEXPLAY_QZ listo: usa WEXPLAY_QZ.connectQz()");
}
