import re
from urllib.parse import quote

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class DeliveryCarrier(models.Model):
    _inherit = "delivery.carrier"

    delivery_type = fields.Selection(
        selection_add=[("mrw", "MRW")],
        ondelete={"mrw": "set default"},
    )
    mrw_config_id = fields.Many2one(
        comodel_name="mrw.shipping.config",
        string="Configuración MRW",
        domain="[('active', '=', True)]",
        ondelete="restrict",
        copy=False,
    )
    mrw_service_id = fields.Many2one(
        comodel_name="mrw.shipping.service",
        string="Servicio MRW",
        domain="[('active', '=', True)]",
        ondelete="restrict",
        copy=False,
    )
    mrw_label_on_send = fields.Boolean(
        string="Obtener etiqueta MRW al enviar",
        default=True,
        help=(
            "If enabled, the MRW label will be requested immediately after the "
            "shipment is created from a delivery order."
        ),
    )

    @api.constrains("delivery_type", "mrw_config_id", "mrw_service_id")
    def _check_mrw_carrier_configuration(self):
        for carrier in self.filtered(lambda record: record.delivery_type == "mrw"):
            if not carrier.mrw_config_id:
                raise ValidationError(_("MRW carriers require an MRW configuration."))
            if not carrier.mrw_service_id:
                raise ValidationError(_("MRW carriers require an MRW service."))

    @api.constrains("delivery_type", "company_id", "mrw_config_id")
    def _check_mrw_config_company(self):
        for carrier in self.filtered(lambda record: record.delivery_type == "mrw"):
            if (
                carrier.company_id
                and carrier.mrw_config_id
                and carrier.mrw_config_id.company_id != carrier.company_id
            ):
                raise ValidationError(
                    _("The MRW configuration must belong to the carrier company.")
                )

    @api.constrains("delivery_type", "mrw_service_id")
    def _check_mrw_service_type(self):
        for carrier in self.filtered(lambda record: record.delivery_type == "mrw"):
            if (
                carrier.mrw_service_id
                and carrier.mrw_service_id.service_type
                not in ("national", "international", "both")
            ):
                raise ValidationError(_("The selected MRW service type is not valid."))

    def mrw_rate_shipment(self, order):
        self.ensure_one()
        price = order.pricelist_id._get_product_price(self.product_id, 1.0)
        return {
            "success": True,
            "price": price,
            "error_message": False,
            "warning_message": _(
                "MRW live rating is not available; using the configured delivery product price."
            ),
        }

    def mrw_send_shipping(self, pickings):
        self.ensure_one()
        results = []
        for picking in pickings:
            shipment = self._mrw_get_or_create_shipment_from_picking(picking)
            if shipment.state == "draft":
                shipment.action_prepare()
            if not shipment.mrw_shipment_number:
                shipment._send_create_shipment_to_mrw()
            self._mrw_sync_picking_shipping_data(picking, shipment)
            if shipment.state == "error" or not shipment.mrw_shipment_number:
                raise UserError(
                    shipment.last_error
                    or _("MRW did not return a shipment number for %s.") % picking.name
                )
            if self.mrw_label_on_send and not shipment.label_attachment_id:
                try:
                    shipment._get_label_from_mrw()
                except Exception as error:
                    shipment.write({"last_error": str(error)})
                    shipment._create_log(
                        operation="get_label",
                        status="error",
                        error_message=str(error),
                    )
                self._mrw_sync_picking_shipping_data(picking, shipment)
                if shipment.last_error:
                    picking.message_post(
                        body=_(
                            "MRW shipment %s was created, but the label could not be "
                            "retrieved automatically. You can retry it from the linked "
                            "MRW shipment. Error: %s"
                        )
                        % (shipment.mrw_shipment_number, shipment.last_error)
                    )
            results.append(
                {
                    "exact_price": 0.0,
                    "tracking_number": shipment.mrw_shipment_number,
                }
            )
        return results

    def mrw_get_tracking_link(self, picking):
        self.ensure_one()
        tracking_number = (
            picking.carrier_tracking_ref
            or picking.mrw_shipment_id.mrw_shipment_number
        )
        if not tracking_number:
            return False
        # Conservatively reuse the public national-history URL evidenced in the
        # legacy MRW PrestaShop tracking module until MRW confirms a newer
        # public tracking endpoint for this account.
        return "http://www.mrw.es/seguimiento_envios/MRW_historico_nacional.asp?enviament=%s" % quote(
            tracking_number
        )

    def mrw_cancel_shipment(self, pickings):
        self.ensure_one()
        for picking in pickings:
            shipment = picking.mrw_shipment_id
            if not shipment:
                raise UserError(_("No linked MRW shipment was found for %s.") % picking.name)
            before_state = shipment.state
            shipment._request_external_cancellation()
            if shipment.state != "cancelled":
                raise UserError(
                    shipment.last_error
                    or _("MRW did not confirm cancellation for %s.") % picking.name
                )
            if before_state != "cancelled":
                picking.message_post(
                    body=_("MRW shipment %s cancelled.") % shipment.mrw_shipment_number
                )

    def _mrw_get_or_create_shipment_from_picking(self, picking):
        self.ensure_one()
        if self.delivery_type != "mrw":
            raise UserError(_("This delivery carrier is not configured as MRW."))
        if not self.mrw_config_id:
            raise UserError(_("MRW configuration is required on the delivery carrier."))
        if not self.mrw_service_id:
            raise UserError(_("MRW service is required on the delivery carrier."))
        self._mrw_check_picking_can_be_sent(picking)
        if picking.mrw_shipment_id:
            return picking.mrw_shipment_id
        if picking.carrier_tracking_ref:
            return self._mrw_link_existing_tracking_to_picking(picking)
        shipment = self.env["mrw.shipping.shipment"].create(
            self._mrw_prepare_shipment_values_from_picking(picking)
        )
        picking.mrw_shipment_id = shipment
        return shipment

    def _mrw_link_existing_tracking_to_picking(self, picking):
        self.ensure_one()
        shipment = self.env["mrw.shipping.shipment"].create(
            {
                **self._mrw_prepare_shipment_values_from_picking(picking),
                "state": "sent",
                "mrw_shipment_number": picking.carrier_tracking_ref,
            }
        )
        self._mrw_sync_picking_shipping_data(picking, shipment)
        picking.message_post(
            body=_(
                "The delivery order already had MRW tracking %s, so Odoo linked "
                "a recovery MRW shipment instead of creating a new expedition."
            )
            % picking.carrier_tracking_ref
        )
        return shipment

    def _mrw_sync_picking_shipping_data(self, picking, shipment):
        self.ensure_one()
        values = {}
        if not picking.mrw_shipment_id:
            values["mrw_shipment_id"] = shipment.id
        if shipment.mrw_shipment_number and (
            not picking.carrier_tracking_ref
            or picking.carrier_tracking_ref != shipment.mrw_shipment_number
        ):
            values["carrier_tracking_ref"] = shipment.mrw_shipment_number
        if values:
            picking.write(values)
            # MRW shipment creation is an external irreversible side effect.
            # Persist the local audit/tracking link before any later label/UI step.
            self.env.cr.commit()

    def _mrw_check_picking_can_be_sent(self, picking):
        if picking.picking_type_code != "outgoing":
            raise UserError(
                _(
                    "MRW shipments can only be created from outgoing delivery orders. "
                    "%s is a %s transfer, so it should not be sent to MRW."
                )
                % (picking.name, picking.picking_type_id.display_name)
            )
        partner = picking.partner_id
        if not partner:
            raise UserError(_("A delivery address is required on %s.") % picking.name)
        shipment_type = self._mrw_get_shipment_type(partner)
        if (
            shipment_type == "international"
            and not self.mrw_config_id.enable_international_shipments
        ):
            raise UserError(
                _(
                    "MRW international shipments are not enabled on configuration "
                    "%s. Enable them only after validating the international TEST "
                    "flow with MRW."
                )
                % self.mrw_config_id.display_name
            )
        service_type = self.mrw_service_id.service_type
        if service_type != "both" and service_type != shipment_type:
            raise UserError(
                _(
                    "The MRW service %(service)s is configured as %(service_type)s, "
                    "but %(picking)s requires a %(shipment_type)s service."
                )
                % {
                    "service": self.mrw_service_id.display_name,
                    "service_type": service_type,
                    "picking": picking.name,
                    "shipment_type": shipment_type,
                }
            )
        missing_fields = []
        if not partner.street:
            missing_fields.append(_("street"))
        if not partner.zip:
            missing_fields.append(_("zip"))
        if not partner.city:
            missing_fields.append(_("city"))
        if not partner.country_id:
            missing_fields.append(_("country"))
        if missing_fields:
            raise UserError(
                _("The delivery address for %s is missing: %s.")
                % (picking.name, ", ".join(missing_fields))
            )
        phone = partner.mobile or partner.phone
        if not phone:
            raise UserError(_("A recipient phone is required on %s.") % picking.name)
        phone_digits = re.sub(r"\D", "", phone)
        if shipment_type == "national" and partner.country_id.code == "ES":
            if phone_digits.startswith("0034") and len(phone_digits) == 13:
                phone_digits = phone_digits[-9:]
            elif phone_digits.startswith("34") and len(phone_digits) == 11:
                phone_digits = phone_digits[-9:]
            if len(phone_digits) != 9:
                raise UserError(
                    _(
                        "The recipient phone for %s must be a Spanish 9-digit "
                        "number, optionally prefixed with +34."
                    )
                    % picking.name
                )
        elif len(phone_digits) < 6:
            raise UserError(
                _("The recipient phone for %s is too short for MRW.") % picking.name
            )

    def _mrw_prepare_shipment_values_from_picking(self, picking):
        self.ensure_one()
        partner = picking.partner_id
        if not partner:
            raise UserError(_("A delivery address is required on %s.") % picking.name)
        if not partner.country_id:
            raise UserError(_("A destination country is required on %s.") % picking.name)
        shipment_type = self._mrw_get_shipment_type(partner)
        return {
            "source": "picking",
            "picking_id": picking.id,
            "carrier_id": self.id,
            "company_id": picking.company_id.id,
            "config_id": self.mrw_config_id.id,
            "service_id": self.mrw_service_id.id,
            "shipment_type": shipment_type,
            "partner_id": partner.id,
            "recipient_name": partner.name,
            "recipient_phone": partner.mobile or partner.phone,
            "recipient_vat": partner.vat,
            "street": partner.street,
            "street2": partner.street2,
            "zip": partner.zip,
            "city": partner.city,
            "country_id": partner.country_id.id,
            "state_id": partner.state_id.id,
            "reference": picking.name,
            "shipping_date": fields.Date.context_today(picking),
            "package_ids": self._mrw_prepare_package_commands_from_picking(picking),
        }

    def _mrw_get_shipment_type(self, partner):
        company_country = self.mrw_config_id.company_id.country_id
        if company_country and partner.country_id == company_country:
            return "national"
        if partner.country_id.code == "ES":
            return "national"
        return "international"

    def _mrw_prepare_package_commands_from_picking(self, picking):
        packages = picking.move_line_ids.mapped("result_package_id")
        commands = []
        sequence = 1
        for package in packages:
            package_type = package.package_type_id
            weight = package.shipping_weight or package._get_weight(picking.id)
            if weight <= 0:
                raise UserError(_("Package weight must be greater than zero."))
            commands.append(
                (
                    0,
                    0,
                    {
                        "sequence": sequence,
                        "weight": weight,
                        "height": package_type.height or 1,
                        "width": package_type.width or 1,
                        "length": package_type.packaging_length or 1,
                        "dimension_code": "3",
                        "internal_reference": package.name or _("Package %s") % sequence,
                    },
                )
            )
            sequence += 1
        if commands:
            return commands

        weight = picking.shipping_weight or picking.weight_bulk or picking.weight
        if weight <= 0:
            raise UserError(
                _(
                    "The delivery order %s has no shipping weight. Set product "
                    "weights or a package weight before sending it to MRW."
                )
                % picking.name
            )
        return [
            (
                0,
                0,
                {
                    "sequence": 1,
                    "weight": weight,
                    "height": 1,
                    "width": 1,
                    "length": 1,
                    "dimension_code": "3",
                    "internal_reference": picking.name,
                },
            )
        ]
