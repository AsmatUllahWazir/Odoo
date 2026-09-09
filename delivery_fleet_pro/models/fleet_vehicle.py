from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class FleetVehicle(models.Model):
    _inherit = "fleet.vehicle"

    delivery_capacity_weight = fields.Float(string="Delivery Capacity (kg)")
    delivery_capacity_volume = fields.Float(string="Delivery Capacity (m³)")
    delivery_capacity_packages = fields.Integer(string="Package Capacity")
    delivery_status = fields.Selection(
        [
            ("available", "Available"),
            ("assigned", "Assigned"),
            ("in_transit", "In Transit"),
            ("maintenance", "Maintenance"),
            ("inactive", "Inactive"),
        ],
        default="available",
        string="Delivery Status",
    )
    delivery_home_depot_id = fields.Many2one("stock.warehouse", string="Home Depot")
    delivery_driver_license_required = fields.Boolean()
    delivery_refrigerated = fields.Boolean()
    delivery_hazardous_allowed = fields.Boolean()
    delivery_height_m = fields.Float()
    delivery_length_m = fields.Float()
    delivery_width_m = fields.Float()
    delivery_fuel_type = fields.Selection(
        [("petrol", "Petrol"), ("diesel", "Diesel"), ("hybrid", "Hybrid"), ("electric", "Electric"), ("other", "Other")]
    )
    delivery_fuel_consumption = fields.Float(string="Fuel Consumption (L/100 km)")
    delivery_cost_per_hour = fields.Monetary()
    delivery_cost_per_km = fields.Monetary()
    delivery_route_ids = fields.One2many("delivery.route", "vehicle_id", readonly=True)
    delivery_route_count = fields.Integer(compute="_compute_delivery_route_count")
    delivery_current_route_id = fields.Many2one("delivery.route", compute="_compute_current_route")
    currency_id = fields.Many2one("res.currency", related="company_id.currency_id", store=True)

    @api.depends("delivery_route_ids.state")
    def _compute_current_route(self):
        active_states = ("planned", "dispatched", "in_transit")
        for vehicle in self:
            vehicle.delivery_current_route_id = vehicle.delivery_route_ids.filtered(lambda r: r.state in active_states)[:1]

    @api.depends("delivery_route_ids")
    def _compute_delivery_route_count(self):
        for vehicle in self:
            vehicle.delivery_route_count = len(vehicle.delivery_route_ids)

    @api.constrains("delivery_capacity_weight", "delivery_capacity_volume", "delivery_capacity_packages", "delivery_cost_per_hour", "delivery_cost_per_km")
    def _check_delivery_capacity(self):
        for vehicle in self:
            if vehicle.delivery_capacity_weight < 0 or vehicle.delivery_capacity_volume < 0 or vehicle.delivery_capacity_packages < 0:
                raise ValidationError(_("Vehicle delivery capacities cannot be negative."))
            if vehicle.delivery_cost_per_hour < 0 or vehicle.delivery_cost_per_km < 0:
                raise ValidationError(_("Vehicle delivery costs cannot be negative."))
