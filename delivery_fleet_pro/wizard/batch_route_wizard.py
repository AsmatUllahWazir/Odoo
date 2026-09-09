from datetime import timedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class DeliveryBatchRouteWizard(models.TransientModel):
    _name = "delivery.batch.route.wizard"
    _description = "Create Multiple Delivery Routes"

    date_from = fields.Date(required=True, default=fields.Date.context_today)
    date_to = fields.Date(required=True, default=fields.Date.context_today)
    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company)
    warehouse_id = fields.Many2one("stock.warehouse", required=True)
    vehicle_ids = fields.Many2many("fleet.vehicle")
    driver_ids = fields.Many2many("hr.employee")
    max_stops_per_route = fields.Integer(default=25)
    auto_assign = fields.Boolean(default=True)
    auto_optimize = fields.Boolean(default=True)
    service_type_id = fields.Many2one("delivery.service.type")
    zone_id = fields.Many2one("delivery.zone")
    picking_ids = fields.Many2many("stock.picking")
    created_route_ids = fields.Many2many("delivery.route", readonly=True)

    @api.constrains("date_from", "date_to", "max_stops_per_route")
    def _check_values(self):
        for wizard in self:
            if wizard.date_to < wizard.date_from:
                raise UserError(_("End date must be on or after start date."))
            if wizard.max_stops_per_route <= 0:
                raise UserError(_("Maximum stops per route must be positive."))

    def action_prepare_pickings(self):
        self.ensure_one()
        domain = [
            ("company_id", "=", self.company_id.id),
            ("picking_type_id.warehouse_id", "=", self.warehouse_id.id),
            ("picking_type_id.code", "=", "outgoing"),
            ("state", "=", "assigned"),
            ("scheduled_date", ">=", fields.Datetime.to_datetime(self.date_from)),
            ("scheduled_date", "<", fields.Datetime.to_datetime(self.date_to) + timedelta(days=1)),
        ]
        if self.zone_id:
            domain.append(("partner_id.delivery_zone_id", "=", self.zone_id.id))
        self.picking_ids = [fields.Command.set(self.env["stock.picking"].search(domain).ids)]
        return self._reopen()

    def action_create_routes(self):
        self.ensure_one()
        if not self.picking_ids:
            raise UserError(_("No pickings were selected."))
        created = self.env["delivery.route"]
        current_date = self.date_from
        while current_date <= self.date_to:
            day_pickings = self.picking_ids.filtered(lambda p: p.scheduled_date.date() == current_date)
            if self.zone_id:
                day_pickings = day_pickings.filtered(lambda p: p.partner_id.delivery_zone_id == self.zone_id)
            for offset in range(0, len(day_pickings), self.max_stops_per_route):
                chunk = day_pickings[offset:offset + self.max_stops_per_route]
                if not chunk:
                    continue
                driver = self.driver_ids[offset // self.max_stops_per_route] if self.driver_ids and offset // self.max_stops_per_route < len(self.driver_ids) else False
                vehicle = self.vehicle_ids[offset // self.max_stops_per_route] if self.vehicle_ids and offset // self.max_stops_per_route < len(self.vehicle_ids) else False
                route = self.env["delivery.route"].create({
                    "date": current_date,
                    "company_id": self.company_id.id,
                    "warehouse_id": self.warehouse_id.id,
                    "driver_id": driver.id if driver else False,
                    "vehicle_id": vehicle.id if vehicle else False,
                    "service_type_id": self.service_type_id.id,
                    "zone_id": self.zone_id.id,
                })
                seq = 10
                for picking in chunk:
                    self.env["delivery.route.line"].create({
                        "route_id": route.id,
                        "picking_id": picking.id,
                        "sequence": seq,
                        "latitude": picking.partner_id.delivery_latitude,
                        "longitude": picking.partner_id.delivery_longitude,
                    })
                    seq += 10
                if self.auto_assign:
                    self.env["delivery.scheduler"].assign_resources(route)
                if self.auto_optimize:
                    self.env["delivery.routing.service"].route(route.line_ids, route.warehouse_id, "heuristic", route.company_id)
                created |= route
            current_date += timedelta(days=1)
        self.created_route_ids = [fields.Command.set(created.ids)]
        return self._reopen()

    def _reopen(self):
        return {"type": "ir.actions.act_window", "res_model": self._name, "view_mode": "form", "res_id": self.id, "target": "new"}
