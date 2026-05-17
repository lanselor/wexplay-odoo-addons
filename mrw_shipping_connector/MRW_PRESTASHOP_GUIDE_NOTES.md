# MRW PrestaShop Installation Guide Notes

Source reviewed:

```text
C:\Users\Alex\Downloads\modulo-para-Prestashop-MRW.pdf
```

Extracted text copy used for analysis:

```text
C:\Users\Alex\Downloads\modulo-para-Prestashop-MRW.txt
```

This document is not an API contract. It is an operational installation and
usage guide for MRW's official PrestaShop module, so it must only be used as
supporting evidence for workflow and configuration decisions. Endpoint names,
request XML, SOAP wrappers, and response structures must continue to come from
the PrestaShop PHP source, WSDL inspection, and live TEST logs.

## Relevant Confirmations

The guide confirms that the integration is based on MRW SAGEC accounts.
SAGEC is described as MRW's automated shipment-management service for clients.

The guide confirms that both TEST and PRO environments exist and that PRO
accounts may remain disabled until several TEST shipments have been generated
and validated.

The guide confirms these SAGEC credential/configuration fields:

- franchise code: required
- subscriber number: required
- department code: optional
- user name: required
- password: required

The guide confirms that multiple MRW subscribers can exist in the same shop and
that only one subscriber can be marked as the default. This supports our Odoo
design with multiple `mrw.shipping.config` records per company/branch and a
single default constraint per company/branch.

The guide confirms that default national and international services are chosen
at configuration level, but can be overridden for an individual shipment before
transmitting it to MRW. This supports keeping services as editable records and
copying the selected service onto each shipment.

The guide confirms that the official module can generate labels automatically
or manually, download them, and store them on the server. Our Odoo module keeps
manual actions first and stores generated labels as `ir.attachment`.

The guide confirms that MRW returns a shipment/expedition number that can be
used as the tracking reference. No separate tracking API structure is described
in the guide.

## Operational Options Mentioned

The guide mentions these operational options around an order/shipment:

- change package count before MRW transmission
- change service before MRW transmission
- change subscriber before MRW transmission
- change delivery time slot for eCommerce service
- Saturday delivery
- delivery at MRW franchise
- notification/pre-advice option
- cash-on-delivery/reimbursement test cases

Only the fields already supported by the WSDL/source/log evidence should be
implemented. The options above are useful backlog candidates, not complete API
specifications by themselves.

## Testing Guidance From The Guide

The guide recommends a test phase before production and suggests testing a
variety of shipments:

- single-package shipments
- multi-package shipments
- different destinations
- correct and incorrect addresses
- shipments with and without reimbursement
- different weights

It also says TEST can generate shipment numbers and labels, even though they
are not real production shipments. This matches the behavior already observed
in Odoo TEST validation.

## Production Rollout Guidance

The guide recommends sending several generated label PDFs to MRW Field Support
for validation before moving to production. It identifies `integracion@mrw.es`
as the support email and says the franchise should be copied when requesting
the move to PRO.

It also recommends coordinating the first PRO test shipments with the local
franchise and marking those shipments clearly as tests in reference and/or
observations so the franchise can locate and delete them.

## Not Found In The Guide

The guide does not provide:

- WSDL URLs
- SOAP endpoint URLs
- SOAP action values
- request XML structure
- response XML structure
- service-code catalog
- an API operation to list available services
- tracking API operation or payload
- cancellation API operation or payload
- label binary/base64 technical format
- phone-number formatting rules

## Design Impact For Odoo

The guide strengthens these existing design decisions:

- Keep TEST-only safeguards until the production go-live process is explicit.
- Keep multiple configurations/subscribers, with one default per company/branch.
- Keep service records editable and configurable rather than hardcoded in logic.
- Keep manual preview/send/get-label actions while the connector is still being
  validated.
- Keep technical logs and label attachments, because MRW may ask for generated
  PDFs during validation.
- Build a future validation checklist before enabling production calls.

