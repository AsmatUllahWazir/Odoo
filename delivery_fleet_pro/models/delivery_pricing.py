from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class DeliveryPricingRule(models.Model):
    _name = "delivery.pricing.rule"
    _description = "Delivery Pricing Rule"
    _order = "sequence, id"

    name = fields.Char(required=True)
    code = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company)
    service_type_id = fields.Many2one("delivery.service.type")
    zone_id = fields.Many2one("delivery.zone")
    min_weight = fields.Float()
    max_weight = fields.Float()
    min_distance = fields.Float()
    max_distance = fields.Float()
    base_fee = fields.Monetary()
    per_km_fee = fields.Monetary()
    per_kg_fee = fields.Monetary()
    per_stop_fee = fields.Monetary()
    fuel_surcharge_percent = fields.Float()
    currency_id = fields.Many2one("res.currency", related="company_id.currency_id", store=True)
    notes = fields.Text()

    _sql_constraints = [("pricing_code_company_unique", "unique(company_id, code)", "Pricing rule code must be unique per company.")]

    @api.constrains("min_weight", "max_weight", "min_distance", "max_distance", "fuel_surcharge_percent")
    def _check_ranges(self):
        for rule in self:
            if rule.max_weight and rule.max_weight < rule.min_weight:
                raise ValidationError(_("Maximum weight must be greater than minimum weight."))
            if rule.max_distance and rule.max_distance < rule.min_distance:
                raise ValidationError(_("Maximum distance must be greater than minimum distance."))
            if rule.fuel_surcharge_percent < 0:
                raise ValidationError(_("Fuel surcharge cannot be negative."))

    def matches(self, route, line=None):
        self.ensure_one()
        weight = line.weight if line else route.total_weight
        distance = route.actual_distance or route.estimated_distance
        if self.service_type_id and route.service_type_id != self.service_type_id:
            return False
        if self.zone_id and route.zone_id != self.zone_id:
            return False
        if weight < self.min_weight:
            return False
        if self.max_weight and weight > self.max_weight:
            return False
        if distance < self.min_distance:
            return False
        if self.max_distance and distance > self.max_distance:
            return False
        return True

    def calculate(self, route, line=None):
        self.ensure_one()
        weight = line.weight if line else route.total_weight
        distance = route.actual_distance or route.estimated_distance
        stops = 1 if line else route.stop_count
        subtotal = self.base_fee + distance * self.per_km_fee + weight * self.per_kg_fee + stops * self.per_stop_fee
        return subtotal * (1 + self.fuel_surcharge_percent / 100.0)
