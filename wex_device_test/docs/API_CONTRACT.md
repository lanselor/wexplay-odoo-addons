# API Contract

## Scope

This document defines the shared contract between:

- Odoo `wex_device_test`
- the Android APK `Wex Device Test`
- the QR pairing payload rendered from the repair order test flow

It covers:

- API authentication
- device session context
- run pairing flow
- diagnostic flow
- guided test result flow
- QR payload used to bootstrap pairing

## Common headers

- `Authorization: Bearer <api_token>`
- `Content-Type: application/json`

## Common device block

The Android app must send these fields in `ping`, `diagnostic`, `result` and `pair` requests.

```json
{
  "device_uuid": "9a6f4e44-4f3b-4bc3-9d66-3c5059aa91f0",
  "manufacturer": "Google",
  "model": "Pixel 8",
  "android_version": "15",
  "sdk_int": 35,
  "app_version": "1.0.0"
}
```

## Run pairing flow

### Functional goal

Before sending guided test data to a repair order, the APK must pair itself with one concrete `wex.device.test.run`.

The run is created in Odoo from the repair order test flow for one concrete SAT repair.

### Pair endpoint

- Method: `POST`
- URL: `/wex/device-test/run/pair`
- Content type: `application/json`

### Pair request body

`pairing_token` is the main key for real pairing.

`pairing_code` is an optional manual fallback and should not be treated as the strongest identifier if a token is available.

Practical rule:

- in QR-driven pairing, the APK should privilege `pairing_token`
- `pairing_code` remains a technician-friendly fallback
- the UI should avoid presenting both values with similar weight, because that caused real operator confusion during validation

```json
{
  "device_uuid": "9a6f4e44-4f3b-4bc3-9d66-3c5059aa91f0",
  "manufacturer": "Google",
  "model": "Pixel 8",
  "android_version": "15",
  "sdk_int": 35,
  "app_version": "1.0.0",
  "pairing_token": "run-token-generated-by-odoo",
  "pairing_code": "B9361C"
}
```

### Pair success response

HTTP `200 OK`

```json
{
  "ok": true,
  "code": "run_paired",
  "message": "Run paired successfully.",
  "session_id": 123,
  "run_id": 77,
  "server_time": "2026-05-30 20:30:00",
  "pairing": {
    "status": "paired",
    "token_mode": "pairing_token",
    "code_mode": "pairing_code"
  },
  "run": {
    "id": 77,
    "name": "Test Run - SAT/26000649",
    "state": "paired",
    "pairing_code": "B9361C",
    "repair_order_id": 541,
    "repair_order_name": "SAT/26000649"
  },
  "session": {
    "id": 123,
    "device_uuid": "9a6f4e44-4f3b-4bc3-9d66-3c5059aa91f0",
    "status": "ok",
    "ping_count": 1,
    "last_ping_at": "2026-05-30 20:30:00"
  }
}
```

### Pair error examples

#### Invalid pairing token

HTTP `404 Not Found`

```json
{
  "ok": false,
  "code": "pairing_run_not_found",
  "message": "No active run matches the provided pairing token.",
  "server_time": "2026-05-30 20:30:00"
}
```

#### Run not pairable

HTTP `409 Conflict`

```json
{
  "ok": false,
  "code": "run_not_pairable",
  "message": "This run is no longer available for pairing.",
  "server_time": "2026-05-30 20:30:00"
}
```

## Ping endpoint

- Method: `POST`
- URL: `/wex/device-test/session/ping`
- Content type: `application/json`

### Ping request body

After pairing, the Android app should send `run_id` and `pairing_token` with operational requests so Odoo can associate the traffic with the active run.

Connectivity tests that only validate the server should not be polluted with stale pairing context from older runs.

Practical rule:

- "test connection" in Android should use plain device context
- operational traffic should include `run_id` and `pairing_token` only after the app is really paired

```json
{
  "device_uuid": "9a6f4e44-4f3b-4bc3-9d66-3c5059aa91f0",
  "manufacturer": "Google",
  "model": "Pixel 8",
  "android_version": "15",
  "sdk_int": 35,
  "app_version": "1.0.0",
  "run_id": 77,
  "pairing_token": "run-token-generated-by-odoo"
}
```

### Ping success response

HTTP `200 OK`

```json
{
  "ok": true,
  "code": "ping_recorded",
  "message": "Conexión correcta",
  "session_id": 123,
  "run_id": 77,
  "server_time": "2026-05-26 12:00:00",
  "run": {
    "id": 77,
    "state": "paired"
  },
  "session": {
    "id": 123,
    "device_uuid": "9a6f4e44-4f3b-4bc3-9d66-3c5059aa91f0",
    "status": "ok",
    "ping_count": 3,
    "last_ping_at": "2026-05-26 12:00:00"
  }
}
```

## Diagnostic endpoint

- Method: `POST`
- URL: `/wex/device-test/session/diagnostic`
- Content type: `application/json`

### Diagnostic request body

```json
{
  "device_uuid": "9a6f4e44-4f3b-4bc3-9d66-3c5059aa91f0",
  "manufacturer": "Google",
  "model": "Pixel 8",
  "android_version": "15",
  "sdk_int": 35,
  "app_version": "1.0.0",
  "run_id": 77,
  "pairing_token": "run-token-generated-by-odoo",
  "diagnostic": {
    "battery_level": 58,
    "network_type": "wifi",
    "storage_free_mb": 24512,
    "storage_total_mb": 512000,
    "warnings": [
      {
        "message": "Battery saver active",
        "technical_details": "System power saving mode is enabled."
      }
    ]
  }
}
```

### Diagnostic success response

HTTP `200 OK`

```json
{
  "ok": true,
  "code": "diagnostic_recorded",
  "message": "Diagnóstico recibido correctamente",
  "session_id": 123,
  "run_id": 77,
  "server_time": "2026-05-26 12:00:00",
  "run": {
    "id": 77,
    "state": "paired"
  },
  "session": {
    "id": 123,
    "device_uuid": "9a6f4e44-4f3b-4bc3-9d66-3c5059aa91f0",
    "status": "ok",
    "last_diagnostic_at": "2026-05-26 12:00:00",
    "battery_level": 58,
    "network_type": "wifi",
    "storage_free_mb": 24512,
    "storage_total_mb": 512000
  }
}
```

## Test result endpoint

- Method: `POST`
- URL: `/wex/device-test/session/result`
- Content type: `application/json`

### Test result request body

```json
{
  "device_uuid": "9a6f4e44-4f3b-4bc3-9d66-3c5059aa91f0",
  "manufacturer": "Google",
  "model": "Pixel 8",
  "android_version": "15",
  "sdk_int": 35,
  "app_version": "1.0.0",
  "run_id": 77,
  "pairing_token": "run-token-generated-by-odoo",
  "result": {
    "test_type": "speaker",
    "status": "confirmed_ok",
    "message": "Speaker test confirmed by user.",
    "technical_details": "Audio tone played and confirmed.",
    "measurements": {
      "channel": "speaker",
      "volume": 80
    }
  }
}
```

### Test result success response

HTTP `200 OK`

```json
{
  "ok": true,
  "code": "test_result_recorded",
  "message": "Resultado de altavoz recibido correctamente",
  "session_id": 123,
  "run_id": 77,
  "server_time": "2026-05-27 12:00:00",
  "run": {
    "id": 77,
    "state": "in_progress"
  },
  "result": {
    "id": 456,
    "test_type": "speaker",
    "status": "confirmed_ok",
    "executed_at": "2026-05-27 12:00:00"
  },
  "session": {
    "id": 123,
    "device_uuid": "9a6f4e44-4f3b-4bc3-9d66-3c5059aa91f0",
    "status": "ok",
    "last_test_at": "2026-05-27 12:00:00",
    "last_battery_temperature_c": null,
    "last_thermal_status": null
  }
}
```

## QR payload

The QR should not contain business logic. It should only transport enough data for the APK to bootstrap the same pairing flow that can also be completed manually.

The QR is a transport for pairing bootstrap, not a second protocol.

### Recommended QR JSON payload

```json
{
  "type": "wex_device_test_pairing",
  "version": 1,
  "base_url": "https://odoo.wexplay.local",
  "pairing_token": "run-token-generated-by-odoo",
  "pairing_code": "B9361C",
  "repair_order_ref": "SAT/26000649",
  "run_id": 77
}
```

### Current Odoo generation rules

The current Odoo implementation generates the QR from the repair order test flow using:

- one QR for APK download
- one QR for repair pairing when a run is active

The pairing QR is rendered from a JSON payload serialized by Odoo and encoded in the native barcode route:

- `/report/barcode/QR/<value>?width=<w>&height=<h>`

### QR field meaning

- `type`: fixed discriminator so the APK can reject unrelated QR codes
- `version`: payload version for future compatibility
- `base_url`: base URL the APK should use for API calls in that environment
- `pairing_token`: main key for secure pairing
- `pairing_code`: short operator-friendly fallback
- `repair_order_ref`: optional visual confirmation for the technician
- `run_id`: optional hint that can help UI confirmation, but should not replace token validation

### Base URL rule

`base_url` should be the technician-reachable Odoo base URL for that environment.

It should not silently degrade to `localhost` when the Android device is expected to call Odoo through the LAN or a public HTTPS URL.

Current project rule:

- prefer `wex_device_test.public_base_url` when configured
- use `web.base.url` only as fallback
- if `web.base.url` points to `localhost`, the environment is not suitable for QR bootstrap unless the value is overridden

## Manual fallback pairing

If QR scanning is not available, the APK should still allow:

- manual `base_url`
- manual `pairing_token`
- optional manual `pairing_code`

The backend contract remains exactly the same.

### Operator-facing distinction

During validation, technicians confused:

- the short `pairing_code`
- the long `pairing_token`

Therefore both Odoo and Android should keep a clear visual distinction:

- short operator code
- technical token

## Shared state expected by both sides

After a successful pairing, both Odoo and the APK should reason with the same minimal state:

- `session_id`
- `run_id`
- `pairing_token`
- `run.state`
- `repair_order_name`
- `device_uuid`

The APK should persist those values locally until the run is completed or explicitly reset.

In the current Android implementation, that local state also drives dashboard summaries and test navigation context.

## Supported test types and statuses

- `speaker`: `pending`, `played`, `confirmed_ok`, `confirmed_fail`, `error`
- `earpiece`: `pending`, `played`, `confirmed_ok`, `confirmed_fail`, `error`
- `proximity`: `available`, `not_available`, `detected`, `not_detected`, `error`
- `accelerometer`: `available`, `not_available`, `detected`, `not_detected`, `error`
- `gyroscope`: `available`, `not_available`, `detected`, `not_detected`, `error`
- `thermal_info`: `available`, `not_available`, `error`

## Common error responses

### Missing token

HTTP `401 Unauthorized`

```json
{
  "ok": false,
  "code": "missing_bearer_token",
  "message": "Missing Bearer token.",
  "server_time": "2026-05-26 12:00:00"
}
```

### Invalid token

HTTP `403 Forbidden`

```json
{
  "ok": false,
  "code": "invalid_api_token",
  "message": "Invalid API token.",
  "server_time": "2026-05-26 12:00:00"
}
```

### Invalid payload

HTTP `400 Bad Request`

```json
{
  "ok": false,
  "code": "invalid_payload",
  "message": "Field 'device_uuid' is required.",
  "server_time": "2026-05-26 12:00:00"
}
```

### Invalid JSON

HTTP `400 Bad Request`

```json
{
  "ok": false,
  "code": "invalid_json_payload",
  "message": "Invalid JSON payload.",
  "server_time": "2026-05-26 12:00:00"
}
```

### Server not configured

HTTP `503 Service Unavailable`

```json
{
  "ok": false,
  "code": "token_not_configured",
  "message": "Device test API token is not configured.",
  "server_time": "2026-05-26 12:00:00"
}
```

## Stability rules

- `message` remains human-readable and suitable for direct display.
- `code` is the stable field intended for app-side branching.
- `session_id` remains stable and should keep backward compatibility.
- `run_id` becomes the stable functional anchor for one concrete review.
- `pairing_token` is the primary pairing credential.
- `pairing_code` is a fallback operator code and should not replace token validation.
- Additional keys under `run` and `session` may grow in later iterations.
- `diagnostic` remains a dedicated object.
- `result` remains a dedicated object.

## Current implementation notes

These notes are not protocol guarantees, but they describe the implementation already built and validated during the current phase:

- Odoo already generates QR images inside the repair order test flow
- Odoo already exposes a configurable `wex_device_test.public_base_url`
- Android already supports QR scanning as a dependency-based feature
- Android already persists pairing state locally
- Android dashboard and tests UI are under active UX iteration and should not be treated as frozen contract
