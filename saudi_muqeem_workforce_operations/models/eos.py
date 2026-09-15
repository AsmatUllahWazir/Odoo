from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class SaudiEOSRequest(models.Model):
    _name = 'saudi.eos.request'
    _description = 'Saudi End of Service Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'request_date desc, id desc'
    name = fields.Char(default='New', required=True, copy=False, tracking=True)
    employee_id = fields.Many2one('hr.employee', required=True, ondelete='cascade', tracking=True)
    company_id = fields.Many2one(related='employee_id.company_id', store=True)
    request_date = fields.Date(default=fields.Date.context_today, required=True)
    last_working_day = fields.Date(required=True)
    start_date = fields.Date(related='employee_id.first_contract_date', store=True)
    reason = fields.Selection([('resignation', 'Resignation'), ('termination', 'Termination'), ('contract_expiry', 'Contract Expiry'), ('retirement', 'Retirement'), ('mutual', 'Mutual Agreement'), ('other', 'Other')], required=True, tracking=True)
    state = fields.Selection([('draft', 'Draft'), ('submitted', 'Submitted'), ('hr_approved', 'HR Approved'), ('finance_approved', 'Finance Approved'), ('paid', 'Paid'), ('rejected', 'Rejected'), ('cancelled', 'Cancelled')], default='draft', tracking=True)
    service_years = fields.Float(compute='_compute_service', store=True)
    service_months = fields.Integer(compute='_compute_service', store=True)
    monthly_basic = fields.Monetary(currency_field='currency_id')
    monthly_housing = fields.Monetary(currency_field='currency_id')
    monthly_allowances = fields.Monetary(currency_field='currency_id')
    eos_base_salary = fields.Monetary(compute='_compute_amounts', store=True, currency_field='currency_id')
    gross_eos = fields.Monetary(compute='_compute_amounts', store=True, currency_field='currency_id')
    leave_encashment = fields.Monetary(currency_field='currency_id')
    unpaid_deductions = fields.Monetary(currency_field='currency_id')
    advances_deduction = fields.Monetary(currency_field='currency_id')
    other_deductions = fields.Monetary(currency_field='currency_id')
    net_settlement = fields.Monetary(compute='_compute_amounts', store=True, currency_field='currency_id')
    currency_id = fields.Many2one(related='company_id.currency_id', store=True)
    calculation_notes = fields.Html()
    rejection_reason = fields.Text()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('saudi.eos.request') or 'New'
        return super().create(vals_list)

    @api.depends('employee_id.first_contract_date', 'last_working_day')
    def _compute_service(self):
        for rec in self:
            if rec.start_date and rec.last_working_day and (rec.last_working_day >= rec.start_date):
                days = (rec.last_working_day - rec.start_date).days + 1
                rec.service_years = days / 365.0
                rec.service_months = int(days / 30.4375)
            else:
                rec.service_years = 0
                rec.service_months = 0

    @api.depends('service_years', 'monthly_basic', 'monthly_housing', 'monthly_allowances', 'leave_encashment', 'unpaid_deductions', 'advances_deduction', 'other_deductions', 'reason')
    def _compute_amounts(self):
        for rec in self:
            base = rec.monthly_basic + rec.monthly_housing + rec.monthly_allowances
            rec.eos_base_salary = base
            years = rec.service_years
            if years <= 0:
                gross = 0
            elif years <= 5:
                gross = base * 0.5 * years
            else:
                gross = base * 0.5 * 5 + base * (years - 5)
            if rec.reason == 'resignation':
                if years < 2:
                    factor = 0.0
                elif years < 5:
                    factor = 1 / 3
                elif years < 10:
                    factor = 2 / 3
                else:
                    factor = 1.0
                gross *= factor
            rec.gross_eos = gross
            rec.net_settlement = gross + rec.leave_encashment - rec.unpaid_deductions - rec.advances_deduction - rec.other_deductions

    @api.constrains('last_working_day', 'start_date')
    def _check_dates(self):
        for rec in self:
            if rec.start_date and rec.last_working_day < rec.start_date:
                raise ValidationError(_('Last working day cannot be before the employee start date.'))

    def action_submit(self):
        self.write({'state': 'submitted'})

    def action_hr_approve(self):
        self.write({'state': 'hr_approved'})

    def action_finance_approve(self):
        self.write({'state': 'finance_approved'})

    def action_mark_paid(self):
        self.write({'state': 'paid'})

    def action_reject(self):
        self.write({'state': 'rejected'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})
