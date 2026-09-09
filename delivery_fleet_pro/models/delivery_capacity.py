from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class DeliveryCapacityCheck(models.Model):
    _name = "delivery.capacity.check"
    _description = "Delivery Capacity Check"
    _order = "route_id, check_datetime desc"

    route_id = fields.Many2one("delivery.route", required=True, ondelete="cascade")
    check_datetime = fields.Datetime(default=fields.Datetime.now, required=True)
    vehicle_id = fields.Many2one("fleet.vehicle", related="route_id.vehicle_id", store=True)
    driver_id = fields.Many2one("hr.employee", related="route_id.driver_id", store=True)
    weight = fields.Float(related="route_id.total_weight", store=True)
    volume = fields.Float(related="route_id.total_volume", store=True)
    package_count = fields.Float(related="route_id.total_packages", store=True)
    weight_capacity = fields.Float(related="vehicle_id.delivery_capacity_weight", store=True)
    volume_capacity = fields.Float(related="vehicle_id.delivery_capacity_volume", store=True)
    package_capacity = fields.Integer(related="vehicle_id.delivery_capacity_packages", store=True)
    weight_utilization = fields.Float(compute="_compute_utilization", store=True)
    volume_utilization = fields.Float(compute="_compute_utilization", store=True)
    package_utilization = fields.Float(compute="_compute_utilization", store=True)
    passed = fields.Boolean(compute="_compute_passed", store=True)
    notes = fields.Text()

    @api.depends("weight", "volume", "package_count", "weight_capacity", "volume_capacity", "package_capacity")
    def _compute_utilization(self):
        for check in self:
            check.weight_utilization = check.weight / check.weight_capacity * 100 if check.weight_capacity else 0.0
            check.volume_utilization = check.volume / check.volume_capacity * 100 if check.volume_capacity else 0.0
            check.package_utilization = check.package_count / check.package_capacity * 100 if check.package_capacity else 0.0

    @api.depends("weight_utilization", "volume_utilization", "package_utilization")
    def _compute_passed(self):
        for check in self:
            check.passed = all(value <= 100 for value in (check.weight_utilization, check.volume_utilization, check.package_utilization) if value)

    def action_recheck(self):
        for check in self:
            check.check_datetime = fields.Datetime.now()
        return True

    @api.model
    def create_for_route(self, route):
        return self.create({"route_id": route.id})
