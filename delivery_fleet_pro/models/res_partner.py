from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = "res.partner"

    delivery_preferred_from = fields.Float(string="Preferred Delivery From", help="Local time in decimal hours.")
    delivery_preferred_to = fields.Float(string="Preferred Delivery To", help="Local time in decimal hours.")
    delivery_instructions = fields.Text(string="Delivery Instructions")
    delivery_latitude = fields.Float(string="Delivery Latitude", digits=(10, 7))
    delivery_longitude = fields.Float(string="Delivery Longitude", digits=(10, 7))
    delivery_geocoded = fields.Boolean(default=False)
    delivery_geocode_accuracy = fields.Selection(
        [("rooftop", "Rooftop"), ("range", "Range"), ("street", "Street"), ("city", "City"), ("approximate", "Approximate")]
    )
    delivery_service_type_id = fields.Many2one("delivery.service.type", string="Preferred Delivery Service")
    delivery_sla_id = fields.Many2one("delivery.sla", string="Delivery SLA")
    delivery_zone_id = fields.Many2one("delivery.zone", string="Delivery Zone")
    delivery_access_notes = fields.Text()
    delivery_door_code = fields.Char(groups="delivery_fleet_pro.group_delivery_fleet_manager")
    delivery_tracking_opt_out = fields.Boolean(default=False)
    delivery_route_line_ids = fields.One2many("delivery.route.line", "partner_id", readonly=True)
    delivery_stop_count = fields.Integer(compute="_compute_delivery_stop_count")

    @api.depends("delivery_route_line_ids")
    def _compute_delivery_stop_count(self):
        for partner in self:
            partner.delivery_stop_count = len(partner.delivery_route_line_ids)

    @api.constrains("delivery_preferred_from", "delivery_preferred_to", "delivery_latitude", "delivery_longitude")
    def _check_delivery_preferences(self):
        for partner in self:
            if partner.delivery_preferred_from < 0 or partner.delivery_preferred_from > 24:
                raise ValidationError(_("Preferred delivery start must be between 0 and 24 hours."))
            if partner.delivery_preferred_to < 0 or partner.delivery_preferred_to > 24:
                raise ValidationError(_("Preferred delivery end must be between 0 and 24 hours."))
            if partner.delivery_preferred_from and partner.delivery_preferred_to and partner.delivery_preferred_from > partner.delivery_preferred_to:
                raise ValidationError(_("Preferred delivery start must be before the end."))
            if not -90 <= partner.delivery_latitude <= 90:
                raise ValidationError(_("Delivery latitude must be between -90 and 90."))
            if not -180 <= partner.delivery_longitude <= 180:
                raise ValidationError(_("Delivery longitude must be between -180 and 180."))
