from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class DeliveryAttempt(models.Model):
    _name = "delivery.attempt"
    _description = "Delivery Attempt"
    _order = "attempt_datetime desc, id desc"

    name = fields.Char(required=True, copy=False)
    route_line_id = fields.Many2one("delivery.route.line", required=True, ondelete="cascade", index=True)
    route_id = fields.Many2one("delivery.route", related="route_line_id.route_id", store=True)
    picking_id = fields.Many2one("stock.picking", related="route_line_id.picking_id", store=True)
    partner_id = fields.Many2one("res.partner", related="route_line_id.partner_id", store=True)
    attempt_number = fields.Integer(required=True, default=1)
    attempt_datetime = fields.Datetime(default=fields.Datetime.now, required=True)
    driver_id = fields.Many2one("hr.employee", related="route_line_id.route_id.driver_id", store=True)
    vehicle_id = fields.Many2one("fleet.vehicle", related="route_line_id.route_id.vehicle_id", store=True)
    result = fields.Selection(
        [("delivered", "Delivered"), ("partial", "Partial"), ("failed", "Failed"), ("cancelled", "Cancelled")],
        required=True,
    )
    failure_id = fields.Many2one("delivery.failure")
    recipient_name = fields.Char()
    latitude = fields.Float(digits=(10, 7))
    longitude = fields.Float(digits=(10, 7))
    duration_minutes = fields.Float()
    notes = fields.Text()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code("delivery.attempt") or "New"
        return super().create(vals_list)

    @api.constrains("attempt_number", "duration_minutes")
    def _check_attempt_values(self):
        for attempt in self:
            if attempt.attempt_number <= 0:
                raise ValidationError(_("Attempt number must be greater than zero."))
            if attempt.duration_minutes < 0:
                raise ValidationError(_("Attempt duration cannot be negative."))
