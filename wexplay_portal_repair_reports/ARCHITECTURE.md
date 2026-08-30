# Wexplay Portal Repair Reports - Architecture

## Purpose

`wexplay_portal_repair_reports` provides B2B customers with an on-demand
technical report from an authorized SAT portal page. It is a portal bridge
module: SAT content and report generation remain owned by `wexplay_repair`;
portal access and presentation remain isolated from the base SAT module.

## Dependencies and responsibilities

- `wexplay_portal` provides authenticated B2B SAT access by commercial partner.
- `wexplay_repair_images` provides the SAT photographs already available to
  the company through the portal.
- `wexplay_portal_repair_workflow` provides the shared internal activity and
  Portal clientes dashboard infrastructure.

The module owns:

- two portal report actions: Wexplay identity and customer identity;
- the customer report identity profile per commercial partner;
- secure rendering orchestration and download UX;
- the chatter/activity trace produced after a successful render.

## Security model

- The controller searches the SAT only within the portal user's visible domain.
- It does not use `sudo()` in the controller.
- The `repair.order` helper validates portal access again before rendering or
  logging the download; privileged rendering is encapsulated after that check.
- The browser never submits image ids, arbitrary report fields or DMS ids.
- Custom logos are embedded only in the authenticated identity page or report;
  no generic image route or DMS route is exposed.

## Report generation

Each request renders a fresh PDF and returns it directly to the browser. The
PDF is not stored in DMS, attached to the SAT or cached as a portal document.
Current expected volume does not justify persistence or a queue.

### Report variants

- **Wexplay** reuses the internal SAT report body with Wexplay identity.
- **Personalized** uses a dedicated QWeb layout and paper format. It includes
  the customer identity and technical content but omits Wexplay identity, SAT
  reference, workflow status, staff names, consents and signatures.

The customer cannot alter the technical report content, add notes or change
which images are included.

### Images

Every SAT image already authorized for that portal company is included in both
variants. Videos are excluded. This deliberately avoids a new selection task
for technicians and avoids giving portal users a DMS-level image selector.
Each image has its own framed evidence page, using the available area without
cropping or forcing smaller images to scale up.

## Customer identity

There is one `wex.portal.sat.report.brand` profile per commercial partner. It
can use billing data or custom data, plus a custom logo and a validated single
hexadecimal corporate color. CSS, arbitrary templates and free-form report
layout changes are intentionally out of scope.

The identity form displays the saved custom logo and previews a newly selected
image locally before save. The browser does not upload the replacement until
the customer submits the form.

## Download experience and traceability

The frontend fetches the PDF so it can show `Generando informe`, display a
spinner, disable both report buttons and prevent duplicate clicks. On success,
the browser starts the normal file download; errors restore the actions and
show feedback.

## Custom logo validation

Custom report logos are validated from their binary content, not their file
extension or browser MIME type. The portal accepts PNG, JPEG and WebP uploads
up to 6 MB, rejects corrupted or oversized source images, and stores a static
PNG normalized proportionally within 1024 x 768 px.

After the PDF is rendered successfully, the module:

- creates a `wex.portal.repair.event` of type `report_downloaded` with its
  variant;
- posts an internal `repair.order` chatter message identifying the portal user
  and report variant;
- leaves the event as done because it is traceability, not pending work.

The dashboard can therefore show report downloads by period and activity
without adding a parallel audit model.

## Deliberate limits

- No report persistence in DMS for portal downloads.
- No portal editing of report notes or technical content.
- No user-selected image list.
- No public route, token flow or B2C use.
- No client-defined CSS, templates or unrestricted branding rules.
