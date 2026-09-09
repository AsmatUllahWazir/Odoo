from odoo import api, fields, models, _
from odoo.exceptions import UserError


class DeliveryGeocodeWizard(models.TransientModel):
    _name = "delivery.geocode.wizard"
    _description = "Geocode Delivery Addresses"

    partner_ids = fields.Many2many("res.partner", string="Customers")
    overwrite_existing = fields.Boolean(default=False)
    provider = fields.Selection(
        [("manual", "Manual"), ("openrouteservice", "OpenRouteService"), ("google", "Google")],
        default="manual",
        required=True,
    )
    default_latitude = fields.Float()
    default_longitude = fields.Float()
    note = fields.Text()

    @api.onchange("partner_ids")
    def _onchange_partners(self):
        if not self.partner_ids:
            return
        missing = self.partner_ids.filtered(lambda p: not p.delivery_latitude or not p.delivery_longitude)
        self.note = _("%s selected customers are missing coordinates.") % len(missing)

    def action_apply(self):
        self.ensure_one()
        if not self.partner_ids:
            raise UserError(_("Select at least one customer."))
        if self.provider != "manual":
            raise UserError(_("External geocoding must be connected to a provider endpoint before it can be executed."))
        for partner in self.partner_ids:
            if self.overwrite_existing or not (partner.delivery_latitude or partner.delivery_longitude):
                partner.write({"delivery_latitude": self.default_latitude, "delivery_longitude": self.default_longitude, "delivery_geocoded": True, "delivery_geocode_accuracy": "approximate"})
        return True
