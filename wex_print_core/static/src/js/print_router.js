/** @odoo-module **/

const PRINT_MODE_PARAM = "wex_print_core.print_mode";
const TRACE_MODEL = "wex.print.trace";
const DOCUMENT_TYPE_MODEL = "wex.print.document.type";
const ASSIGNMENT_MODEL = "wex.print.assignment";

async function getPrintMode(env) {
    const orm = env?.services?.orm;
    return (await orm?.call("ir.config_parameter", "get_param", [PRINT_MODE_PARAM, "legacy"])) || "legacy";
}

async function getDocumentType(env, documentCode) {
    const orm = env?.services?.orm;
    const rows =
        (await orm?.searchRead(
            DOCUMENT_TYPE_MODEL,
            [["code", "=", documentCode]],
            ["id", "name", "code", "legacy_kind", "report_name"]
        )) || [];
    return rows[0] || null;
}

export async function resolvePrintRoute(documentCode, env, opts = {}) {
    const requestedMode = await getPrintMode(env);
    const documentType = documentCode ? await getDocumentType(env, documentCode) : null;
    const legacyKind = documentType?.legacy_kind || opts.kind || "label";
    let nextResolution = null;

    try {
        const orm = env?.services?.orm;
        nextResolution = await orm?.call(ASSIGNMENT_MODEL, "resolve_shadow", [documentCode || ""]);
    } catch (error) {
        nextResolution = {
            found: false,
            document_code: documentCode || "",
            message: error?.message || String(error),
        };
    }

    // Fase 2.1: incluso en hybrid/new_only seguimos por legacy para no romper.
    return {
        requestedMode,
        executionMode: requestedMode,
        resolutionSource: "legacy",
        documentType,
        documentCode: documentCode || "",
        kind: legacyKind,
        reportName: documentType?.report_name || opts.reportName || "",
        nextResolution,
    };
}

export async function tracePrintDecision(env, payload) {
    try {
        const orm = env?.services?.orm;
        await orm?.create(TRACE_MODEL, [payload]);
    } catch {
        // Best-effort: la traza nunca debe bloquear la impresión.
    }
}
