// Run with: node wexplay_attendance_desktop/tests/attendance_service.test.mjs
// Exercise the service with native route responses; no database writes.
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {runInNewContext} from "node:vm";
import {test} from "node:test";

const source = readFileSync(new URL("../static/src/attendance_service.js", import.meta.url), "utf8")
    .replace(/^import .*;\r?\n/gm, "")
    .replace(/export /g, "");
const employee = (state = "checked_out", extra = {}) => ({
    id: 7, display_systray: true, attendance_state: state,
    last_check_in: "2026-10-18 06:00:00", hours_today: 2, ...extra,
});

function setup(responses) {
    const calls = [];
    const events = [];
    const context = {
        reactive: (value) => value,
        registry: {category: () => ({add() {}})},
        _t: (value) => value,
        isIosApp: () => false,
        navigator: {onLine: false},
        setTimeout, clearTimeout,
        rpc: async (route, params) => {
            calls.push({route, params});
            const next = responses.shift();
            if (next instanceof Error) { throw next; }
            return typeof next === "function" ? next() : next;
        },
    };
    runInNewContext(source + "\nglobalThis.Service = DesktopAttendance;", context);
    const service = new context.Service({trigger: (event) => events.push(event)});
    return {service, calls, events, context};
}

test("entry and exit use native routes and authoritative server data", async () => {
    for (const [before, after] of [["checked_out", "checked_in"], ["checked_in", "checked_out"]]) {
        const {service, calls, events} = setup([employee(before), employee(before), employee(after)]);
        await service.refresh();
        await service.signInOut();
        assert.equal(service.state.employee.attendance_state, after);
        assert.equal(calls[2].route, "/hr_attendance/systray_check_in_out");
        assert.equal(service.state.ready, true);
        assert.match(service.state.message, /registrada correctamente/);
        assert.equal(service.state.busy, false);
        assert.ok(events.length >= 2);
    }
});

test("shared lock prevents a second action during location acquisition", async () => {
    const {service, calls} = setup([employee(), employee(), employee("checked_in")]);
    await service.refresh();
    let release;
    service._getPosition = () => new Promise((resolve) => { release = resolve; });
    const first = service.signInOut();
    await service.signInOut();
    assert.equal(calls.length, 1);
    assert.equal(service.state.busy, true);
    release({latitude: false, longitude: false});
    await first;
    assert.equal(calls.filter((call) => call.route.endsWith("systray_check_in_out")).length, 1);
});

test("changed state, employee, session or company eligibility never toggles", async () => {
    for (const changed of [employee("checked_in"), employee("checked_out", {id: 8}),
        employee("checked_out", {last_check_in: "2026-10-18 08:00:00"}),
        employee("checked_out", {display_systray: false}), {}]) {
        const {service, calls} = setup([employee(), changed]);
        await service.refresh();
        await service.signInOut();
        assert.equal(calls.length, 2);
        assert.match(service.state.message, /estado ha cambiado/);
    }
});

test("network failure requires refresh and cannot silently repeat a toggle", async () => {
    const {service, calls} = setup([employee(), employee(), new Error("Disconnected"), employee("checked_in")]);
    await service.refresh();
    await service.signInOut();
    assert.equal(service.state.ready, false);
    assert.match(service.state.error, /confirmar el fichaje/);
    assert.equal(service.state.message, "");
    await service.signInOut();
    assert.equal(calls.length, 3);
    await service.refresh();
    assert.equal(service.state.employee.attendance_state, "checked_in");
    assert.equal(service.state.ready, true);
});

test("failed preflight and unexpected mutation response never report success", async () => {
    for (const responses of [[employee(), new Error("Read failed")], [employee(), employee(), {}]]) {
        const {service} = setup(responses);
        await service.refresh();
        await service.signInOut();
        assert.equal(service.state.ready, false);
        assert.ok(service.state.error);
        assert.equal(service.state.message, "");
    }
});

test("ineligible users cannot submit attendance", async () => {
    for (const data of [{}, employee("checked_out", {display_systray: false})]) {
        const {service, calls} = setup([data]);
        await service.refresh();
        await service.signInOut();
        assert.equal(calls.length, 1);
    }
});

test("native systray can supply its displayed state for stale-state validation", async () => {
    const {service, calls} = setup([employee("checked_in"), employee("checked_in")]);
    await service.refresh();
    await service.signInOut(employee("checked_out"));
    assert.equal(calls.length, 2);
    assert.match(service.state.message, /estado ha cambiado/);
});

test("concurrent reads are combined and failures release the read lock", async () => {
    let release;
    const {service, calls} = setup([() => new Promise((resolve) => { release = resolve; }), new Error("Offline")]);
    const first = service.refresh();
    const second = service.refresh();
    assert.equal(calls.length, 1);
    release(employee());
    await Promise.all([first, second]);
    await service.refresh();
    assert.equal(service.state.refreshing, false);
    assert.equal(service.state.ready, false);
});

test("geolocation denial falls back to native coordinates without blocking", async () => {
    const {service, context} = setup([]);
    context.navigator = {onLine: true, geolocation: {
        getCurrentPosition(success, failure) { failure(); },
    }};
    const position = await service._getPosition();
    assert.equal(position.latitude, false);
    assert.equal(position.longitude, false);
});
