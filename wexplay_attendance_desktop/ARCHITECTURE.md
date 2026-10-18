# Wexplay Attendance Desktop

## Specification — 2026-10-18

Approved in conversation: an attendance card in the bottom right of the apps
desktop, with clear state, entry time, today's hours and a large entry/exit
button. Width adapts from compact desktops to large screens. Mobile uses the
available width. It must coexist with update notes and retain Wexplay styling.

Users: internal users with a linked employee and native systray attendance
enabled for that employee's company. No new roles, models or data migrations.
No portal, kiosk, payroll, attendance corrections or history in this iteration.

Acceptance: correct checked-in/out state; native attendance records; no duplicate
clicks during requests; explicit success/error; refresh on reopening/focus and
periodically while visible; native top button remains synchronized; notes and
apps remain accessible on small screens. Functional acceptance was confirmed
by the user on 2026-10-18: the feature works correctly and is accepted. The
confirmation does not identify a production rollout.

## ADR — separate integration and native attendance

The customizer remains independent of HR. This optional module depends on both
the customizer and `hr_attendance`, and extends the OCA AppsMenu template through
OWL inheritance. No OCA or core files are edited.

The frontend service owns request serialization and display state for the card
and native systray action. Both use Odoo 18's authenticated attendance routes,
which resolve `request.env.user.employee_id`. No employee ID is accepted from
the browser and no new sudo, ACL or backend business rule is introduced.
Native company eligibility (`display_systray`) is respected. Geolocation follows
the native best-effort behavior, including a timeout and fallback without GPS.

Before a toggle, fresh employee/state is compared with the displayed state after
location acquisition. A changed state asks the user to review and click again.
The server's toggle response is authoritative; no optimistic success is shown.
On an ambiguous network failure the UI requires a read refresh before another
toggle. A shared busy flag protects both controls within the same web client.
Separate clients still use the native toggle endpoint and its concurrency
semantics; this module does not introduce server-wide idempotency.

The service syncs the native systray through an internal bus event. The card
refreshes on mount, focus, visibility recovery and every minute while visible.
Hours are server values, not an independently calculated attendance duration.

## Files and implementation plan

- `__init__.py`, `__manifest__.py`: module loading and explicit dependencies.
- `attendance_service.js`: `refresh`, `signInOut`, `_getPosition`, `_setEmployee`;
  native route calls, serialized actions and user feedback.
- `attendance_card.js`, `.xml`: lifecycle, formatting and accessible card.
- `attendance_sync.js`: register card on AppsMenu, share native systray actions.
- `attendance_card.scss`: scoped colors and responsive layout. The card is in
  document flow on narrow/short screens; update notes also enter normal flow.

Implement service, then UI/integration, then static/runtime checks and review.
Verify on test: first entry, exit, repeated clicks, existing entries today,
no employee, disabled systray, company switch, denied location, network failure,
native button, another tab, edit mode, notes, mobile and large resolution.

## Validation — 2026-10-18

- Python manifest/XML syntax, JavaScript syntax and SCSS compilation passed.
- Nine automated service tests passed: entry/exit, shared lock, changed employee/
  state/session/eligibility, ambiguous failure, invalid response, ineligible
  users, stale native state, concurrent refreshes and denied geolocation.
- Installed in a new isolated Odoo 18 database, without changing the usual test
  or production databases. Browser tests passed with both debug and compiled
  assets: real entry/exit, bidirectional native button synchronization, company
  option disabled, user without employee, ordinary internal user, failed read
  and recovery, notes without overlap and five viewport sizes (390–1920 px).
- Inspected desktop and mobile screenshots. On 2026-10-18 the user confirmed
  that the feature works correctly and accepted this version. This closes
  functional acceptance; the confirmation does not establish individual
  company-switching/device test results or a production deployment.
- Rapid automated toggles within the same second exposed native attendance
  ordering ambiguity; browser scenarios space separate successful operations
  by over one second. No native attendance model changes are introduced.

## Functional acceptance — 2026-10-18

The user confirmed: “Funciona bien, lo damos por bueno.” This version is accepted
and documented as active. No additional functional changes are requested.
Documentation closure preserves the earlier automated/browser evidence and the
native concurrency limits described above.
