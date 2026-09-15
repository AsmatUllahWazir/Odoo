from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class SaudiClearance(models.Model):
    _name = 'saudi.clearance'
    _description = 'Saudi Employee Clearance / Offboarding'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'request_date desc, id desc'
    name = fields.Char(default='New', required=True, copy=False, tracking=True)
    employee_id = fields.Many2one('hr.employee', required=True, ondelete='cascade', tracking=True)
    company_id = fields.Many2one(related='employee_id.company_id', store=True)
    request_date = fields.Date(default=fields.Date.context_today, required=True)
    last_working_day = fields.Date(required=True)
    reason = fields.Selection([('resignation', 'Resignation'), ('termination', 'Termination'), ('contract_expiry', 'Contract Expiry'), ('retirement', 'Retirement'), ('other', 'Other')], required=True)
    state = fields.Selection([('draft', 'Draft'), ('in_progress', 'In Progress'), ('hr', 'HR Clearance'), ('finance', 'Finance Clearance'), ('it', 'IT Clearance'), ('manager', 'Manager Clearance'), ('ready', 'Ready for Finalization'), ('done', 'Completed'), ('cancelled', 'Cancelled')], default='draft', tracking=True)
    asset_returned = fields.Boolean()
    advances_settled = fields.Boolean()
    loans_settled = fields.Boolean()
    finance_cleared = fields.Boolean()
    it_cleared = fields.Boolean()
    manager_cleared = fields.Boolean()
    hr_cleared = fields.Boolean()
    government_actions_done = fields.Boolean()
    final_payroll_done = fields.Boolean()
    notes = fields.Html()
    completion_percentage = fields.Integer(compute='_compute_completion')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('saudi.clearance') or 'New'
        return super().create(vals_list)

    @api.depends('asset_returned', 'advances_settled', 'loans_settled', 'finance_cleared', 'it_cleared', 'manager_cleared', 'hr_cleared', 'government_actions_done', 'final_payroll_done')
    def _compute_completion(self):
        fields_to_check = ['asset_returned', 'advances_settled', 'loans_settled', 'finance_cleared', 'it_cleared', 'manager_cleared', 'hr_cleared', 'government_actions_done', 'final_payroll_done']
        for rec in self:
            rec.completion_percentage = int(sum((bool(rec[f]) for f in fields_to_check)) * 100 / len(fields_to_check))

    def action_start(self):
        self.write({'state': 'in_progress'})

    def action_hr(self):
        self.write({'state': 'hr'})

    def action_finance(self):
        self.write({'state': 'finance'})

    def action_it(self):
        self.write({'state': 'it'})

    def action_manager(self):
        self.write({'state': 'manager'})

    def action_ready(self):
        for rec in self:
            if rec.completion_percentage < 100:
                raise ValidationError(_('All clearance items must be completed before finalization.'))
            rec.state = 'ready'

    def action_done(self):
        self.write({'state': 'done'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})
