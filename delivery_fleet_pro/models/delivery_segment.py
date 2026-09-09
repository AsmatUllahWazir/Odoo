from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class DeliveryRouteSegment(models.Model):
    _name = "delivery.route.segment"
    _description = "Delivery Route Segment"
    _order = "route_id, sequence, id"

    route_id = fields.Many2one("delivery.route", required=True, ondelete="cascade", index=True)
    sequence = fields.Integer(default=10)
    from_line_id = fields.Many2one("delivery.route.line", ondelete="cascade")
    to_line_id = fields.Many2one("delivery.route.line", ondelete="cascade")
    from_latitude = fields.Float(digits=(10, 7))
    from_longitude = fields.Float(digits=(10, 7))
    to_latitude = fields.Float(digits=(10, 7))
    to_longitude = fields.Float(digits=(10, 7))
    distance_km = fields.Float()
    duration_hours = fields.Float()
    service_delay_hours = fields.Float()
    planned_arrival = fields.Datetime()
    actual_arrival = fields.Datetime()
    provider = fields.Selection(
        [("heuristic", "Heuristic"), ("openrouteservice", "OpenRouteService"), ("google", "Google")],
        default="heuristic",
        required=True,
    )
    status = fields.Selection(
        [("planned", "Planned"), ("active", "Active"), ("completed", "Completed"), ("skipped", "Skipped")],
        default="planned",
        required=True,
    )
    notes = fields.Text()

    @api.constrains("distance_km", "duration_hours", "service_delay_hours")
    def _check_positive_metrics(self):
        for segment in self:
            if segment.distance_km < 0 or segment.duration_hours < 0 or segment.service_delay_hours < 0:
                raise ValidationError(_("Route segment metrics cannot be negative."))
