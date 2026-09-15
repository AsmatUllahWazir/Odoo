from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import date, timedelta

class HrEmployee(models.Model):
    _inherit = 'hr.employee'
    saudi_employee_type = fields.Selection([('saudi', 'Saudi Citizen'), ('non_saudi', 'Non-Saudi'), ('gulf', 'GCC Citizen')], string='Saudi Workforce Type', default='non_saudi', tracking=True)
    national_id = fields.Char(string='National ID', tracking=True)
    iqama_number = fields.Char(string='Iqama Number', tracking=True, copy=False)
    iqama_issue_date = fields.Date(string='Iqama Issue Date')
    iqama_expiry_date = fields.Date(string='Iqama Expiry Date', tracking=True)
    iqama_hijri_expiry = fields.Char(string='Iqama Expiry (Hijri)')
    passport_number = fields.Char(string='Passport Number', tracking=True)
    passport_issue_date = fields.Date(string='Passport Issue Date')
    passport_expiry_date = fields.Date(string='Passport Expiry Date', tracking=True)
    work_permit_number = fields.Char(string='Work Permit Number', tracking=True)
    work_permit_expiry_date = fields.Date(string='Work Permit Expiry', tracking=True)
    profession_ar = fields.Char(string='Profession (Arabic)')
    sponsor_name = fields.Char(string='Sponsor Name')
    sponsor_id_number = fields.Char(string='Sponsor ID')
    border_number = fields.Char(string='Border Number')
    visa_number = fields.Char(string='Visa Number')
    visa_type = fields.Selection([('work', 'Work Visa'), ('visit', 'Visit'), ('family', 'Family'), ('other', 'Other')], string='Visa Type')
    visa_expiry_date = fields.Date(string='Visa Expiry')
    insurance_policy_number = fields.Char(string='Medical Insurance Policy')
    insurance_expiry_date = fields.Date(string='Insurance Expiry')
    gosi_status = fields.Selection([('not_applicable', 'Not Applicable'), ('pending', 'Pending'), ('active', 'Active'), ('suspended', 'Suspended'), ('terminated', 'Terminated')], string='GOSI Status', default='pending', tracking=True)
    gosi_number = fields.Char(string='GOSI Registration Number')
    qiwa_contract_status = fields.Selection([('unknown', 'Unknown'), ('draft', 'Draft'), ('pending', 'Pending Employee'), ('active', 'Active'), ('expired', 'Expired'), ('terminated', 'Terminated')], string='Qiwa Contract Status', default='unknown')
    qiwa_contract_reference = fields.Char(string='Qiwa Contract Reference')
    government_notes = fields.Text(string='Government Notes')
    compliance_document_ids = fields.One2many('saudi.compliance.document', 'employee_id', string='Compliance Documents')
    government_transaction_ids = fields.One2many('saudi.government.transaction', 'employee_id', string='Government Transactions')
    compliance_case_ids = fields.One2many('saudi.compliance.case', 'employee_id', string='Compliance Cases')
    clearance_ids = fields.One2many('saudi.clearance', 'employee_id', string='Clearances')
    eos_request_ids = fields.One2many('saudi.eos.request', 'employee_id', string='EOS Requests')
    compliance_score = fields.Integer(compute='_compute_compliance_score', store=True)
    compliance_status = fields.Selection([('compliant', 'Compliant'), ('attention', 'Needs Attention'), ('critical', 'Critical')], compute='_compute_compliance_status', store=True)
    compliance_issue_count = fields.Integer(compute='_compute_compliance_score', store=True)
    document_expiry_count = fields.Integer(compute='_compute_compliance_score', store=True)
    government_transaction_count = fields.Integer(compute='_compute_compliance_score', store=True)
    active_compliance_case_count = fields.Integer(compute='_compute_compliance_score', store=True)
    has_iqama = fields.Boolean(compute='_compute_compliance_score', store=True)
    has_passport = fields.Boolean(compute='_compute_compliance_score', store=True)
    has_work_permit = fields.Boolean(compute='_compute_compliance_score', store=True)
    has_insurance = fields.Boolean(compute='_compute_compliance_score', store=True)

    @api.depends('iqama_expiry_date', 'passport_expiry_date', 'work_permit_expiry_date', 'insurance_expiry_date', 'visa_expiry_date', 'compliance_document_ids.state', 'compliance_case_ids.state', 'compliance_case_ids.priority')
    def _compute_compliance_score(self):
        today = fields.Date.context_today(self)
        for employee in self:
            issues = 0
            docs = employee.compliance_document_ids.filtered(lambda d: d.state in ('expired', 'expiring'))
            issues += len(docs)
            for value in (employee.iqama_expiry_date, employee.passport_expiry_date, employee.work_permit_expiry_date, employee.insurance_expiry_date, employee.visa_expiry_date):
                if value and value <= today + timedelta(days=30):
                    issues += 1
            cases = employee.compliance_case_ids.filtered(lambda c: c.state not in ('closed', 'cancelled'))
            issues += len(cases)
            employee.compliance_issue_count = issues
            employee.document_expiry_count = len(docs)
            employee.government_transaction_count = len(employee.government_transaction_ids)
            employee.active_compliance_case_count = len(cases)
            employee.has_iqama = bool(employee.iqama_number and employee.iqama_expiry_date)
            employee.has_passport = bool(employee.passport_number and employee.passport_expiry_date)
            employee.has_work_permit = bool(employee.work_permit_number and employee.work_permit_expiry_date)
            employee.has_insurance = bool(employee.insurance_policy_number and employee.insurance_expiry_date)
            required = 4 if employee.saudi_employee_type == 'non_saudi' else 2
            present = sum((bool(x) for x in (employee.has_iqama, employee.has_passport, employee.has_work_permit, employee.has_insurance)))
            base = max(0, min(100, int(present / required * 70)))
            penalty = min(70, issues * 10)
            employee.compliance_score = max(0, min(100, base + 30 - penalty))

    @api.depends('compliance_score', 'compliance_issue_count')
    def _compute_compliance_status(self):
        for employee in self:
            if employee.compliance_score >= 85 and employee.compliance_issue_count == 0:
                employee.compliance_status = 'compliant'
            elif employee.compliance_score >= 55:
                employee.compliance_status = 'attention'
            else:
                employee.compliance_status = 'critical'

    @api.constrains('iqama_number', 'passport_number', 'work_permit_number', 'gosi_number')
    def _check_unique_government_numbers(self):
        for employee in self:
            for field_name, label in [('iqama_number', 'Iqama Number'), ('passport_number', 'Passport Number'), ('work_permit_number', 'Work Permit Number'), ('gosi_number', 'GOSI Number')]:
                value = employee[field_name]
                if value:
                    domain = [(field_name, '=', value), ('id', '!=', employee.id)]
                    if self.search_count(domain):
                        raise ValidationError(_('%s must be unique.') % label)

    def action_open_compliance_documents(self):
        self.ensure_one()
        return {'type': 'ir.actions.act_window', 'name': _('Compliance Documents'), 'res_model': 'saudi.compliance.document', 'view_mode': 'tree,form', 'domain': [('employee_id', '=', self.id)], 'context': {'default_employee_id': self.id}}

    def action_open_government_transactions(self):
        self.ensure_one()
        return {'type': 'ir.actions.act_window', 'name': _('Government Transactions'), 'res_model': 'saudi.government.transaction', 'view_mode': 'tree,form', 'domain': [('employee_id', '=', self.id)], 'context': {'default_employee_id': self.id}}

    def action_create_compliance_case(self):
        self.ensure_one()
        return {'type': 'ir.actions.act_window', 'name': _('New Compliance Case'), 'res_model': 'saudi.compliance.case', 'view_mode': 'form', 'target': 'current', 'context': {'default_employee_id': self.id}}
