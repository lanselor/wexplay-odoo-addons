# Implementation Status

## Scope of this document

This document records what is already implemented and validated in the current phase across:

- Odoo `wex_device_test`
- the Android app `WexDeviceTestApp`
- the external APK download mini web

It is not a roadmap. It is an implementation snapshot meant to reduce context loss.

## Odoo implementation already present

### Core models

The module already includes these operational models:

- `wex.device.test.session`
- `wex.device.test.log`
- `wex.device.test.result`
- `wex.device.test.run`

Current role of each one:

- `session`: current aggregated state of one Android device in one company
- `log`: historical technical and operational events
- `result`: concrete guided test results
- `run`: one concrete SAT review linked to one `repair.order`

### HTTP endpoints

The following endpoints already exist and are working:

- `POST /wex/device-test/session/ping`
- `POST /wex/device-test/session/diagnostic`
- `POST /wex/device-test/session/result`
- `POST /wex/device-test/run/pair`

Authentication is already enforced through:

- `Authorization: Bearer <api_token>`

### Pairing and run lifecycle

The current pairing flow is already implemented:

- Odoo creates a `run`
- Odoo generates `pairing_token`
- Odoo generates `pairing_code`
- Android pairs through `/run/pair`
- Odoo links `run` and `session`
- later `ping`, `diagnostic` and `result` can travel with `run_id` and `pairing_token`

Current active run states:

- `pending_pairing`
- `paired`
- `in_progress`
- `completed`
- `cancelled`

### Repair order integration

The module already extends `repair.order` with a first operational test flow.

Current capabilities already implemented in the repair form:

- create `Test Run`
- open active run
- restart pairing
- show and hide technical pairing token
- display current session when paired
- display QR for APK download
- display QR for repair pairing
- switch visible panel between preparation and active session

### Current QR implementation in Odoo

Odoo already generates two QR images:

- APK download QR
- run pairing QR

The route validated in the current environment is:

- `/report/barcode/QR/<value>?width=<w>&height=<h>`

The project explicitly does not rely on the alternative query-string style `?type=QR` because that failed in the validated environment.

### Configuration already present

Current configuration values already introduced:

- `wex_device_test.api_token`
- `wex_device_test.public_base_url`

The purpose of `public_base_url` is to avoid generating a QR that points Android to a non-reachable `localhost`.

## External APK download mini web

The current project already includes a separate mini web outside Odoo for APK delivery.

Location in local environment:

- `C:\odoo18\test`

Planned publication target:

- `https://www.wexplay.com/test`

Current known decisions:

- debug password: `1337`
- the placeholder APK must be replaced with the real exported APK from Android Studio

## Android implementation already present

### Functional capabilities

The Android app already goes beyond a simple ping prototype.

Capabilities already introduced:

- manual Odoo base URL configuration
- manual API token configuration
- ping against Odoo
- manual pairing
- QR pairing
- local persistence of pairing state
- basic diagnostic submission
- guided result submission
- local logs and operational summaries
- dashboard UI in active iteration
- tests menu in active iteration

### Contract alignment

The Android side is already aligned with:

- `API_CONTRACT.md`

That includes:

- `run_id`
- `pairing_token`
- `pairing_code`
- QR payload parsing
- operational requests after pairing

### QR scanning

QR reading is already implemented through a dependency-based approach rather than custom reinvention.

The chosen direction during the project was to use an existing scanner integration instead of writing QR recognition logic from scratch.

### Local pairing state

The Android app already persists locally at least:

- `run_id`
- `session_id`
- `pairing_token`
- `pairing_code`
- `repair_order_name`
- `run_name`
- `run_state`
- `base_url`

That state is already reused by dashboard summaries and by the tests area.

## Android UI status

### Dashboard

The dashboard has already been redesigned from a monolithic technical screen into a menu-oriented structure, but the UX is still under refinement.

Current themes already discussed and partially implemented:

- home should behave as an operational menu
- configuration, pairing, tests and logs should be separated
- oversized cards with too much passive information should be reduced
- SAT reference should be visible where it gives the technician context

### Tests screen

The tests area already has a visual menu of test items and status badges.

Open UX issues already detected:

- some actions such as `Abrir` were shown before their navigation target was fully implemented
- SAT context should be clearer in the tests area
- the tests screen is promising visually and should remain the main working area

## Issues and lessons already discovered

These are not future risks. They already happened during validation and should remain documented:

- confusion between `pairing_code` and `pairing_token`
- QR generation route mismatch in Odoo until the native working route was used
- `localhost` leaking into QR bootstrap when the environment needed a LAN IP or public URL
- Android cleartext policy blocking local HTTP without explicit allowance
- operational requests being contaminated by stale pairing context until connectivity and run context were separated

## What is not final yet

The following areas are still considered under active design iteration:

- final UX of the Android dashboard
- final UX split between connection and results inside SAT `Test`
- final modelling of `Test` for non-mobile device types
- whether future device families will get their own specialized modules

## Current architectural conclusion

At the end of the current phase, the project already has:

- a working Odoo backend
- a working run pairing flow
- working QR generation in Odoo
- a working external APK delivery path
- a working Android pairing and reporting base

What remains open is mostly product modelling and UX refinement, not the existence of a viable technical foundation.
