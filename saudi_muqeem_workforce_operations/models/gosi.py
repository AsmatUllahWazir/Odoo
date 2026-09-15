from odoo import api, fields, models, _

class SaudiGOSIProfile(models.Model):
    _name = 'saudi.gosi.profile'
    _description = 'Saudi GOSI Employee Profile'
    _inherit = ['mail.thread']
    _rec_name = 'employee_id'
    employee_id = fields.Many2one('hr.employee', required=True, ondelete='cascade', tracking=True)
    company_id = fields.Many2one(related='employee_id.company_id', store=True)
    gosi_number = fields.Char(required=True, tracking=True)
    eligibility = fields.Selection([('eligible', 'Eligible'), ('not_eligible', 'Not Eligible'), ('pending', 'Pending')], default='eligible', tracking=True)
    registration_date = fields.Date()
    deregistration_date = fields.Date()
    occupational_hazard = fields.Boolean(default=True)
    basic_salary = fields.Monetary(currency_field='currency_id')
    housing_allowance = fields.Monetary(currency_field='currency_id')
    other_allowances = fields.Monetary(currency_field='currency_id')
    contribution_base = fields.Monetary(compute='_compute_contribution_base', store=True, currency_field='currency_id')
    employee_rate = fields.Float(default=9.75)
    employer_rate = fields.Float(default=9.75)
    hazard_rate = fields.Float(default=2.0)
    employee_contribution = fields.Monetary(compute='_compute_contributions', store=True, currency_field='currency_id')
    employer_contribution = fields.Monetary(compute='_compute_contributions', store=True, currency_field='currency_id')
    total_contribution = fields.Monetary(compute='_compute_contributions', store=True, currency_field='currency_id')
    currency_id = fields.Many2one(related='company_id.currency_id', store=True)
    notes = fields.Text()
    _sql_constraints = [('employee_unique', 'unique(employee_id)', 'Only one GOSI profile is allowed per employee.')]

    @api.depends('basic_salary', 'housing_allowance', 'other_allowances')
    def _compute_contribution_base(self):
        for rec in self:
            rec.contribution_base = rec.basic_salary + rec.housing_allowance + rec.other_allowances

    @api.depends('contribution_base', 'employee_rate', 'employer_rate', 'hazard_rate', 'eligibility')
    def _compute_contributions(self):
        for rec in self:
            if rec.eligibility != 'eligible':
                rec.employee_contribution = rec.employer_contribution = rec.total_contribution = 0
                continue
            rec.employee_contribution = rec.contribution_base * rec.employee_rate / 100
            rec.employer_contribution = rec.contribution_base * (rec.employer_rate + rec.hazard_rate) / 100
            rec.total_contribution = rec.employee_contribution + rec.employer_contribution
