# Implementation plan

Date: 2026-10-18. Authorized by user. Based on repository SPEC, architecture and
execution-plan templates. External acceptance remains pending as listed in SPEC.

## Files and responsibilities
- __manifest__.py, __init__.py: dependency/loading and native provider lifecycle.
- const.py, utils.py: fixed protocol endpoints, bounded decoding and SHA256 signing.
- models/payment_provider.py: configuration validation, EUR/cards, secret access.
- models/payment_transaction.py: sequence reference, render hook, validation/states.
- controllers/main.py: thin POST webhook and GET browser return.
- views/payment_provider_views.xml: native provider form extension.
- views/payment_templates.xml: redirect form without card inputs.
- data/payment_provider_data.xml: disabled provider and reference sequence.
- tests/test_redsys.py: protocol/security, state transitions and native processing.
- README.md, CHANGELOG.md, ARCHITECTURE.md, docs/: operational documentation.

## Relevant methods
Provider: _get_default_payment_method_codes, _get_supported_currencies,
_redsys_check_configuration, _redsys_get_api_url.
Transaction: _compute_reference, _get_specific_rendering_values,
_redsys_prepare_payment_parameters, _get_tx_from_notification_data,
_redsys_check_notification, _process_notification_data.

## Sequence and effort
1. Installable disabled provider/configuration: small.
2. Redirect and signing plus authenticated callback: medium.
3. Isolated database installation and security/accounting tests: medium.
4. Documentation and diff review: small.
5. External sandbox acceptance after URL/terminal configuration: pending.

## Test plan
Fixed external signature vector; malformed base64/JSON/duplicate keys; forged
signature; mismatched semantic fields; valid decline; duplicate success; stale
decline after success; EUR/positive-only; no tokens; restricted secret; isolated
installation and native payment/invoice reconciliation. Native quotation and
invoice token flow must be accepted in the public sandbox before production.

Rollback: disable and unpublish. Never uninstall to remove financial history.
