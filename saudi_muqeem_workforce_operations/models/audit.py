from odoo import api, fields, models

class SaudiComplianceAudit(models.Model):
    _name = 'saudi.compliance.audit'
    _description = 'Saudi Compliance Audit Event'
    _order = 'event_date desc, id desc'
    event_date = fields.Datetime(default=fields.Datetime.now, required=True, readonly=True)
    user_id = fields.Many2one('res.users', default=lambda self: self.env.user, readonly=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, readonly=True)
    model_name = fields.Char(readonly=True)
    record_id = fields.Integer(readonly=True)
    employee_id = fields.Many2one('hr.employee', readonly=True)
    event_type = fields.Selection([('create', 'Create'), ('update', 'Update'), ('submit', 'Submit'), ('approve', 'Approve'), ('complete', 'Complete'), ('reject', 'Reject'), ('cancel', 'Cancel'), ('sync', 'Government Sync')], required=True, readonly=True)
    description = fields.Text(readonly=True)
    reference = fields.Char(readonly=True)
    success = fields.Boolean(default=True, readonly=True)

    @api.model
    def log_event(self, event_type, record, description='', employee=None, reference=None, success=True):
        return self.create({'model_name': record._name if record else False, 'record_id': record.id if record else 0, 'employee_id': employee.id if employee else False, 'event_type': event_type, 'description': description, 'reference': reference, 'success': success})
