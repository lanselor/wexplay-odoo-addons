# Wexplay Repair Decision Log

## 2026-04 Phase 0-1

### Keep `wexplay_repair` as SAT base module

Decision:
- Do not split the module yet.

Reason:
- `wexplay_repair_workflow` and `wexplay_repair_delivery` already depend on this module as their functional base.
- A structural split now would increase migration and regression risk.

### Make manifests more explicit, but avoid forced ecosystem reshaping

Decision:
- Clean obvious manifest issues now.
- Do not force new addon installation paths in this phase unless the dependency is unquestionably hard and safe to enforce.

Reason:
- The current goal is stabilization, not reorganization.
- Forcing a new dependency too early may break update paths in active databases.

### Keep QZ printing as documented latent coupling for now

Decision:
- Document `wexplay_sat_print` as a runtime integration not yet hardened in `depends`.

Reason:
- `wexplay_repair` references QZ client action tags directly.
- That coupling is real.
- Hardening it in `depends` needs a conscious product decision because it changes installation requirements.

### DMS remains in the base module for now

Decision:
- Keep SAT DMS helpers in `wexplay_repair` during this phase.

Reason:
- They are already consumed as shared SAT infrastructure.
- Moving them now would mix architectural cleanup with functional refactor.

### Sequence hook is accepted as technical debt, not as target behavior

Decision:
- Leave `post_init_hook` unchanged in this phase.

Reason:
- It is installation-sensitive.
- The current phase should not alter setup behavior.
- It is explicitly tracked as debt for a later hardening phase.
