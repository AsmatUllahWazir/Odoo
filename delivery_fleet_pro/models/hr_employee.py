from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    delivery_skills = fields.Text(string="Delivery Skills")
    delivery_available = fields.Boolean(default=True, string="Available for Delivery")
    delivery_license_number = fields.Char(string="Delivery License Number")
    delivery_license_expiry = fields.Date()
    delivery_license_class = fields.Char()
    delivery_max_hours = fields.Float(default=8.0)
    delivery_hourly_cost = fields.Monetary()
    delivery_home_depot_id = fields.Many2one("stock.warehouse")
    delivery_current_route_id = fields.Many2one("delivery.route", compute="_compute_current_route")
    delivery_route_ids = fields.One2many("delivery.route", "driver_id", readonly=True)
    delivery_route_count = fields.Integer(compute="_compute_route_count")
    delivery_can_handle_cash = fields.Boolean()
    delivery_can_handle_fragile = fields.Boolean()
    delivery_can_handle_temperature = fields.Boolean()
    delivery_notes = fields.Text()
    currency_id = fields.Many2one("res.currency", related="company_id.currency_id", store=True)

    @api.depends("delivery_route_ids.state")
    def _compute_current_route(self):
        active_states = ("planned", "dispatched", "in_transit")
        for employee in self:
            employee.delivery_current_route_id = employee.delivery_route_ids.filtered(lambda r: r.state in active_states)[:1]

    @api.depends("delivery_route_ids")
    def _compute_route_count(self):
        for employee in self:
            employee.delivery_route_count = len(employee.delivery_route_ids)

    @api.constrains("delivery_max_hours", "delivery_hourly_cost")
    def _check_delivery_values(self):
        for employee in self:
            if employee.delivery_max_hours <= 0:
                raise ValidationError(_("Driver maximum hours must be greater than zero."))
            if employee.delivery_hourly_cost < 0:
                raise ValidationError(_("Driver hourly cost cannot be negative."))
