import math
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class DeliveryGeocodeCache(models.Model):
    _name = "delivery.geocode.cache"
    _description = "Delivery Geocoding Cache"
    _order = "write_date desc"

    name = fields.Char(required=True)
    normalized_address = fields.Char(required=True, index=True)
    street = fields.Char()
    street2 = fields.Char()
    city = fields.Char()
    zip = fields.Char()
    state_id = fields.Many2one("res.country.state")
    country_id = fields.Many2one("res.country")
    latitude = fields.Float(digits=(10, 7))
    longitude = fields.Float(digits=(10, 7))
    accuracy = fields.Selection(
        [("rooftop", "Rooftop"), ("range", "Range"), ("street", "Street"), ("city", "City"), ("approximate", "Approximate")],
        default="approximate",
    )
    provider = fields.Selection(
        [("manual", "Manual"), ("openrouteservice", "OpenRouteService"), ("google", "Google")],
        default="manual",
    )
    provider_reference = fields.Char()
    active = fields.Boolean(default=True)
    notes = fields.Text()

    _sql_constraints = [("normalized_address_unique", "unique(normalized_address)", "This normalized address is already cached.")]

    @api.constrains("latitude", "longitude")
    def _check_coordinates(self):
        for record in self:
            if not -90 <= record.latitude <= 90 or not -180 <= record.longitude <= 180:
                raise ValidationError(_("Invalid geographic coordinates."))

    @api.model
    def normalize(self, partner):
        values = [partner.street, partner.street2, partner.city, partner.zip, partner.state_id.name, partner.country_id.name]
        return ", ".join(value.strip().lower() for value in values if value and value.strip())

    @api.model
    def get_for_partner(self, partner):
        normalized = self.normalize(partner)
        return self.search([("normalized_address", "=", normalized), ("active", "=", True)], limit=1)

    @api.model
    def haversine_km(self, lat1, lon1, lat2, lon2):
        radius = 6371.0
        p1 = math.radians(lat1)
        p2 = math.radians(lat2)
        dp = math.radians(lat2 - lat1)
        dl = math.radians(lon2 - lon1)
        a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
        return radius * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
