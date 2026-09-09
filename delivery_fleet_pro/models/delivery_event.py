from odoo import api, fields, models, _


class DeliveryEvent(models.Model):
    _name = "delivery.event"
    _description = "Delivery Tracking Event"
    _order = "event_datetime desc, id desc"

    name = fields.Char(required=True)
    route_id = fields.Many2one("delivery.route", ondelete="cascade", index=True)
    route_line_id = fields.Many2one("delivery.route.line", ondelete="cascade", index=True)
    picking_id = fields.Many2one("stock.picking", index=True)
    event_type = fields.Selection(
        [
            ("created", "Created"),
            ("planned", "Planned"),
            ("assigned", "Assigned"),
            ("dispatched", "Dispatched"),
            ("arrived", "Arrived"),
            ("attempted", "Delivery Attempted"),
            ("delivered", "Delivered"),
            ("partial", "Partially Delivered"),
            ("failed", "Failed"),
            ("retry", "Retry Scheduled"),
            ("cancelled", "Cancelled"),
            ("pod", "POD Captured"),
            ("note", "Note"),
        ],
        required=True,
        index=True,
    )
    event_datetime = fields.Datetime(default=fields.Datetime.now, required=True, index=True)
    user_id = fields.Many2one("res.users", default=lambda self: self.env.user)
    latitude = fields.Float(digits=(10, 7))
    longitude = fields.Float(digits=(10, 7))
    description = fields.Text()
    source = fields.Selection(
        [("system", "System"), ("driver", "Driver"), ("portal", "Portal"), ("user", "User")],
        default="system",
        required=True,
    )
    is_customer_visible = fields.Boolean(default=True)
    partner_id = fields.Many2one("res.partner", related="route_line_id.partner_id", store=True)
    company_id = fields.Many2one("res.company", related="route_id.company_id", store=True)

    @api.model
    def log_event(self, event_type, route=None, line=None, description=None, source="system", **kwargs):
        vals = {
            "name": dict(self._fields["event_type"].selection).get(event_type, event_type),
            "event_type": event_type,
            "route_id": route.id if route else False,
            "route_line_id": line.id if line else False,
            "picking_id": line.picking_id.id if line and line.picking_id else False,
            "description": description or False,
            "source": source,
            "latitude": kwargs.get("latitude", 0.0),
            "longitude": kwargs.get("longitude", 0.0),
            "is_customer_visible": kwargs.get("is_customer_visible", True),
        }
        return self.create(vals)
