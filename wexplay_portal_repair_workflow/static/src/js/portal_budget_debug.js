/** @odoo-module **/

const STORAGE_KEY = "wexplay.portal_budget_debug_snapshot";

function getDebugScript() {
    return document.getElementById("wexPortalBudgetDebugData");
}

function readSnapshotFromPage() {
    const script = getDebugScript();
    if (!script) {
        return null;
    }
    try {
        return JSON.parse(script.textContent || "{}");
    } catch (_error) {
        return null;
    }
}

function saveSnapshot(snapshot) {
    if (!snapshot) {
        return;
    }
    try {
        window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(snapshot));
    } catch (_error) {
        // Ignore storage issues in portal debug helper.
    }
}

function loadSnapshot() {
    try {
        const raw = window.sessionStorage.getItem(STORAGE_KEY);
        return raw ? JSON.parse(raw) : null;
    } catch (_error) {
        return null;
    }
}

function enrichSnapshot(baseSnapshot, action) {
    const snapshot = Object.assign({}, baseSnapshot || {});
    snapshot.last_action = action || snapshot.last_action || "";
    snapshot.saved_at = new Date().toISOString();
    snapshot.page_url = window.location.href;
    return snapshot;
}

function bindBudgetDebugForms(baseSnapshot) {
    const forms = document.querySelectorAll("form[data-wex-portal-debug-action]");
    for (const form of forms) {
        form.addEventListener("submit", () => {
            const action = form.dataset.wexPortalDebugAction || "";
            saveSnapshot(enrichSnapshot(baseSnapshot, action));
        });
    }
}

function isForbiddenPage() {
    const title = (document.title || "").toLowerCase();
    const bodyText = (document.body && document.body.innerText
        ? document.body.innerText
        : ""
    ).toLowerCase();
    return title.includes("403") || bodyText.includes("403: prohibido");
}

function findForbiddenAnchor() {
    return (
        document.querySelector(".oe_structure, main, #wrap, .container") || document.body
    );
}

function renderForbiddenSnapshot(snapshot) {
    if (!snapshot || document.getElementById("wexPortalDebugSnapshotFallback")) {
        return;
    }
    const anchor = findForbiddenAnchor();
    if (!anchor) {
        return;
    }

    const rows = Object.entries(snapshot)
        .map(([key, value]) => {
            const safeValue =
                value === false ? "False" : value === true ? "True" : value || "-";
            return `
                <tr>
                    <th style="padding:6px 10px;border-top:1px solid #d7d7d7;text-align:left;white-space:nowrap;">${key}</th>
                    <td style="padding:6px 10px;border-top:1px solid #d7d7d7;">${safeValue}</td>
                </tr>
            `;
        })
        .join("");

    const wrapper = document.createElement("section");
    wrapper.id = "wexPortalDebugSnapshotFallback";
    wrapper.style.margin = "24px 0";
    wrapper.innerHTML = `
        <div style="border:1px solid #d7d7d7;border-radius:12px;background:#f6f6f6;padding:20px;">
            <h3 style="margin:0 0 8px 0;font-size:24px;">Ultimo snapshot portal</h3>
            <p style="margin:0 0 14px 0;color:#666;">
                Esta traza se guardo en el navegador justo antes de la accion del portal que acabo en 403.
            </p>
            <div style="overflow:auto;">
                <table style="width:100%;border-collapse:collapse;font-size:14px;">
                    <tbody>${rows}</tbody>
                </table>
            </div>
        </div>
    `;
    anchor.prepend(wrapper);
}

document.addEventListener("DOMContentLoaded", () => {
    const pageSnapshot = readSnapshotFromPage();
    if (pageSnapshot) {
        const enrichedSnapshot = enrichSnapshot(pageSnapshot, "");
        saveSnapshot(enrichedSnapshot);
        bindBudgetDebugForms(enrichedSnapshot);
    }

    if (isForbiddenPage()) {
        renderForbiddenSnapshot(loadSnapshot());
    }
});
