from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class DeliverySLA(models.Model):
    _name = "delivery.sla"
    _description = "Delivery SLA"
    _order = "sequence, name"

    name = fields.Char(required=True)
    code = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company)
    service_type_id = fields.Many2one("delivery.service.type")
    target_hours = fields.Float(default=24.0)
    tolerance_minutes = fields.Integer(default=15)
    warning_hours = fields.Float(default=4.0)
    penalty_amount = fields.Monetary(default=0.0)
    currency_id = fields.Many2one("res.currency", related="company_id.currency_id", store=True)
    description = fields.Text()

    _sql_constraints = [("sla_code_company_unique", "unique(company_id, code)", "SLA code must be unique per company.")]

    @api.constrains("target_hours", "warning_hours", "tolerance_minutes")
    def _check_targets(self):
        for sla in self:
            if sla.target_hours <= 0:
                raise ValidationError(_("Target hours must be greater than zero."))
            if sla.warning_hours < 0:
                raise ValidationError(_("Warning hours cannot be negative."))
            if sla.tolerance_minutes < 0:
                raise ValidationError(_("Tolerance cannot be negative."))
