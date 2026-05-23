/** @odoo-module **/

function wait(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
}

export async function openPortalRepairOperatorChat(env, params = {}) {
    const channelId = params.channel_id;
    if (!channelId) {
        return false;
    }

    const store = env.services["mail.store"];
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
