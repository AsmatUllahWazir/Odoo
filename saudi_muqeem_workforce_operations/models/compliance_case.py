from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class SaudiComplianceCase(models.Model):
    _name = 'saudi.compliance.case'
    _description = 'Saudi HR Compliance Case'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'priority desc, deadline asc, id desc'
    name = fields.Char(default='New', required=True, copy=False, tracking=True)
    employee_id = fields.Many2one('hr.employee', required=True, ondelete='cascade', tracking=True)
    company_id = fields.Many2one(related='employee_id.company_id', store=True)
    case_type = fields.Selection([('document', 'Document Expiry'), ('iqama', 'Iqama'), ('passport', 'Passport'), ('work_permit', 'Work Permit'), ('insurance', 'Insurance'), ('gosi', 'GOSI'), ('qiwa', 'Qiwa Contract'), ('wps', 'WPS'), ('labor_law', 'Labor Law'), ('government', 'Government Transaction'), ('offboarding', 'Offboarding'), ('other', 'Other')], required=True, tracking=True)
    priority = fields.Selection([('0', 'Low'), ('1', 'Normal'), ('2', 'High'), ('3', 'Critical')], default='1', tracking=True)
    state = fields.Selection([('draft', 'New'), ('in_progress', 'In Progress'), ('waiting', 'Waiting'), ('resolved', 'Resolved'), ('closed', 'Closed'), ('cancelled', 'Cancelled')], default='draft', tracking=True)
    assigned_to = fields.Many2one('res.users', default=lambda self: self.env.user, tracking=True)
    deadline = fields.Date(tracking=True)
    description = fields.Html()
    resolution = fields.Html()
    root_cause = fields.Text()
    government_transaction_id = fields.Many2one('saudi.government.transaction')
    document_id = fields.Many2one('saudi.compliance.document')
    days_overdue = fields.Integer(compute='_compute_days_overdue')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('saudi.compliance.case') or 'New'
        return super().create(vals_list)

    @api.depends('deadline', 'state')
    def _compute_days_overdue(self):
        today = fields.Date.context_today(self)
        for rec in self:
            rec.days_overdue = max(0, (today - rec.deadline).days) if rec.deadline and rec.state not in ('closed', 'cancelled') else 0

    def action_start(self):
        self.write({'state': 'in_progress'})

    def action_wait(self):
        self.write({'state': 'waiting'})

    def action_resolve(self):
        for rec in self:
            if not rec.resolution:
                raise ValidationError(_('Please enter a resolution before resolving the case.'))
            rec.state = 'resolved'

    def action_close(self):
        self.write({'state': 'closed'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})
