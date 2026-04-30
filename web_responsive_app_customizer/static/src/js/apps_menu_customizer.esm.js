/* global Sortable */

import {onMounted, onPatched, onWillUnmount} from "@odoo/owl";
import {useService} from "@web/core/utils/hooks";
import {patch} from "@web/core/utils/patch";
import {session} from "@web/session";
import {user} from "@web/core/user";
import {AppsMenu} from "@web_responsive/components/apps_menu/apps_menu.esm";
import {menuService} from "@web/webclient/menus/menu_service";

const LONG_PRESS_DELAY = 650;
const MOVE_TOLERANCE = 8;

function getStoredOrder() {
    return (session.apps_menu && session.apps_menu.custom_order) || [];
}

function setStoredOrder(order) {
    session.apps_menu = session.apps_menu || {};
    session.apps_menu.custom_order = order;
}

function sortMenusByStoredOrder(menus) {
    const order = getStoredOrder().map((id) => Number(id));
    if (!order.length) {
        return menus;
    }
    const indexedOrder = new Map(order.map((id, index) => [id, index]));
    return [...menus].sort((left, right) => {
        const leftIndex = indexedOrder.get(left.id);
        const rightIndex = indexedOrder.get(right.id);
        if (leftIndex === undefined && rightIndex === undefined) {
            return 0;
        }
        if (leftIndex === undefined) {
            return 1;
        }
        if (rightIndex === undefined) {
            return -1;
        }
        return leftIndex - rightIndex;
    });
}

function getMenuItemId(item) {
    if (item.dataset.menuId) {
        return Number(item.dataset.menuId);
    }
    const href = item.getAttribute("href");
    if (!href) {
        return 0;
    }
    const match = href.match(/(?:^|[?#&])menu_id=(\d+)/);
    return match ? Number(match[1]) : 0;
}

const originalMenuServiceStart = menuService.start;
menuService.start = async function (...args) {
    const service = await originalMenuServiceStart.call(this, ...args);
    const originalGetApps = service.getApps.bind(service);
    service.getApps = () => sortMenusByStoredOrder(originalGetApps());
    return service;
};

patch(AppsMenu.prototype, {
    setup() {
        super.setup(...arguments);
        this.orm = useService("orm");
        this._customizerEditMode = false;
        this._customizerLongPressTimer = null;
        this._customizerPointerStart = null;
        this._customizerClickHandler = this._onCustomizerClick.bind(this);
        this._customizerPointerDownHandler = this._onCustomizerPointerDown.bind(this);
        this._customizerPointerMoveHandler = this._onCustomizerPointerMove.bind(this);
        this._customizerPointerUpHandler = this._onCustomizerPointerUp.bind(this);

        onMounted(() => this._refreshCustomizer());
        onPatched(() => this._refreshCustomizer());
        onWillUnmount(() => {
            this._destroyCustomizerSortable();
            this._clearCustomizerLongPress();
            document.removeEventListener("pointermove", this._customizerPointerMoveHandler);
            document.removeEventListener("pointerup", this._customizerPointerUpHandler);
            document.removeEventListener("pointercancel", this._customizerPointerUpHandler);
        });
    },

    setOpenState(openState) {
        super.setOpenState(...arguments);
        if (!openState) {
            this.exitCustomizerEditMode();
        }
    },

    exitCustomizerEditMode() {
        this._customizerEditMode = false;
        this._customizerContainer?.classList.remove("o_app_menu_customizer_edit_mode");
        this._customizerDoneButton?.remove();
        this._customizerDoneButton = null;
        this._setCustomizerSortableEnabled(false);
    },

    _refreshCustomizer() {
        const container = document.querySelector(".app-menu-container");
        if (!container) {
            this._destroyCustomizerSortable();
            return;
        }
        this._ensureCustomizerMenuIds(container);
        this._applyCustomizerBackground(container);
        this._applyStoredCustomizerOrder(container);
        this._bindCustomizerEvents(container);
        this._setupCustomizerSortable(container);
    },

    _ensureCustomizerMenuIds(container) {
        for (const item of container.querySelectorAll(".o-app-menu-item")) {
            const menuId = getMenuItemId(item);
            if (menuId) {
                item.dataset.menuId = String(menuId);
            }
        }
    },

    _applyCustomizerBackground(container) {
        const backgroundUrl = session.apps_menu && session.apps_menu.background_url;
        if (!backgroundUrl) {
            return;
        }
        container.style.backgroundImage = [
            "linear-gradient(rgba(79, 67, 121, 0.72), rgba(108, 96, 151, 0.62))",
            `url("${backgroundUrl}")`,
        ].join(", ");
    },

    _bindCustomizerEvents(container) {
        if (this._customizerContainer === container) {
            return;
        }
        if (this._customizerContainer) {
            this._customizerContainer.removeEventListener(
                "click",
                this._customizerClickHandler,
                true
            );
            this._customizerContainer.removeEventListener(
                "pointerdown",
                this._customizerPointerDownHandler
            );
        }
        this._customizerContainer = container;
        container.addEventListener("click", this._customizerClickHandler, true);
        container.addEventListener("pointerdown", this._customizerPointerDownHandler);
    },

    _setupCustomizerSortable(container) {
        const list = container.querySelector(".o-app-menu-list");
        if (!list || typeof Sortable === "undefined") {
            return;
        }
        if (this._customizerSortable && this._customizerSortable.el === list) {
            this._setCustomizerSortableEnabled(this._customizerEditMode);
            return;
        }
        this._destroyCustomizerSortable();
        this._customizerSortable = new Sortable(list, {
            animation: 150,
            dataIdAttr: "data-menu-id",
            disabled: !this._customizerEditMode,
            draggable: ".o-app-menu-item",
            ghostClass: "o_app_menu_customizer_sortable_ghost",
            chosenClass: "o_app_menu_customizer_sortable_chosen",
            onEnd: () => this._saveCustomizerOrder(),
        });
    },

    _destroyCustomizerSortable() {
        if (this._customizerSortable) {
            this._customizerSortable.destroy();
            this._customizerSortable = null;
        }
    },

    _setCustomizerSortableEnabled(enabled) {
        if (this._customizerSortable) {
            this._customizerSortable.option("disabled", !enabled);
        }
    },

    _applyStoredCustomizerOrder(container) {
        const list = container.querySelector(".o-app-menu-list");
        if (!list) {
            return;
        }
        const order = getStoredOrder().map((id) => Number(id));
        if (!order.length) {
            return;
        }
        const indexedOrder = new Map(order.map((id, index) => [id, index]));
        const items = [...list.querySelectorAll(".o-app-menu-item")];
        items
            .sort((left, right) => {
                const leftIndex = indexedOrder.get(getMenuItemId(left));
                const rightIndex = indexedOrder.get(getMenuItemId(right));
                if (leftIndex === undefined && rightIndex === undefined) {
                    return 0;
                }
                if (leftIndex === undefined) {
                    return 1;
                }
                if (rightIndex === undefined) {
                    return -1;
                }
                return leftIndex - rightIndex;
            })
            .forEach((item) => list.appendChild(item));
    },

    _onCustomizerPointerDown(event) {
        if (this._customizerEditMode || event.button !== 0) {
            return;
        }
        const item = event.target.closest(".o-app-menu-item");
        if (!item || !this._customizerContainer?.contains(item)) {
            return;
        }
        this._clearCustomizerLongPress();
        this._customizerPointerStart = {
            x: event.clientX,
            y: event.clientY,
        };
        this._customizerLongPressTimer = setTimeout(() => {
            this._enterCustomizerEditMode();
            this._setCustomizerSortableEnabled(true);
        }, LONG_PRESS_DELAY);
        document.addEventListener("pointermove", this._customizerPointerMoveHandler);
        document.addEventListener("pointerup", this._customizerPointerUpHandler);
        document.addEventListener("pointercancel", this._customizerPointerUpHandler);
    },

    _enterCustomizerEditMode() {
        this._customizerEditMode = true;
        this._customizerContainer?.classList.add("o_app_menu_customizer_edit_mode");
        this._ensureCustomizerDoneButton();
    },

    _ensureCustomizerDoneButton() {
        if (this._customizerDoneButton || !this._customizerContainer) {
            return;
        }
        const button = document.createElement("button");
        button.type = "button";
        button.className = "o_app_menu_customizer_done";
        button.title = "Finish editing";
        const icon = document.createElement("i");
        icon.className = "fa fa-check";
        button.appendChild(icon);
        button.addEventListener("click", (event) => {
            event.preventDefault();
            event.stopPropagation();
            this.exitCustomizerEditMode();
        });
        this._customizerContainer.prepend(button);
        this._customizerDoneButton = button;
    },

    _onCustomizerPointerMove(event) {
        if (!this._customizerPointerStart) {
            return;
        }
        const deltaX = Math.abs(event.clientX - this._customizerPointerStart.x);
        const deltaY = Math.abs(event.clientY - this._customizerPointerStart.y);
        if (deltaX > MOVE_TOLERANCE || deltaY > MOVE_TOLERANCE) {
            this._clearCustomizerLongPress();
        }
    },

    _onCustomizerPointerUp() {
        this._clearCustomizerLongPress();
        document.removeEventListener("pointermove", this._customizerPointerMoveHandler);
        document.removeEventListener("pointerup", this._customizerPointerUpHandler);
        document.removeEventListener("pointercancel", this._customizerPointerUpHandler);
    },

    _clearCustomizerLongPress() {
        if (this._customizerLongPressTimer) {
            clearTimeout(this._customizerLongPressTimer);
            this._customizerLongPressTimer = null;
        }
        this._customizerPointerStart = null;
    },

    _onCustomizerClick(event) {
        if (!this._customizerEditMode) {
            return;
        }
        const item = event.target.closest(".o-app-menu-item");
        if (item) {
            event.preventDefault();
            event.stopImmediatePropagation();
        }
    },

    async _saveCustomizerOrder() {
        const list = this._customizerContainer?.querySelector(".o-app-menu-list");
        if (!list) {
            return;
        }
        const order = [...list.querySelectorAll(".o-app-menu-item")]
            .map((item) => getMenuItemId(item))
            .filter(Boolean);
        setStoredOrder(order);
        await this.orm.write("res.users", [user.userId], {
            apps_menu_custom_order: order,
        });
    },
});
