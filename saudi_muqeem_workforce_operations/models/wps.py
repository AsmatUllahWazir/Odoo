from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class SaudiWPSBatch(models.Model):
    _name = 'saudi.wps.batch'
    _description = 'Saudi WPS / Mudad Payroll Batch'
    _inherit = ['mail.thread']
    _order = 'period_end desc, id desc'
    name = fields.Char(default='New', required=True, copy=False, tracking=True)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    period_start = fields.Date(required=True)
    period_end = fields.Date(required=True)
    bank_name = fields.Char()
    state = fields.Selection([('draft', 'Draft'), ('validated', 'Validated'), ('generated', 'File Generated'), ('submitted', 'Submitted'), ('accepted', 'Accepted'), ('rejected', 'Rejected')], default='draft', tracking=True)
    line_ids = fields.One2many('saudi.wps.line', 'batch_id')
    employee_count = fields.Integer(compute='_compute_totals', store=True)
    total_amount = fields.Monetary(compute='_compute_totals', store=True, currency_field='currency_id')
    invalid_count = fields.Integer(compute='_compute_totals', store=True)
    currency_id = fields.Many2one(related='company_id.currency_id', store=True)
    validation_message = fields.Text()

    @api.depends('line_ids.amount', 'line_ids.validation_state')
    def _compute_totals(self):
        for rec in self:
            rec.employee_count = len(rec.line_ids)
            rec.total_amount = sum(rec.line_ids.mapped('amount'))
            rec.invalid_count = len(rec.line_ids.filtered(lambda l: l.validation_state == 'invalid'))

    @api.constrains('period_start', 'period_end')
    def _check_period(self):
        for rec in self:
            if rec.period_end < rec.period_start:
                raise ValidationError(_('Period end must be after period start.'))

    def action_validate(self):
        for batch in self:
            batch.line_ids._validate_line()
            if batch.invalid_count:
                batch.validation_message = _('There are invalid WPS lines. Please correct them before generating the file.')
                raise ValidationError(batch.validation_message)
            batch.state = 'validated'
        return True

    def action_generate(self):
        for batch in self:
            if batch.state != 'validated':
                raise ValidationError(_('Validate the batch before generating a file.'))
            batch.state = 'generated'
        return True

    def action_submit(self):
        self.write({'state': 'submitted'})

    def action_accept(self):
        self.write({'state': 'accepted'})

    def action_reject(self):
        self.write({'state': 'rejected'})

class SaudiWPSLine(models.Model):
    _name = 'saudi.wps.line'
    _description = 'Saudi WPS Line'
    batch_id = fields.Many2one('saudi.wps.batch', required=True, ondelete='cascade')
    employee_id = fields.Many2one('hr.employee', required=True)
    bank_name = fields.Char()
    iban = fields.Char()
    employee_identifier = fields.Char()
    basic_salary = fields.Monetary(currency_field='currency_id')
    housing = fields.Monetary(currency_field='currency_id')
    deductions = fields.Monetary(currency_field='currency_id')
    amount = fields.Monetary(compute='_compute_amount', store=True, currency_field='currency_id')
    currency_id = fields.Many2one(related='batch_id.currency_id', store=True)
    validation_state = fields.Selection([('valid', 'Valid'), ('invalid', 'Invalid')], default='invalid', tracking=True)
    validation_message = fields.Text()

    @api.depends('basic_salary', 'housing', 'deductions')
    def _compute_amount(self):
        for line in self:
            line.amount = line.basic_salary + line.housing - line.deductions

    def _validate_line(self):
        for line in self:
            errors = []
            if not line.employee_id:
                errors.append(_('Employee is required.'))
            if not line.iban:
                errors.append(_('IBAN is required.'))
            if not line.employee_identifier:
                errors.append(_('Employee identifier is required.'))
            if line.amount < 0:
                errors.append(_('Net amount cannot be negative.'))
            line.validation_state = 'invalid' if errors else 'valid'
            line.validation_message = '\n'.join(errors)
