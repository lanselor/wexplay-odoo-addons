/** @odoo-module **/

function wait(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
}

async function closeAppsMenuIfNeeded(env) {
    const appMenuContainer = document.querySelector(".app-menu-container");
    if (!appMenuContainer) {
        return;
    }
    env.bus?.trigger("ACTION_MANAGER:UI-UPDATED");
    env.bus?.trigger("APPS_MENU:STATE_CHANGED", false);

    const closeAttempts = [0, 25, 75, 150];
    for (const delay of closeAttempts) {
        if (delay) {
            await wait(delay);
        }
        if (!document.querySelector(".app-menu-container")) {
            break;
        }
    }
}

export async function openPortalRepairOperatorChat(env, params = {}) {
    const channelId = params.channel_id;
    if (!channelId) {
        return false;
    }

    const store = env.services["mail.store"];
    await closeAppsMenuIfNeeded(env);
    const attempts = [0, 250, 750, 1500];

    for (const delay of attempts) {
        if (delay) {
            await wait(delay);
        }
        const thread = await store.Thread.getOrFetch({
            model: "discuss.channel",
            id: channelId,
        });
        if (thread) {
            thread.open();
            return true;
        }
    }

    return false;
}
