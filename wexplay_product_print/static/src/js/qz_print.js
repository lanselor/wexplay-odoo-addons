/** @odoo-module **/
console.log("🔥🔥🔥 QZ_PRINT VERSION 27🔥🔥🔥");

import { browser } from "@web/core/browser/browser";

const QZ_JS_URL = "https://qz.io/api/qz-tray.js";
const WEX_QZ_DEBUG_FORCE_LOG = true;  // opcional
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
        // IMPORTANTE: Para Brother QL, 'width' es siempre el ancho físico del rollo (29)
        size: { width: 29, height: 42 }, 
        margins: { top: 0, right: 0, bottom: 0, left: 0 },
        scaleContent: false,  // <--- ESTA ES LA CLAVE: Evita que QZ re-escale el PDF
        orientation: "landscape", 
        colorType: "blackwhite",
        copies: 1,
        density: 8,           // Correcto para Brother
        interpolation: "nearest",
        rasterize: true,      // Obligatorio para evitar errores de fuentes en Brother
        // Añadimos este parámetro para forzar la compatibilidad con el driver
        forceDetailed: true 
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
        const qz = await ensureQz();
        const printer = await getPrinter(printerName);
        const config = buildQlLabelConfig(printer);

        // Limpieza de cabecera para evitar errores de parseo
        const cleanBase64 = base64png.replace(/^data:application\/pdf;base64,/, "");

        const data = [{
            type: 'pixel',    // Correcto
            format: 'pdf',   // Correcto
            flavor: 'base64', // Correcto
            data: cleanBase64
        }];
   
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
        const data = [{
            type: 'pixel',   // Evita el error "No enum constant"
            format: 'pdf',   // Especifica que el contenido es PDF
            flavor: 'base64',// Indica que pasamos el string binario
            data: pdfBase64  // El string generado por arrayBufferToBase64 (ya viene limpio)
        }];

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
//BLOQUES NUEVOS AÑADIDOS PARA LA CONFIGURACIÓN de SETTINGS
//NECESARIOS PARA RECUPERAR DATOS MINIMOS DE CONFIGURACIÓN
//######################################################

//######################################################
//Devuelve la lista de impresoras detectadas por QZ.
 //* @returns {Promise<string[]>}
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

/**
 * Devuelve la impresora por defecto del sistema según QZ.
// * @returns {Promise<string>}
 */
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


/**
 * Test simple: intenta conectar y devuelve un estado y mensaje.
// * @returns {Promise<{ok: boolean, message: string}>}
 */
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
// Objetivo: los módulos consumidores NO eligen impresora.
// Solo dicen kind: "label" | "thermal" | "a4"
//######################################################

const WEX_QZ_PARAM_KEYS = {
    label: "wexplay_sat_print.wex_qz_label_printer",
    thermal: "wexplay_sat_print.wex_qz_thermal_printer",
    a4: "wexplay_sat_print.wex_qz_a4_printer",
    debug: "wexplay_sat_print.wex_qz_debug",
    allowFallback: "wexplay_sat_print.wex_qz_allow_fallback",
};

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
        // Nota: en Odoo web, orm.call(model, method, args)
        const val = await orm.call("ir.config_parameter", "get_param", [key, defaultValue]);
        return val ?? defaultValue;
    } catch (e) {
        // No rompemos impresión por permisos o contexto (conservador)
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

/**
 * Resuelve el nombre de impresora configurada para un tipo.
 * @param {"label"|"thermal"|"a4"} kind
 * @param {Object} env OWL env (this.env)
 * @returns {Promise<{printerName: string, allowFallback: boolean, debug: boolean, source: string}>}
 */
export async function resolvePrinterName(kind, env) {
    if (!["label", "thermal", "a4"].includes(kind)) {
        throw new Error(`resolvePrinterName: kind inválido: ${kind}`);
    }
    const WEX_QZ_DEBUG_TAG = "[WEX_QZ_BYKIND]"; 
    // Defaults alineados con tu res.config.settings (allow_fallback default=True)
    const debugRaw = await _getConfigParam(env, WEX_QZ_PARAM_KEYS.debug, "false");
    const allowFallbackRaw = await _getConfigParam(env, WEX_QZ_PARAM_KEYS.allowFallback, "true");

    const debug = _toBool(debugRaw, false);
    const allowFallback = _toBool(allowFallbackRaw, true);

    // 1) Fuente primaria: config_parameter (lo que guarda Ajustes hoy)
    const key = WEX_QZ_PARAM_KEYS[kind];
    const fromParam = String(await _getConfigParam(env, key, "") || "").trim();
    if (fromParam) {
        return { printerName: fromParam, allowFallback, debug, source: "config_parameter" };
    }

    // 2) Fuente secundaria: res.company (por resiliencia)
    const field = WEX_QZ_COMPANY_FIELDS[kind];
    const fromCompany = String(await _readCompanyField(env, field) || "").trim();
    if (fromCompany) {
        return { printerName: fromCompany, allowFallback, debug, source: "company" };
    }

    // 3) No configurado
    return { printerName: "", allowFallback, debug, source: "none" };
}

/**
 * Imprime un PDF de Odoo por tipo de impresora.
 * Mantiene el flujo existente: resuelve -> llama a printOdooPdfUrl().
 * @param {"label"|"thermal"|"a4"} kind
 * @param {string} reportUrl
 * @param {Object} env OWL env (this.env)
 */
export async function printOdooPdfUrlByKind(kind, reportUrl, env) {
    const info = await resolvePrinterName(kind, env);
    console.log(WEX_QZ_DEBUG_TAG, "printOdooPdfUrlByKind ENTER", {
         kind,
         reportUrl,
         hasEnv: !!env,
         hasOrm: !!env?.services?.orm,
    });
    if (info.debug) {
        console.log("[QZ] printOdooPdfUrlByKind()", { kind, reportUrl, ...info });
    }

    // Caso normal: hay impresora configurada
    if (info.printerName) {
        const WEX_QZ_DEBUG_TAG = "[WEX_QZ_BYKIND]";
        return printOdooPdfUrl(reportUrl, info.printerName);
    }

    // Sin impresora configurada
    if (!info.allowFallback) {
        const WEX_QZ_DEBUG_TAG = "[WEX_QZ_BYKIND-SIN IMPRESORA CONFIGURADA]";
        throw new Error(`No hay impresora configurada para '${kind}' y el fallback está desactivado.`);
    }

    // Fallback: impresora por defecto del sistema (QZ)
    await connectQz();
    const qz = await ensureQz();
    const defaultPrinter = await qz.printers.getDefault();

    const WEX_QZ_DEBUG_TAG = "[WEX_QZ_BYKIND - Impresora por defecto del sisema]";

    if (!defaultPrinter) {
        throw new Error("Fallback activado, pero QZ no devolvió impresora por defecto del sistema.");
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
