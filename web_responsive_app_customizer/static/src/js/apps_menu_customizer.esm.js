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
const ICON_SIZES = ["small", "medium", "large"];

function getStoredOrder() {
    return getPreferenceList("custom_order");
}

function getPreferenceList(name) {
    return ((session.apps_menu && session.apps_menu[name]) || [])
        .map((key) => String(key))
        .filter(Boolean);
}

function setPreferenceList(name, values) {
    session.apps_menu = session.apps_menu || {};
    session.apps_menu[name] = values;
}

function getIconSize() {
    return (session.apps_menu && session.apps_menu.icon_size) || "medium";
}

function getIconSizeIndex() {
    return Math.max(0, ICON_SIZES.indexOf(getIconSize()));
}

function setStoredOrder(order) {
    setPreferenceList("custom_order", order);
}

function getMenuOrderIndex(indexedOrder, menu) {
    const keys = [getMenuKey(menu), menu.id].map((key) => String(key || ""));
    for (const key of keys) {
        if (indexedOrder.has(key)) {
            return indexedOrder.get(key);
        }
    }
}

function getMenuKey(menu) {
    return String(menu.xmlid || menu.id || "");
}

function sortMenusByStoredOrder(menus) {
    const order = getStoredOrder();
    const favoriteKeys = new Set(getPreferenceList("favorite_keys"));
    if (!order.length && !favoriteKeys.size) {
        return menus;
    }
    const indexedOrder = new Map(order.map((id, index) => [id, index]));
    return [...menus].sort((left, right) => {
        const leftFavorite = favoriteKeys.has(getMenuKey(left));
        const rightFavorite = favoriteKeys.has(getMenuKey(right));
        if (leftFavorite !== rightFavorite) {
            return leftFavorite ? -1 : 1;
        }
        const leftIndex = getMenuOrderIndex(indexedOrder, left);
        const rightIndex = getMenuOrderIndex(indexedOrder, right);
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

function getMenuItemKey(item) {
    if (item.dataset.menuKey) {
        return item.dataset.menuKey;
    }
    if (item.dataset.menuXmlid) {
        return item.dataset.menuXmlid;
    }
    if (item.dataset.menuId) {
        return item.dataset.menuId;
    }
    const href = item.getAttribute("href");
    if (!href) {
        return "";
    }
    const match = href.match(/(?:^|[?#&])menu_id=(\d+)/);
    return match ? match[1] : "";
}

function buildIcon(className) {
    const icon = document.createElement("i");
    icon.className = className;
    return icon;
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
        this._customizerToolbar?.remove();
        this._customizerToolbar = null;
        this._setCustomizerSortableEnabled(false);
        if (this._customizerContainer) {
            this._applyCustomizerItemStates(this._customizerContainer);
        }
    },

    _refreshCustomizer() {
        const container = document.querySelector(".app-menu-container");
        if (!container) {
            this._destroyCustomizerSortable();
            return;
        }
        this._ensureCustomizerMenuKeys(container);
        this._applyCustomizerBackground(container);
        this._applyStoredCustomizerOrder(container);
        this._applyCustomizerIconSize(container);
        this._applyCustomizerItemStates(container);
        this._bindCustomizerEvents(container);
        this._setupCustomizerSortable(container);
    },

    _ensureCustomizerMenuKeys(container) {
        for (const item of container.querySelectorAll(".o-app-menu-item")) {
            const menuKey = getMenuItemKey(item);
            if (menuKey) {
                item.dataset.menuKey = menuKey;
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

    _applyCustomizerIconSize(container) {
        container.dataset.iconSize = getIconSize();
    },

    _applyCustomizerItemStates(container) {
        const favoriteKeys = new Set(getPreferenceList("favorite_keys"));
        const hiddenKeys = new Set(getPreferenceList("hidden_keys"));
        for (const item of container.querySelectorAll(".o-app-menu-item")) {
            const menuKey = getMenuItemKey(item);
            const isFavorite = favoriteKeys.has(menuKey);
            const isHidden = hiddenKeys.has(menuKey);
            item.classList.toggle("o_app_menu_customizer_favorite", isFavorite);
            item.classList.toggle("o_app_menu_customizer_hidden", isHidden);
            item.classList.toggle("d-none", isHidden && !this._customizerEditMode);
            if (this._customizerEditMode) {
                this._ensureCustomizerItemControls(item);
            } else {
                this._removeCustomizerItemControls(item);
            }
        }
    },

    _ensureCustomizerItemControls(item) {
        if (!item.querySelector(".o_app_menu_customizer_item_tools")) {
            const tools = document.createElement("div");
            tools.className = "o_app_menu_customizer_item_tools";
            const favoriteButton = document.createElement("button");
            favoriteButton.type = "button";
            favoriteButton.title = "Toggle favorite";
            favoriteButton.dataset.appMenuCustomizerAction = "favorite";
            const hiddenButton = document.createElement("button");
            hiddenButton.type = "button";
            hiddenButton.title = "Hide or show app";
            hiddenButton.dataset.appMenuCustomizerAction = "hidden";
            tools.append(favoriteButton, hiddenButton);
            item.prepend(tools);
        }
        this._syncCustomizerItemControls(item);
    },

    _syncCustomizerItemControls(item) {
        const favoriteButton = item.querySelector(
            "[data-app-menu-customizer-action='favorite']"
        );
        const hiddenButton = item.querySelector(
            "[data-app-menu-customizer-action='hidden']"
        );
        if (!favoriteButton || !hiddenButton) {
            return;
        }
        favoriteButton.replaceChildren(
            buildIcon(
                item.classList.contains("o_app_menu_customizer_favorite")
                    ? "fa fa-star"
                    : "fa fa-star-o"
            )
        );
        hiddenButton.replaceChildren(
            buildIcon(
                item.classList.contains("o_app_menu_customizer_hidden")
                    ? "fa fa-eye-slash"
                    : "fa fa-eye"
            )
        );
    },

    _removeCustomizerItemControls(item) {
        item.querySelector(".o_app_menu_customizer_item_tools")?.remove();
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
            dataIdAttr: "data-menu-key",
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
        const order = getStoredOrder();
        if (!order.length) {
            const favoriteKeys = new Set(getPreferenceList("favorite_keys"));
            if (!favoriteKeys.size) {
                return;
            }
        }
        const favoriteKeys = new Set(getPreferenceList("favorite_keys"));
        const indexedOrder = new Map(order.map((id, index) => [id, index]));
        const items = [...list.querySelectorAll(".o-app-menu-item")];
        items
            .sort((left, right) => {
                const leftFavorite = favoriteKeys.has(getMenuItemKey(left));
                const rightFavorite = favoriteKeys.has(getMenuItemKey(right));
                if (leftFavorite !== rightFavorite) {
                    return leftFavorite ? -1 : 1;
                }
                const leftIndex = indexedOrder.get(getMenuItemKey(left));
                const rightIndex = indexedOrder.get(getMenuItemKey(right));
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
        this._ensureCustomizerToolbar();
        if (this._customizerContainer) {
            this._applyCustomizerItemStates(this._customizerContainer);
        }
    },

    _ensureCustomizerToolbar() {
        if (this._customizerToolbar || !this._customizerContainer) {
            return;
        }
        const toolbar = document.createElement("div");
        toolbar.className = "o_app_menu_customizer_toolbar";

        const title = document.createElement("div");
        title.className = "o_app_menu_customizer_toolbar_title";
        title.replaceChildren(buildIcon("fa fa-arrows"), document.createTextNode("Editando menú"));

        const sizeControl = document.createElement("label");
        sizeControl.className = "o_app_menu_customizer_size";
        const sizeText = document.createElement("span");
        sizeText.textContent = "Tamaño";
        const sizeInput = document.createElement("input");
        sizeInput.type = "range";
        sizeInput.min = "0";
        sizeInput.max = String(ICON_SIZES.length - 1);
        sizeInput.step = "1";
        sizeInput.value = String(getIconSizeIndex());
        sizeInput.addEventListener("input", () => {
            this._setCustomizerIconSize(ICON_SIZES[Number(sizeInput.value)], false);
        });
        sizeInput.addEventListener("change", () => {
            this._setCustomizerIconSize(ICON_SIZES[Number(sizeInput.value)], true);
        });
        sizeControl.append(sizeText, sizeInput);

        const resetButton = document.createElement("button");
        resetButton.type = "button";
        resetButton.className = "o_app_menu_customizer_toolbar_button";
        resetButton.title = "Restaurar escritorio";
        resetButton.replaceChildren(
            buildIcon("fa fa-refresh"),
            document.createTextNode("Restaurar")
        );
        resetButton.addEventListener("click", (event) => {
            event.preventDefault();
            event.stopPropagation();
            this._resetCustomizerDesktop();
        });

        const doneButton = document.createElement("button");
        doneButton.type = "button";
        doneButton.className = "o_app_menu_customizer_toolbar_button o-primary";
        doneButton.title = "Terminar edición";
        doneButton.replaceChildren(buildIcon("fa fa-check"), document.createTextNode("Listo"));
        doneButton.addEventListener("click", (event) => {
            event.preventDefault();
            event.stopPropagation();
            this.exitCustomizerEditMode();
        });

        toolbar.append(title, sizeControl, resetButton, doneButton);
        this._customizerContainer.prepend(toolbar);
        this._customizerToolbar = toolbar;
    },

    async _setCustomizerIconSize(size, persist) {
        session.apps_menu = session.apps_menu || {};
        session.apps_menu.icon_size = size || "medium";
        if (this._customizerContainer) {
            this._applyCustomizerIconSize(this._customizerContainer);
        }
        if (persist) {
            await this.orm.write("res.users", [user.userId], {
                apps_menu_icon_size: session.apps_menu.icon_size,
            });
        }
    },

    async _resetCustomizerDesktop() {
        const defaults = {
            custom_order: [],
            favorite_keys: [],
            hidden_keys: [],
        };
        for (const [key, value] of Object.entries(defaults)) {
            setPreferenceList(key, value);
        }
        session.apps_menu = session.apps_menu || {};
        session.apps_menu.icon_size = "medium";
        await this.orm.write("res.users", [user.userId], {
            apps_menu_custom_order: [],
            apps_menu_favorite_keys: [],
            apps_menu_hidden_keys: [],
            apps_menu_icon_size: "medium",
        });
        if (this._customizerContainer) {
            this._applyCustomizerIconSize(this._customizerContainer);
            this._applyDefaultMenuOrder(this._customizerContainer);
            this._applyCustomizerItemStates(this._customizerContainer);
            this._refreshCustomizerToolbar();
        }
    },

    _applyDefaultMenuOrder(container) {
        const list = container.querySelector(".o-app-menu-list");
        if (!list) {
            return;
        }
        const defaultOrder = this.menuService.getApps().map(getMenuKey);
        const indexedOrder = new Map(defaultOrder.map((key, index) => [key, index]));
        [...list.querySelectorAll(".o-app-menu-item")]
            .sort((left, right) => {
                const leftIndex = indexedOrder.get(getMenuItemKey(left));
                const rightIndex = indexedOrder.get(getMenuItemKey(right));
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

    _refreshCustomizerToolbar() {
        const sizeInput = this._customizerToolbar?.querySelector("input[type='range']");
        if (sizeInput) {
            sizeInput.value = String(getIconSizeIndex());
        }
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
        const actionButton = event.target.closest("[data-app-menu-customizer-action]");
        if (actionButton) {
            event.preventDefault();
            event.stopImmediatePropagation();
            this._onCustomizerItemAction(actionButton);
            return;
        }
        if (!this._customizerEditMode) {
            return;
        }
        const item = event.target.closest(".o-app-menu-item");
        if (item) {
            event.preventDefault();
            event.stopImmediatePropagation();
        }
    },

    _onCustomizerItemAction(actionButton) {
        const item = actionButton.closest(".o-app-menu-item");
        const menuKey = item && getMenuItemKey(item);
        if (!menuKey) {
            return;
        }
        const action = actionButton.dataset.appMenuCustomizerAction;
        if (action === "favorite") {
            this._toggleCustomizerListValue("favorite_keys", menuKey);
        } else if (action === "hidden") {
            this._toggleCustomizerListValue("hidden_keys", menuKey);
        }
    },

    async _toggleCustomizerListValue(fieldName, menuKey) {
        const currentValues = getPreferenceList(fieldName);
        const nextValues = currentValues.includes(menuKey)
            ? currentValues.filter((key) => key !== menuKey)
            : [...currentValues, menuKey];
        setPreferenceList(fieldName, nextValues);
        if (this._customizerContainer) {
            this._applyStoredCustomizerOrder(this._customizerContainer);
            this._applyCustomizerItemStates(this._customizerContainer);
        }
        const odooField =
            fieldName === "favorite_keys"
                ? "apps_menu_favorite_keys"
                : "apps_menu_hidden_keys";
        await this.orm.write("res.users", [user.userId], {
            [odooField]: nextValues,
        });
    },

    async _saveCustomizerOrder() {
        const list = this._customizerContainer?.querySelector(".o-app-menu-list");
        if (!list) {
            return;
        }
        const order = [...list.querySelectorAll(".o-app-menu-item")]
            .map((item) => getMenuItemKey(item))
            .filter(Boolean);
        setStoredOrder(order);
        await this.orm.write("res.users", [user.userId], {
            apps_menu_custom_order: order,
        });
    },
});
