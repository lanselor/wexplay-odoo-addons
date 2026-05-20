/** @odoo-module **/

const CONVERSATION_HASHES = new Set([
    "#portalRepairConversation",
    "#portalRepairConversationComposer",
    "#tab-conversacion",
]);

function isDebugEnabled() {
    const params = new URLSearchParams(window.location.search);
    return params.get("debug_portal_chat") === "1";
}

function debugLog(step, payload = {}) {
    if (!isDebugEnabled()) {
        return;
    }
    console.info("[wex portal chat]", step, payload);
}

function writeDebugStatus(message) {
    const node = document.getElementById("wexPortalChatJsDebug");
    if (node) {
        node.textContent = `estado js: ${message}`;
    }
}

function getConversationTrigger() {
    return document.getElementById("tab-conversacion-btn");
}

function getConversationPanel() {
    return document.getElementById("portalRepairConversation");
}

function getFichaTrigger() {
    return document.getElementById("tab-ficha-btn");
}

function getConversationPane() {
    return document.getElementById("tab-conversacion");
}

function getFichaPane() {
    return document.getElementById("tab-ficha");
}

function shouldOpenConversation() {
    const hash = window.location.hash || "";
    if (CONVERSATION_HASHES.has(hash)) {
        return true;
    }
    const params = new URLSearchParams(window.location.search);
    return params.get("tab") === "conversation";
}

function openConversationTab() {
    const trigger = getConversationTrigger();
    debugLog("openConversationTab:start", {
        hasTrigger: Boolean(trigger),
        hasBootstrapTab: Boolean(window.bootstrap?.Tab),
        query: window.location.search,
        hash: window.location.hash,
    });
    if (!trigger || !window.bootstrap?.Tab) {
        debugLog("openConversationTab:bootstrap-missing");
        writeDebugStatus("bootstrap ausente o trigger no encontrado");
        manuallyActivateConversationTab();
        return false;
    }
    window.bootstrap.Tab.getOrCreateInstance(trigger).show();
    debugLog("openConversationTab:bootstrap-show", {
        triggerClasses: trigger.className,
        paneClasses: getConversationPane()?.className,
    });
    writeDebugStatus("bootstrap show ejecutado");
    return true;
}

function focusConversationPanel() {
    const panel = getConversationPanel();
    if (!panel) {
        debugLog("focusConversationPanel:no-panel");
        writeDebugStatus("panel de conversación no encontrado");
        return;
    }
    panel.scrollIntoView({ behavior: "smooth", block: "start" });
    const composer = document.getElementById("portal_conversation_body");
    if (window.location.hash === "#portalRepairConversationComposer" && composer) {
        window.setTimeout(() => composer.focus(), 250);
    }
    debugLog("focusConversationPanel:done", {
        hasComposer: Boolean(composer),
    });
    writeDebugStatus("panel enfocado");
}

function manuallyActivateConversationTab() {
    const trigger = getConversationTrigger();
    const fichaTrigger = getFichaTrigger();
    const pane = getConversationPane();
    const fichaPane = getFichaPane();
    if (!trigger || !pane) {
        debugLog("manuallyActivateConversationTab:missing-elements", {
            hasTrigger: Boolean(trigger),
            hasPane: Boolean(pane),
        });
        writeDebugStatus("faltan elementos para activar conversación");
        return false;
    }
    document
        .querySelectorAll("#repairDetailTabs .nav-link")
        .forEach((element) => {
            element.classList.remove("active");
            element.setAttribute("aria-selected", "false");
        });
    document
        .querySelectorAll("#repairDetailTabsContent .tab-pane")
        .forEach((element) => {
            element.classList.remove("show", "active");
        });
    trigger.classList.add("active");
    trigger.setAttribute("aria-selected", "true");
    pane.classList.add("show", "active");
    debugLog("manuallyActivateConversationTab:done", {
        triggerClasses: trigger.className,
        paneClasses: pane.className,
        fichaTriggerClasses: fichaTrigger?.className,
        fichaPaneClasses: fichaPane?.className,
    });
    writeDebugStatus("activación manual completada");
    return true;
}

function bootstrapPortalConversation() {
    debugLog("bootstrapPortalConversation:init", {
        query: window.location.search,
        hash: window.location.hash,
        shouldOpen: shouldOpenConversation(),
    });
    writeDebugStatus("js cargado");
    if (!shouldOpenConversation()) {
        writeDebugStatus("no hace falta abrir conversación");
        return;
    }
    manuallyActivateConversationTab();
    openConversationTab();
    window.setTimeout(() => {
        focusConversationPanel();
        writeDebugStatus(
            `trigger=${getConversationTrigger()?.className || "?"} | pane=${getConversationPane()?.className || "?"}`
        );
    }, 120);
}

document.addEventListener("DOMContentLoaded", bootstrapPortalConversation);
window.addEventListener("load", bootstrapPortalConversation);
