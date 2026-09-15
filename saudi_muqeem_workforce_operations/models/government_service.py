from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class SaudiGovernmentService(models.Model):
    _name = 'saudi.government.service'
    _description = 'Saudi Government Service Configuration'
    _order = 'sequence, name'
    name = fields.Char(required=True, translate=True)
    code = fields.Char(required=True)
    provider = fields.Selection([('manual', 'Manual'), ('muqeem', 'Muqeem'), ('qiwa', 'Qiwa'), ('gosi', 'GOSI'), ('mudad', 'Mudad')], default='manual', required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    requires_iqama = fields.Boolean()
    requires_passport = fields.Boolean()
    requires_national_id = fields.Boolean()
    requires_sponsor = fields.Boolean()
    requires_attachment = fields.Boolean()
    default_deadline_days = fields.Integer(default=5)
    description = fields.Text(translate=True)
    endpoint_key = fields.Char(help='Logical adapter key. Credentials and URLs must be configured outside source code.')
    _sql_constraints = [('service_code_unique', 'unique(code)', 'Government service code must be unique.')]

class SaudiGovernmentServiceLog(models.Model):
    _name = 'saudi.government.service.log'
    _description = 'Government Service Audit Log'
    _order = 'create_date desc'
    transaction_id = fields.Many2one('saudi.government.transaction', required=True, ondelete='cascade')
    employee_id = fields.Many2one(related='transaction_id.employee_id', store=True)
    service_code = fields.Char()
    provider = fields.Selection(related='transaction_id.provider', store=True)
    event = fields.Selection([('created', 'Created'), ('submitted', 'Submitted'), ('processing', 'Processing'), ('success', 'Success'), ('failure', 'Failure'), ('retry', 'Retry'), ('cancelled', 'Cancelled')], required=True)
    event_date = fields.Datetime(default=fields.Datetime.now, required=True)
    user_id = fields.Many2one('res.users', default=lambda self: self.env.user)
    message = fields.Text()
    payload_hash = fields.Char(help='Hash/reference only; do not store secrets or credentials here.')

    @api.model
    def log(self, transaction, event, message=None, payload_hash=None):
        return self.create({'transaction_id': transaction.id, 'service_code': transaction.service_type, 'event': event, 'message': message, 'payload_hash': payload_hash})
