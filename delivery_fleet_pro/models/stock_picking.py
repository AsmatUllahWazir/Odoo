from odoo import api, fields, models, _


class StockPicking(models.Model):
    _inherit = "stock.picking"

    delivery_route_line_ids = fields.One2many("delivery.route.line", "picking_id", string="Delivery Route Stops")
    delivery_route_count = fields.Integer(compute="_compute_delivery_route_count")
    delivery_route_id = fields.Many2one("delivery.route", compute="_compute_delivery_route", store=True)
    delivery_status = fields.Selection(
        [
            ("not_planned", "Not Planned"),
            ("planned", "Planned"),
            ("assigned", "Assigned"),
            ("in_transit", "In Transit"),
            ("arrived", "Arrived"),
            ("delivered", "Delivered"),
            ("partial", "Partial"),
            ("failed", "Failed"),
            ("cancelled", "Cancelled"),
        ],
        compute="_compute_delivery_status",
        store=True,
    )
    delivery_latitude = fields.Float(related="partner_id.delivery_latitude", readonly=True)
    delivery_longitude = fields.Float(related="partner_id.delivery_longitude", readonly=True)
    delivery_instructions = fields.Text(related="partner_id.delivery_instructions", readonly=True)

    @api.depends("delivery_route_line_ids")
    def _compute_delivery_route_count(self):
        for picking in self:
            picking.delivery_route_count = len(picking.delivery_route_line_ids)

    @api.depends("delivery_route_line_ids.route_id")
    def _compute_delivery_route(self):
        for picking in self:
            picking.delivery_route_id = picking.delivery_route_line_ids[:1].route_id if picking.delivery_route_line_ids else False

    @api.depends("delivery_route_line_ids.status")
    def _compute_delivery_status(self):
        for picking in self:
            statuses = picking.delivery_route_line_ids.mapped("status")
            if not statuses:
                picking.delivery_status = "not_planned"
            elif "delivered" in statuses and all(s in ("delivered", "cancelled") for s in statuses):
                picking.delivery_status = "delivered"
            elif "partial" in statuses:
                picking.delivery_status = "partial"
            elif "failed" in statuses:
                picking.delivery_status = "failed"
            elif "arrived" in statuses:
                picking.delivery_status = "arrived"
            elif "in_transit" in statuses:
                picking.delivery_status = "in_transit"
            elif "assigned" in statuses:
                picking.delivery_status = "assigned"
            else:
                picking.delivery_status = "planned"

    def action_open_delivery_route(self):
        self.ensure_one()
        route = self.delivery_route_id
        if not route:
            return False
        return {
            "type": "ir.actions.act_window",
            "res_model": "delivery.route",
            "view_mode": "form",
            "res_id": route.id,
        }
