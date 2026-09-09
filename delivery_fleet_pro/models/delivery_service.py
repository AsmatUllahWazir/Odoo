from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class DeliveryServiceType(models.Model):
    _name = "delivery.service.type"
    _description = "Delivery Service Type"
    _order = "sequence, name"

    name = fields.Char(required=True)
    code = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    description = fields.Text()
    default_service_minutes = fields.Float(default=10.0)
    requires_signature = fields.Boolean(default=True)
    requires_photo = fields.Boolean()
    requires_otp = fields.Boolean()
    allow_partial = fields.Boolean(default=True)
    allow_failed_retry = fields.Boolean(default=True)
    color = fields.Integer(default=0)

    _sql_constraints = [("code_unique", "unique(code)", "Service type code must be unique.")]


class DeliveryZone(models.Model):
    _name = "delivery.zone"
    _description = "Delivery Zone"
    _order = "sequence, name"

    name = fields.Char(required=True)
    code = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company)
    warehouse_id = fields.Many2one("stock.warehouse")
    color = fields.Integer(default=0)
    zip_prefixes = fields.Text(help="One ZIP prefix per line.")
    cities = fields.Text(help="One city per line.")
    max_stops = fields.Integer(default=50)
    max_weight = fields.Float()
    max_volume = fields.Float()
    notes = fields.Text()

    _sql_constraints = [("zone_code_company_unique", "unique(company_id, code)", "Zone code must be unique per company.")]

    def matches_partner(self, partner):
        self.ensure_one()
        zips = {line.strip().lower() for line in (self.zip_prefixes or "").splitlines() if line.strip()}
        cities = {line.strip().lower() for line in (self.cities or "").splitlines() if line.strip()}
        zip_match = any((partner.zip or "").lower().startswith(prefix) for prefix in zips) if zips else True
        city_match = (partner.city or "").lower() in cities if cities else True
        return zip_match and city_match
