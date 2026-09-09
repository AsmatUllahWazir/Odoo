from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class DeliveryPlanRouteWizard(models.TransientModel):
    _name = "delivery.plan.route.wizard"
    _description = "Plan Delivery Route"

    date = fields.Date(required=True, default=fields.Date.context_today)
    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company)
    warehouse_id = fields.Many2one("stock.warehouse", required=True)
    route_id = fields.Many2one("delivery.route")
    vehicle_id = fields.Many2one("fleet.vehicle")
    driver_id = fields.Many2one("hr.employee")
    service_type_id = fields.Many2one("delivery.service.type")
    zone_id = fields.Many2one("delivery.zone")
    include_assigned = fields.Boolean(default=False)
    picking_ids = fields.Many2many("stock.picking", string="Pickings")
    open_picking_ids = fields.Many2many("stock.picking", compute="_compute_open_pickings")
    select_all = fields.Boolean()

    @api.depends("warehouse_id", "date", "include_assigned", "zone_id")
    def _compute_open_pickings(self):
        for wizard in self:
            domain = [
                ("company_id", "=", wizard.company_id.id),
                ("picking_type_id.code", "=", "outgoing"),
                ("state", "in", ["confirmed", "assigned"] if wizard.include_assigned else ["assigned"]),
                ("scheduled_date", ">=", fields.Datetime.to_datetime(wizard.date)),
                ("scheduled_date", "<", fields.Datetime.to_datetime(wizard.date) + __import__("datetime").timedelta(days=1)),
            ]
            if wizard.warehouse_id:
                domain.append(("picking_type_id.warehouse_id", "=", wizard.warehouse_id.id))
            if wizard.zone_id:
                domain.append(("partner_id.delivery_zone_id", "=", wizard.zone_id.id))
            wizard.open_picking_ids = self.env["stock.picking"].search(domain)

    def action_load_open_pickings(self):
        self.ensure_one()
        self.picking_ids = [fields.Command.set(self.open_picking_ids.ids)]
        return {"type": "ir.actions.act_window", "res_model": self._name, "view_mode": "form", "res_id": self.id, "target": "new"}

    def action_create_route(self):
        self.ensure_one()
        if not self.picking_ids:
            raise UserError(_("Select at least one outgoing picking."))
        if self.route_id and self.route_id.state not in ("draft",):
            raise ValidationError(_("The selected route is not editable."))
        route = self.route_id or self.env["delivery.route"].create(
            {
                "date": self.date,
                "company_id": self.company_id.id,
                "warehouse_id": self.warehouse_id.id,
                "vehicle_id": self.vehicle_id.id,
                "driver_id": self.driver_id.id,
                "service_type_id": self.service_type_id.id,
                "zone_id": self.zone_id.id,
            }
        )
        existing = route.line_ids.mapped("picking_id").ids
        sequence = max(route.line_ids.mapped("sequence") or [0]) + 10
        lines = []
        for picking in self.picking_ids:
            if picking.id in existing:
                continue
            partner = picking.partner_id
            lines.append(
                {
                    "route_id": route.id,
                    "picking_id": picking.id,
                    "sequence": sequence,
                    "date_from": self._window_from(partner),
                    "date_to": self._window_to(partner),
                    "latitude": partner.delivery_latitude,
                    "longitude": partner.delivery_longitude,
                    "status": "pending",
                }
            )
            sequence += 10
        if lines:
            self.env["delivery.route.line"].create(lines)
        return {
            "type": "ir.actions.act_window",
            "res_model": "delivery.route",
            "view_mode": "form",
            "res_id": route.id,
        }

    def _window_from(self, partner):
        if not partner.delivery_preferred_from:
            return False
        return fields.Datetime.to_datetime(self.date) + __import__("datetime").timedelta(hours=partner.delivery_preferred_from)

    def _window_to(self, partner):
        if not partner.delivery_preferred_to:
            return False
        return fields.Datetime.to_datetime(self.date) + __import__("datetime").timedelta(hours=partner.delivery_preferred_to)
