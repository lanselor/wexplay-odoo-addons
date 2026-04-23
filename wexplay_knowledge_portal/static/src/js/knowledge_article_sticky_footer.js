/** @odoo-module **/

let floatingFooterBootObserver = null;
let floatingFooterBound = false;

function getArticleForms() {
    return [...document.querySelectorAll(".o_form_view.wex_kb_article_form")];
}

function shouldShowFloatingBar(form) {
    const floatingBar = form.querySelector(".wex_kb_workspace_floating_bar");
    const topbar = form.querySelector(".wex_kb_workspace_topbar");
    if (!floatingBar || !topbar) {
        return false;
    }
    const topbarRect = topbar.getBoundingClientRect();
    const formRect = form.getBoundingClientRect();
    return topbarRect.bottom < 72 && formRect.bottom > 180;
}

function syncFloatingBars() {
    for (const form of getArticleForms()) {
        const floatingBar = form.querySelector(".wex_kb_workspace_floating_bar");
        if (!floatingBar) {
            continue;
        }
        floatingBar.classList.toggle("is-visible", shouldShowFloatingBar(form));
    }
}

function bindFloatingFooterListeners() {
    if (floatingFooterBound) {
        return;
    }
    floatingFooterBound = true;
    window.addEventListener("scroll", syncFloatingBars, { passive: true });
    window.addEventListener("resize", syncFloatingBars, { passive: true });
    document.addEventListener("click", () => window.requestAnimationFrame(syncFloatingBars), true);
    document.addEventListener("keyup", () => window.requestAnimationFrame(syncFloatingBars), true);
}

function bootFloatingFooter() {
    bindFloatingFooterListeners();
    syncFloatingBars();
}

function startFloatingFooterBootObserver() {
    if (floatingFooterBootObserver) {
        return;
    }
    floatingFooterBootObserver = new MutationObserver(() => {
        if (!getArticleForms().length) {
            return;
        }
        bootFloatingFooter();
    });
    floatingFooterBootObserver.observe(document.body, { childList: true, subtree: true });
}

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => {
        bootFloatingFooter();
        startFloatingFooterBootObserver();
    });
} else {
    bootFloatingFooter();
    startFloatingFooterBootObserver();
}
