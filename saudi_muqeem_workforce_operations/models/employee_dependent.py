from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class SaudiEmployeeDependent(models.Model):
    _name = 'saudi.employee.dependent'
    _description = 'Saudi Employee Dependent Government Document'
    _inherit = ['mail.thread']
    _order = 'employee_id, name'
    name = fields.Char(required=True, tracking=True)
    employee_id = fields.Many2one('hr.employee', required=True, ondelete='cascade', tracking=True)
    relationship = fields.Selection([('spouse', 'Spouse'), ('son', 'Son'), ('daughter', 'Daughter'), ('parent', 'Parent'), ('other', 'Other')], required=True)
    national_id = fields.Char()
    iqama_number = fields.Char(tracking=True)
    passport_number = fields.Char(tracking=True)
    nationality_id = fields.Many2one('res.country')
    date_of_birth = fields.Date()
    iqama_expiry_date = fields.Date(tracking=True)
    passport_expiry_date = fields.Date(tracking=True)
    insurance_expiry_date = fields.Date(tracking=True)
    notes = fields.Text()
    state = fields.Selection([('valid', 'Valid'), ('attention', 'Needs Attention'), ('expired', 'Expired')], compute='_compute_state', store=True)

    @api.depends('iqama_expiry_date', 'passport_expiry_date', 'insurance_expiry_date')
    def _compute_state(self):
        today = fields.Date.context_today(self)
        for rec in self:
            dates = [d for d in (rec.iqama_expiry_date, rec.passport_expiry_date, rec.insurance_expiry_date) if d]
            if any((d < today for d in dates)):
                rec.state = 'expired'
            elif any((d <= today.replace(day=min(today.day, 28)) for d in dates)):
                rec.state = 'attention'
            else:
                rec.state = 'valid'

    @api.constrains('date_of_birth')
    def _check_dob(self):
        for rec in self:
            if rec.date_of_birth and rec.date_of_birth > fields.Date.context_today(self):
                raise ValidationError(_('Date of birth cannot be in the future.'))
