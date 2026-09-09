from datetime import timedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class DeliveryFailureWizard(models.TransientModel):
    _name = "delivery.failure.wizard"
    _description = "Record Delivery Failure"

    route_line_id = fields.Many2one("delivery.route.line", required=True)
    reason_id = fields.Many2one("delivery.failure", required=True)
    failed_at = fields.Datetime(default=fields.Datetime.now, required=True)
    notes = fields.Text()
    latitude = fields.Float(digits=(10, 7))
    longitude = fields.Float(digits=(10, 7))
    create_retry = fields.Boolean(default=True)
    retry_date = fields.Date()

    @api.onchange("reason_id")
    def _onchange_reason(self):
        if self.reason_id and self.route_line_id:
            self.retry_date = self.route_line_id.route_id.date + timedelta(days=self.reason_id.default_retry_days)
            self.create_retry = self.reason_id.retry_allowed

    def action_confirm(self):
        self.ensure_one()
        line = self.route_line_id
        if line.status in ("delivered", "cancelled"):
            raise UserError(_("A delivered or cancelled stop cannot be failed."))
        line.write({"status": "failed", "failure_id": self.reason_id.id, "arrival_time": line.arrival_time or self.failed_at})
        self.env["delivery.event"].log_event(
            "failed",
            route=line.route_id,
            line=line,
            description=self.notes or self.reason_id.name,
            source="driver",
            latitude=self.latitude,
            longitude=self.longitude,
        )
        if self.create_retry and self.reason_id.retry_allowed:
            retry = self.env["delivery.retry"].create({
                "original_line_id": line.id,
                "scheduled_date": self.retry_date or line.route_id.date + timedelta(days=self.reason_id.default_retry_days),
                "attempt_number": self._next_attempt_number(line),
                "reason_id": self.reason_id.id,
                "notes": self.notes,
            })
            line.retry_date = retry.scheduled_date
        return True

    def _next_attempt_number(self, line):
        return self.env["delivery.retry"].search_count([("picking_id", "=", line.picking_id.id)]) + 1
