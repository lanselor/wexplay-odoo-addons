/** @odoo-module **/

const CONFIG_SELECTOR = "#wexPortalPendingBudgetAlertData";
const MODAL_SELECTOR = "#wexPortalPendingBudgetModal";

function readAlertConfig() {
    const element = document.querySelector(CONFIG_SELECTOR);
    if (!element) {
        return null;
    }
    const reminderHours = Number.parseFloat(element.dataset.reminderHours || "5");
    const alertCount = Number.parseInt(element.dataset.alertCount || "0", 10);
    return {
        storageKey: element.dataset.storageKey || "",
        reminderHours: Number.isFinite(reminderHours) ? reminderHours : 5,
        alertCount: Number.isFinite(alertCount) ? alertCount : 0,
    };
}

function loadLastShownAt(storageKey) {
    if (!storageKey) {
        return null;
    }
    try {
        const rawValue = window.localStorage.getItem(storageKey);
        const parsedValue = rawValue ? JSON.parse(rawValue) : null;
        return parsedValue && parsedValue.lastShownAt ? parsedValue.lastShownAt : null;
    } catch (_error) {
        return null;
    }
}

function saveLastShownAt(storageKey, alertCount) {
    if (!storageKey) {
        return;
    }
    try {
        window.localStorage.setItem(
            storageKey,
            JSON.stringify({
                lastShownAt: new Date().toISOString(),
                alertCount: alertCount || 0,
            })
        );
    } catch (_error) {
        // Ignore localStorage issues in the portal reminder helper.
    }
}

function shouldShowReminder(config) {
    if (!config || !config.storageKey || !config.alertCount) {
        return false;
    }
    const lastShownAt = loadLastShownAt(config.storageKey);
    if (!lastShownAt) {
        return true;
    }
    const lastShownTime = Date.parse(lastShownAt);
    if (Number.isNaN(lastShownTime)) {
        return true;
    }
    const elapsedMs = Date.now() - lastShownTime;
    const reminderWindowMs = config.reminderHours * 60 * 60 * 1000;
    return elapsedMs >= reminderWindowMs;
}

function showReminderModal(config) {
    const modalElement = document.querySelector(MODAL_SELECTOR);
    if (!modalElement || !window.bootstrap || !window.bootstrap.Modal) {
        return;
    }
    const modal = window.bootstrap.Modal.getOrCreateInstance(modalElement);
    saveLastShownAt(config.storageKey, config.alertCount);
    modal.show();
}

document.addEventListener("DOMContentLoaded", () => {
    const config = readAlertConfig();
    if (shouldShowReminder(config)) {
        showReminderModal(config);
    }
});
