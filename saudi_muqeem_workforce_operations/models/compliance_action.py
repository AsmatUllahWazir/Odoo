from odoo import api, fields, models, _

class SaudiComplianceAction(models.Model):
    _name = 'saudi.compliance.action'
    _description = 'Saudi Compliance Action Plan'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'deadline, sequence, id'
    name = fields.Char(required=True, tracking=True)
    employee_id = fields.Many2one('hr.employee', required=True, ondelete='cascade')
    company_id = fields.Many2one(related='employee_id.company_id', store=True)
    case_id = fields.Many2one('saudi.compliance.case', ondelete='set null')
    action_type = fields.Selection([('renew_document', 'Renew Document'), ('collect_document', 'Collect Document'), ('submit_government', 'Submit Government Request'), ('verify', 'Verify'), ('approve', 'Approve'), ('follow_up', 'Follow Up'), ('other', 'Other')], required=True)
    sequence = fields.Integer(default=10)
    assigned_to = fields.Many2one('res.users', default=lambda self: self.env.user)
    deadline = fields.Date()
    state = fields.Selection([('todo', 'To Do'), ('in_progress', 'In Progress'), ('done', 'Done'), ('cancelled', 'Cancelled')], default='todo', tracking=True)
    completed_date = fields.Datetime(readonly=True)
    notes = fields.Text()

    def action_start(self):
        self.write({'state': 'in_progress'})

    def action_done(self):
        self.write({'state': 'done', 'completed_date': fields.Datetime.now()})

    def action_cancel(self):
        self.write({'state': 'cancelled'})
