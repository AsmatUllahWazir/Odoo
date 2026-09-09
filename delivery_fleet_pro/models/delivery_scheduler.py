from datetime import datetime, timedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class DeliveryScheduler(models.AbstractModel):
    _name = "delivery.scheduler"
    _description = "Delivery Route Scheduler"

    @api.model
    def find_available_driver(self, company, date, duration=0.0):
        employees = self.env["hr.employee"].search([
            ("company_id", "=", company.id),
            ("delivery_available", "=", True),
        ])
        schedules = self.env["delivery.driver.schedule"].search([
            ("employee_id", "in", employees.ids),
            ("date", "=", date),
            ("available", "=", True),
        ])
        scheduled_ids = schedules.filtered(lambda s: duration <= s.max_hours).mapped("employee_id").ids
        busy = self.env["delivery.route"].search([
            ("company_id", "=", company.id),
            ("date", "=", date),
            ("state", "in", ["planned", "dispatched", "in_transit"]),
        ]).mapped("driver_id").ids
        candidates = employees.filtered(lambda e: e.id not in busy and (not scheduled_ids or e.id in scheduled_ids))
        return candidates[:1]

    @api.model
    def find_available_vehicle(self, company, date, weight=0.0, volume=0.0, packages=0):
        vehicles = self.env["fleet.vehicle"].search([
            ("company_id", "=", company.id),
            ("delivery_status", "=", "available"),
        ])
        busy = self.env["delivery.route"].search([
            ("company_id", "=", company.id),
            ("date", "=", date),
            ("state", "in", ["planned", "dispatched", "in_transit"]),
        ]).mapped("vehicle_id").ids
        candidates = vehicles.filtered(lambda v: v.id not in busy and (not v.delivery_capacity_weight or v.delivery_capacity_weight >= weight) and (not v.delivery_capacity_volume or v.delivery_capacity_volume >= volume) and (not v.delivery_capacity_packages or v.delivery_capacity_packages >= packages))
        return candidates[:1]

    @api.model
    def assign_resources(self, route):
        if not route.driver_id:
            route.driver_id = self.find_available_driver(route.company_id, route.date, route.estimated_duration)
        if not route.vehicle_id:
            route.vehicle_id = self.find_available_vehicle(route.company_id, route.date, route.total_weight, route.total_volume, route.total_packages)
        if not route.driver_id or not route.vehicle_id:
            raise UserError(_("No suitable driver or vehicle was found for route %s.") % route.name)
        return route

    @api.model
    def rebalance_routes(self, routes):
        for route in routes:
            self.assign_resources(route)
        return True
