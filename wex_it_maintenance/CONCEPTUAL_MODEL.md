# Wex IT Maintenance - Conceptual Model

## Why this document exists

The current implementation uses the word `service` in a broad way. That creates ambiguity because Wexplay uses several different concepts that can sound similar but have different operational meaning.

This document defines the target vocabulary before changing models or views.

## Core distinction

### Odoo product

An Odoo product is the thing that can be sold, quoted or invoiced.

Example:
- `[SRV-MNT-GEN-000009] [GTS] Servicio de Mantenimiento Preventivo y Correctivo a empresas (hasta 3 equipos)`

This belongs to the commercial/catalog layer.

It should not be duplicated per customer.

### IT product configuration

Some Odoo products may need an IT maintenance configuration.

Target idea:
- add an `IT Service` or equivalent checkbox on the product
- show an IT-specific configuration tab when enabled
- define standard templates or coverage rules there

This follows the same conceptual pattern Odoo uses with product options such as Sales, Purchase, Point of Sale or Expenses.

Example:
- product: `[GTS] Maintenance up to 3 devices`
- IT configuration:
  - covered devices: 3
  - standard service template
  - suggested checklist
  - suggested visit frequency

### Customer IT coverage

This is the concrete application of a sold/configured product to a customer.

Example:
- `Customer A - GTS Maintenance up to 3 devices`

This should relate commercial Odoo documents with the IT maintenance workspace.

Possible future links:
- customer
- Odoo product
- sale order line
- invoice line
- start/end/renewal dates
- covered assets
- standard service template applied to the customer

This concept does not currently exist as a dedicated model.

## Target operating concepts

### IT services

IT services represent actions or responsibilities Wexplay should perform.

Examples:
- maintenance/review of computers
- maintenance/review of Android devices
- domain review
- backup verification
- preventive maintenance
- corrective maintenance
- support tasks

This answers:

`What work is Wexplay responsible for doing or checking?`

### Software and licensing

Software/licensing represents programs, platforms, licenses, subscriptions and renewals.

Examples:
- Microsoft 365
- Windows
- business management software
- antivirus
- Thunderbird
- domain renewal
- backup license

This answers:

`What software or license exists, who manages it, and when does it renew?`

Important distinction:
- Microsoft 365 is not a credential.
- Microsoft 365 is software/licensing or a managed platform.
- the admin login for Microsoft 365 is a credential linked to that software/platform.

Thunderbird is usually different:
- if it is just installed on a workstation, it may be software installed on an asset
- if it needs no renewal or central management, it does not need the same weight as Microsoft 365

### Networks

Networks represent connectivity and network infrastructure.

Examples:
- VPN
- firewall
- router
- switches
- Wi-Fi
- VLANs
- IP plan
- cabling
- NAT/ports

This answers:

`How is the customer's connectivity structured and what must Wexplay maintain or document?`

Networks may overlap with services operationally, but they deserve separate conceptual treatment because they are often critical in a business environment.

### Assets

Assets are physical or inventory-like devices.

Examples:
- workstation
- laptop
- server
- router
- switch
- NAS
- printer
- smartphone

This answers:

`What specific device exists, where is it, who uses it, and what is its history?`

### Credentials

Credentials are access data.

They should be linked to the thing they unlock:
- customer
- asset
- software/licensing
- network element
- IT service, only if that is the best available context

This answers:

`What access does Wexplay need to operate or support this customer?`

Credentials should not represent platforms themselves.

## Current implementation gap

Current model:
- `wex.it.service`

Current problem:
- it is too broad semantically
- it can be interpreted as service sold, managed service, software, renewal or platform

Target direction:
- reserve `IT services` for Wexplay responsibilities/actions
- add separate concepts for software/licensing and networks
- add a future customer coverage layer to connect Odoo products/invoices with IT maintenance

## Recommended future architecture

Future concepts to consider:
- `wex.it.coverage`
- `wex.it.service.template`
- `wex.it.customer.service`
- `wex.it.software`
- `wex.it.network`

Naming is not final. The important point is the separation of responsibilities.

## Practical rule

Before creating a record, ask:

`Is this something Wexplay sells, something Wexplay does, something installed/licensed, a network component, a physical asset, or an access credential?`

The answer determines where the record should live.
