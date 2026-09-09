from datetime import timedelta
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class DeliveryFailureReason(models.Model):
    _name = "delivery.failure"
    _description = "Delivery Failure Reason"
    _order = "sequence, name"

    name = fields.Char(required=True)
    code = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company)
    retry_allowed = fields.Boolean(default=True)
    default_retry_days = fields.Integer(default=1)
    customer_visible = fields.Boolean(default=True)
    description = fields.Text()

    _sql_constraints = [("failure_code_company_unique", "unique(company_id, code)", "Failure code must be unique per company.")]

    @api.constrains("default_retry_days")
    def _check_retry_days(self):
        for record in self:
            if record.default_retry_days < 0:
                raise ValidationError(_("Retry days cannot be negative."))
