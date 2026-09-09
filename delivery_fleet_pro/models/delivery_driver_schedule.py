from datetime import datetime, time
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class DeliveryDriverSchedule(models.Model):
    _name = "delivery.driver.schedule"
    _description = "Delivery Driver Availability"
    _order = "date, employee_id"

    employee_id = fields.Many2one("hr.employee", required=True, ondelete="cascade")
    company_id = fields.Many2one("res.company", related="employee_id.company_id", store=True)
    date = fields.Date(required=True, default=fields.Date.context_today)
    available = fields.Boolean(default=True)
    start_hour = fields.Float(default=8.0)
    end_hour = fields.Float(default=17.0)
    break_start = fields.Float(default=13.0)
    break_end = fields.Float(default=14.0)
    max_hours = fields.Float(default=8.0)
    notes = fields.Text()

    _sql_constraints = [("driver_date_unique", "unique(employee_id, date)", "A driver can have only one schedule per date.")]

    @api.constrains("start_hour", "end_hour", "break_start", "break_end", "max_hours")
    def _check_hours(self):
        for rec in self:
            if not 0 <= rec.start_hour <= 24 or not 0 <= rec.end_hour <= 24:
                raise ValidationError(_("Working hours must be between 0 and 24."))
            if rec.end_hour <= rec.start_hour:
                raise ValidationError(_("End hour must be after start hour."))
            if rec.max_hours <= 0:
                raise ValidationError(_("Maximum working hours must be positive."))
