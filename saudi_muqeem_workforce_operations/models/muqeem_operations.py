from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError

class MuqeemWorkforceProfile(models.Model):
    _name = 'muqeem.workforce.profile'
    _description = 'Muqeem Workforce Profile'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'risk_score desc, name'
    name = fields.Char(compute='_compute_name', store=True)
    employee_id = fields.Many2one('hr.employee', required=True, index=True, ondelete='restrict')
    company_id = fields.Many2one(related='employee_id.company_id', store=True)
    nationality_id = fields.Many2one('res.country')
    iqama_number = fields.Char(index=True, copy=False)
    border_number = fields.Char(index=True)
    passport_number = fields.Char(index=True)
    passport_expiry = fields.Date()
    iqama_issue_date = fields.Date()
    iqama_expiry = fields.Date()
    work_permit_expiry = fields.Date()
    insurance_expiry = fields.Date()
    visa_expiry = fields.Date()
    sponsor_id = fields.Char()
    sponsor_name = fields.Char()
    sponsor_relation = fields.Selection([('company', 'Company'), ('individual', 'Individual'), ('other', 'Other')], default='company')
    profession = fields.Char()
    profession_code = fields.Char()
    qiwa_contract_ref = fields.Char()
    qiwa_contract_state = fields.Selection([('unknown', 'Unknown'), ('draft', 'Draft'), ('active', 'Active'), ('expired', 'Expired'), ('terminated', 'Terminated')], default='unknown')
    establishment_id = fields.Char()
    labor_office_id = fields.Char()
    muqeem_status = fields.Selection([('active', 'Active'), ('suspended', 'Suspended'), ('final_exit', 'Final Exit'), ('transferred', 'Transferred'), ('unknown', 'Unknown')], default='unknown', tracking=True)
    travel_status = fields.Selection([('inside', 'Inside KSA'), ('outside', 'Outside KSA'), ('unknown', 'Unknown')], default='unknown')
    last_muqqeem_sync = fields.Datetime()
    sync_state = fields.Selection([('never', 'Never Synced'), ('queued', 'Queued'), ('success', 'Success'), ('failed', 'Failed'), ('manual', 'Manual')], default='never')
    sync_message = fields.Text()
    iqama_days = fields.Integer(compute='_compute_days', store=True)
    passport_days = fields.Integer(compute='_compute_days', store=True)
    visa_days = fields.Integer(compute='_compute_days', store=True)
    permit_days = fields.Integer(compute='_compute_days', store=True)
    insurance_days = fields.Integer(compute='_compute_days', store=True)
    expiry_pressure = fields.Float(compute='_compute_risk', store=True)
    risk_score = fields.Float(compute='_compute_risk', store=True)
    risk_level = fields.Selection([('low', 'Low'), ('medium', 'Medium'), ('high', 'High'), ('critical', 'Critical')], compute='_compute_risk', store=True)
    operational_state = fields.Selection([('normal', 'Normal'), ('attention', 'Attention Required'), ('blocked', 'Blocked'), ('exit_process', 'Exit Process')], compute='_compute_risk', store=True)
    travel_readiness = fields.Float(compute='_compute_travel_readiness', store=True)
    service_request_ids = fields.One2many('muqeem.service.request', 'profile_id')
    transaction_ids = fields.One2many('muqeem.operation.transaction', 'profile_id')
    visa_ids = fields.One2many('muqeem.travel.permit', 'profile_id')
    sponsor_transfer_ids = fields.One2many('muqeem.sponsor.transfer', 'profile_id')
    occupation_change_ids = fields.One2many('muqeem.occupation.change', 'profile_id')
    document_ids = fields.One2many('muqeem.workforce.document', 'profile_id')
    fee_ids = fields.One2many('muqeem.government.charge', 'profile_id')
    open_request_count = fields.Integer(compute='_compute_counts')
    failed_transaction_count = fields.Integer(compute='_compute_counts')
    outstanding_charge = fields.Monetary(compute='_compute_counts', currency_field='currency_id')
    currency_id = fields.Many2one(related='company_id.currency_id')
    active = fields.Boolean(default=True)
    notes = fields.Html()
    _sql_constraints = [('employee_unique', 'unique(employee_id)', 'Each employee can have only one Muqeem workforce profile.'), ('iqama_unique', 'unique(iqama_number)', 'Iqama number must be unique when provided.')]

    @api.depends('employee_id')
    def _compute_name(self):
        for r in self:
            r.name = r.employee_id.name or _('Workforce Profile')

    @api.depends('iqama_expiry', 'passport_expiry', 'visa_expiry', 'work_permit_expiry', 'insurance_expiry')
    def _compute_days(self):
        today = fields.Date.context_today(self)
        for r in self:
            for field_name, target in [('iqama_days', r.iqama_expiry), ('passport_days', r.passport_expiry), ('visa_days', r.visa_expiry), ('permit_days', r.work_permit_expiry), ('insurance_days', r.insurance_expiry)]:
                setattr(r, field_name, (target - today).days if target else 99999)

    @api.depends('iqama_days', 'passport_days', 'visa_days', 'permit_days', 'insurance_days', 'travel_status', 'muqeem_status', 'sync_state')
    def _compute_risk(self):
        for r in self:
            penalties = 0.0
            days_list = [r.iqama_days, r.passport_days, r.visa_days, r.permit_days, r.insurance_days]
            weights = [35, 20, 20, 15, 10]
            for days, weight in zip(days_list, weights):
                if days < 0:
                    penalties += weight
                elif days <= 7:
                    penalties += weight * 0.9
                elif days <= 30:
                    penalties += weight * 0.65
                elif days <= 60:
                    penalties += weight * 0.35
                elif days <= 90:
                    penalties += weight * 0.15
            if r.sync_state == 'failed':
                penalties += 10
            if r.muqeem_status in ('suspended', 'final_exit'):
                penalties += 15
            score = max(0.0, min(100.0, 100.0 - penalties))
            r.risk_score = score
            r.expiry_pressure = 100.0 - score
            r.risk_level = 'low' if score >= 85 else 'medium' if score >= 65 else 'high' if score >= 40 else 'critical'
            r.operational_state = 'exit_process' if r.muqeem_status == 'final_exit' else 'blocked' if r.risk_level == 'critical' else 'attention' if r.risk_level in ('high', 'medium') else 'normal'

    @api.depends('iqama_days', 'passport_days', 'visa_days', 'work_permit_expiry', 'insurance_days', 'muqeem_status')
    def _compute_travel_readiness(self):
        for r in self:
            score = 100.0
            for days in [r.iqama_days, r.passport_days, r.visa_days, r.insurance_days]:
                if days < 0:
                    score -= 25
                elif days <= 7:
                    score -= 20
                elif days <= 30:
                    score -= 12
                elif days <= 60:
                    score -= 5
            if r.muqeem_status != 'active':
                score -= 20
            r.travel_readiness = max(0, min(100, score))

    def _compute_counts(self):
        Request = self.env['muqeem.service.request']
        Tx = self.env['muqeem.operation.transaction']
        Charge = self.env['muqeem.government.charge']
        for r in self:
            requests = Request.search([('profile_id', '=', r.id), ('state', 'not in', ('done', 'cancelled', 'rejected'))])
            tx = Tx.search([('profile_id', '=', r.id), ('state', '=', 'failed')])
            charges = Charge.search([('profile_id', '=', r.id), ('state', '=', 'unpaid')])
            r.open_request_count = len(requests)
            r.failed_transaction_count = len(tx)
            r.outstanding_charge = sum(charges.mapped('amount_total'))

    def action_refresh_operational_state(self):
        self._compute_days()
        self._compute_risk()
        self._compute_travel_readiness()
        self._compute_counts()
        return True

    def action_sync_prepare(self):
        self.write({'sync_state': 'queued', 'sync_message': _('Queued for approved Muqeem provider adapter.')})
        self.message_post(body=_('Muqeem synchronization queued.'))
        return True

    def action_open_services(self):
        self.ensure_one()
        return {'type': 'ir.actions.act_window', 'name': _('Government Services'), 'res_model': 'muqeem.service.request', 'view_mode': 'kanban,tree,form', 'domain': [('profile_id', '=', self.id)], 'context': {'default_profile_id': self.id}}

    @api.model
    def cron_risk_engine(self):
        profiles = self.search([('active', '=', True)])
        profiles.action_refresh_operational_state()
        for p in profiles.filtered(lambda x: x.risk_level in ('high', 'critical')):
            p.activity_schedule('mail.mail_activity_data_todo', user_id=self.env.user.id, summary=_('Muqeem risk review'), note=_('Review workforce profile %s. Risk score %.1f.') % (p.name, p.risk_score))
        return True

class MuqeemServiceRequest(models.Model):
    _name = 'muqeem.service.request'
    _description = 'Muqeem Service Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'priority desc, deadline asc, id desc'
    name = fields.Char(default=lambda self: _('New'), readonly=True, copy=False)
    profile_id = fields.Many2one('muqeem.workforce.profile', required=True, ondelete='restrict', index=True)
    employee_id = fields.Many2one(related='profile_id.employee_id', store=True)
    company_id = fields.Many2one(related='profile_id.company_id', store=True)
    service_code = fields.Selection([('iqama_renew', 'Iqama Renewal'), ('iqama_replace', 'Iqama Replacement'), ('iqama_missing', 'Missing Iqama'), ('exit_reentry', 'Exit/Re-Entry'), ('exit_reentry_extend', 'Extend Exit/Re-Entry'), ('exit_reentry_cancel', 'Cancel Exit/Re-Entry'), ('final_exit', 'Final Exit'), ('final_exit_cancel', 'Cancel Final Exit'), ('sponsor_transfer', 'Sponsor Transfer'), ('occupation_change', 'Occupation Change'), ('resident_report', 'Resident Report'), ('visa_report', 'Visa Report')], required=True)
    state = fields.Selection([('draft', 'Draft'), ('precheck', 'Pre-check'), ('documents', 'Document Gate'), ('approval', 'Approval'), ('payment', 'Payment'), ('ready', 'Ready'), ('submitted', 'Submitted'), ('government', 'Government Processing'), ('query', 'Correction Required'), ('approved', 'Government Approved'), ('done', 'Completed'), ('rejected', 'Rejected'), ('cancelled', 'Cancelled')], default='draft', tracking=True)
    priority = fields.Selection([('0', 'Normal'), ('1', 'Important'), ('2', 'Urgent'), ('3', 'Critical')], default='0')
    requested_by = fields.Many2one('res.users', default=lambda self: self.env.user, readonly=True)
    responsible_id = fields.Many2one('res.users', default=lambda self: self.env.user)
    approver_id = fields.Many2one('res.users')
    request_date = fields.Datetime(default=fields.Datetime.now, readonly=True)
    submitted_at = fields.Datetime(readonly=True)
    completed_at = fields.Datetime(readonly=True)
    sla_hours = fields.Integer(default=24)
    deadline = fields.Datetime(compute='_compute_deadline', store=True)
    sla_state = fields.Selection([('on_track', 'On Track'), ('warning', 'Warning'), ('breached', 'Breached')], compute='_compute_sla', store=True)
    age_hours = fields.Float(compute='_compute_sla', store=True)
    eligibility_score = fields.Float(compute='_compute_eligibility', store=True)
    eligibility_state = fields.Selection([('pass', 'Pass'), ('review', 'Review'), ('fail', 'Fail')], compute='_compute_eligibility', store=True)
    document_gate = fields.Selection([('pass', 'Pass'), ('missing', 'Missing'), ('expired', 'Expired')], compute='_compute_document_gate', store=True)
    payment_gate = fields.Selection([('not_required', 'Not Required'), ('pending', 'Pending'), ('paid', 'Paid')], compute='_compute_payment_gate', store=True)
    government_reference = fields.Char(index=True)
    external_message = fields.Text()
    rejection_reason = fields.Text()
    checklist_ids = fields.One2many('muqeem.service.check', 'request_id')
    transaction_ids = fields.One2many('muqeem.operation.transaction', 'request_id')
    charge_ids = fields.One2many('muqeem.government.charge', 'request_id')
    attachment_ids = fields.Many2many('ir.attachment', 'muqeem_request_attachment_rel', 'request_id', 'attachment_id')
    notes = fields.Html()
    can_submit = fields.Boolean(compute='_compute_can_submit')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('muqeem.service.request') or _('New')
        recs = super().create(vals_list)
        for rec in recs:
            rec._create_checklist()
            if rec.service_code in ('iqama_renew', 'iqama_replace', 'exit_reentry', 'final_exit', 'sponsor_transfer'):
                rec.charge_ids = [(0, 0, {'name': _('Government service charge'), 'profile_id': rec.profile_id.id, 'amount': 0, 'fee_type': 'government'})]
        return recs

    @api.depends('request_date', 'sla_hours')
    def _compute_deadline(self):
        for r in self:
            r.deadline = r.request_date + timedelta(hours=r.sla_hours or 24) if r.request_date else False

    @api.depends('request_date', 'deadline', 'state')
    def _compute_sla(self):
        now = fields.Datetime.now()
        for r in self:
            r.age_hours = (now - r.request_date).total_seconds() / 3600 if r.request_date else 0
            if r.state in ('done', 'cancelled', 'rejected'):
                r.sla_state = 'on_track'
            elif r.deadline and now > r.deadline:
                r.sla_state = 'breached'
            elif r.deadline and (r.deadline - now).total_seconds() < (r.sla_hours or 24) * 3600 * 0.25:
                r.sla_state = 'warning'
            else:
                r.sla_state = 'on_track'

    @api.depends('profile_id.risk_score', 'document_gate', 'payment_gate', 'service_code')
    def _compute_eligibility(self):
        for r in self:
            score = r.profile_id.risk_score
            if r.service_code in ('final_exit', 'final_exit_cancel'):
                score += 5
            if r.profile_id.muqeem_status == 'suspended':
                score -= 25
            if r.document_gate == 'expired':
                score -= 35
            if r.document_gate == 'missing':
                score -= 20
            r.eligibility_score = max(0, min(100, score))
            r.eligibility_state = 'pass' if r.eligibility_score >= 80 else 'review' if r.eligibility_score >= 55 else 'fail'

    @api.depends('profile_id.iqama_days', 'profile_id.passport_days', 'profile_id.visa_days', 'service_code')
    def _compute_document_gate(self):
        for r in self:
            days = []
            # if r.service_code.startswith('iqama'):
            #     days.append(r.profile_id.iqama_days)
            if r.service_code in ('exit_reentry', 'exit_reentry_extend', 'exit_reentry_cancel', 'final_exit', 'final_exit_cancel'):
                days.extend([r.profile_id.iqama_days, r.profile_id.passport_days])
            if r.service_code == 'sponsor_transfer':
                days.append(r.profile_id.iqama_days)
            if any((x < 0 for x in days)):
                r.document_gate = 'expired'
            elif any((x == 99999 for x in days)):
                r.document_gate = 'missing'
            else:
                r.document_gate = 'pass'

    @api.depends('charge_ids.state', 'service_code')
    def _compute_payment_gate(self):
        for r in self:
            if not r.charge_ids:
                r.payment_gate = 'not_required'
            elif all((x.state in ('paid', 'waived') for x in r.charge_ids)):
                r.payment_gate = 'paid'
            else:
                r.payment_gate = 'pending'

    def _compute_can_submit(self):
        for r in self:
            r.can_submit = r.state == 'ready' and r.eligibility_state != 'fail' and (r.document_gate == 'pass') and (r.payment_gate in ('paid', 'not_required'))

    def _create_checklist(self):
        labels = [('identity', 'Identity verified'), ('residency', 'Residency status checked'), ('passport', 'Passport checked'), ('documents', 'Required documents ready'), ('fees', 'Fees settled'), ('approval', 'Approval completed')]
        for code, label in labels:
            self.env['muqeem.service.check'].create({'request_id': self.id, 'code': code, 'name': label, 'required': code in ('identity', 'residency', 'documents')})

    def action_start(self):
        self.write({'state': 'precheck'})

    def action_precheck(self):
        self._compute_document_gate()
        self._compute_eligibility()
        if self.eligibility_state == 'fail':
            self.write({'state': 'query', 'external_message': _('Eligibility score is below the automatic submission threshold.')})
        else:
            self.write({'state': 'documents'})

    def action_validate_documents(self):
        self._compute_document_gate()
        if self.document_gate != 'pass':
            raise UserError(_('The document gate is not satisfied.'))
        self.checklist_ids.filtered(lambda x: x.code == 'documents').write({'completed': True, 'completed_by': self.env.user.id, 'completed_at': fields.Datetime.now()})
        self.write({'state': 'approval'})

    def action_approve(self):
        self.checklist_ids.filtered(lambda x: x.code == 'approval').write({'completed': True, 'completed_by': self.env.user.id, 'completed_at': fields.Datetime.now()})
        self._compute_payment_gate()
        self.write({'state': 'payment' if self.payment_gate == 'pending' else 'ready'})

    def action_register_payment(self):
        self.charge_ids.filtered(lambda x: x.state == 'unpaid').write({'state': 'paid', 'paid_date': fields.Date.context_today(self)})
        self.write({'state': 'ready'})

    def action_submit(self):
        for r in self:
            if not r.can_submit:
                raise UserError(_('Request is not ready for government submission.'))
            r.write({'state': 'submitted', 'submitted_at': fields.Datetime.now()})
            tx = self.env['muqeem.operation.transaction'].create({'profile_id': r.profile_id.id, 'request_id': r.id, 'operation': r.service_code, 'state': 'queued', 'request_payload': r._payload()})
            r.message_post(body=_('Government transaction %s queued.') % tx.name)

    def action_process(self):
        for r in self:
            tx = r.transaction_ids.filtered(lambda x: x.state in ('queued', 'processing', 'submitted'))[:1]
            if not tx:
                raise UserError(_('No government transaction is available.'))
            tx.action_process()
            if tx.state == 'success':
                r.write({'state': 'approved', 'government_reference': tx.external_reference})
                r._apply_success(tx)
                r.write({'state': 'done', 'completed_at': fields.Datetime.now()})
            elif tx.state == 'failed':
                r.write({'state': 'query'})

    def _payload(self):
        self.ensure_one()
        return {'service': self.service_code, 'employee': self.employee_id.id, 'iqama': self.profile_id.iqama_number, 'passport': self.profile_id.passport_number, 'sponsor': self.profile_id.sponsor_id, 'request': self.name}

    def _apply_success(self, tx):
        if self.service_code == 'final_exit':
            self.profile_id.muqeem_status = 'final_exit'
        elif self.service_code == 'sponsor_transfer':
            self.profile_id.muqeem_status = 'transferred'
        elif self.service_code == 'occupation_change':
            pass

    def action_reject(self):
        self.write({'state': 'rejected'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})

class MuqeemServiceCheck(models.Model):
    _name = 'muqeem.service.check'
    _description = 'Muqeem Service Checklist'
    _order = 'sequence,id'
    request_id = fields.Many2one('muqeem.service.request', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    code = fields.Char(required=True)
    name = fields.Char(required=True)
    required = fields.Boolean()
    completed = fields.Boolean()
    completed_by = fields.Many2one('res.users')
    completed_at = fields.Datetime()
    note = fields.Char()

    def action_complete(self):
        self.write({'completed': True, 'completed_by': self.env.user.id, 'completed_at': fields.Datetime.now()})

class MuqeemOperationTransaction(models.Model):
    _name = 'muqeem.operation.transaction'
    _description = 'Muqeem Operation Transaction'
    _inherit = ['mail.thread']
    _order = 'create_date desc'
    name = fields.Char(default=lambda self: _('New'), readonly=True, copy=False)
    profile_id = fields.Many2one('muqeem.workforce.profile', required=True, ondelete='restrict')
    request_id = fields.Many2one('muqeem.service.request', ondelete='cascade')
    operation = fields.Char(required=True)
    state = fields.Selection([('queued', 'Queued'), ('submitted', 'Submitted'), ('processing', 'Processing'), ('success', 'Success'), ('failed', 'Failed'), ('cancelled', 'Cancelled')], default='queued', tracking=True)
    provider_mode = fields.Selection([('manual', 'Manual Assisted'), ('sandbox', 'Sandbox'), ('production', 'Production')], default='manual')
    request_payload = fields.Json()
    response_payload = fields.Json()
    external_reference = fields.Char(index=True)
    error_code = fields.Char()
    error_message = fields.Text()
    started_at = fields.Datetime()
    completed_at = fields.Datetime()
    duration_seconds = fields.Float(compute='_compute_duration', store=True)
    attempt = fields.Integer(default=1)

    @api.model_create_multi
    def create(self, vals_list):
        for v in vals_list:
            if v.get('name', _('New')) == _('New'):
                v['name'] = self.env['ir.sequence'].next_by_code('muqeem.operation.transaction') or _('New')
        return super().create(vals_list)

    @api.depends('started_at', 'completed_at')
    def _compute_duration(self):
        for r in self:
            r.duration_seconds = (r.completed_at - r.started_at).total_seconds() if r.started_at and r.completed_at else 0

    def action_process(self):
        for r in self:
            r.started_at = fields.Datetime.now()
            r.state = 'processing'
            if r.provider_mode == 'manual':
                r.response_payload = {'mode': 'manual_assisted', 'instruction': 'Execute using authorized Muqeem portal/provider and enter the government reference.'}
                r.external_reference = 'MANUAL-' + str(r.id).zfill(7)
                r.state = 'success'
            else:
                r.response_payload = {'mode': r.provider_mode, 'status': 'adapter_required'}
                r.external_reference = 'SIM-' + str(r.id).zfill(7)
                r.state = 'success'
            r.completed_at = fields.Datetime.now()

    def action_retry(self):
        for r in self:
            r.write({'state': 'queued', 'attempt': r.attempt + 1})

class MuqeemTravelPermit(models.Model):
    _name = 'muqeem.travel.permit'
    _description = 'Exit Re-entry and Final Exit Permit'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'return_before desc'
    name = fields.Char(compute='_compute_name', store=True)
    profile_id = fields.Many2one('muqeem.workforce.profile', required=True, ondelete='cascade')
    permit_type = fields.Selection([('single_exit_reentry', 'Single Exit/Re-Entry'), ('multiple_exit_reentry', 'Multiple Exit/Re-Entry'), ('final_exit', 'Final Exit')], required=True)
    permit_number = fields.Char(index=True)
    issue_date = fields.Date()
    expiry_date = fields.Date()
    return_before = fields.Date()
    travel_date = fields.Date()
    expected_return = fields.Date()
    actual_return = fields.Date()
    destination_id = fields.Many2one('res.country')
    state = fields.Selection([('draft', 'Draft'), ('requested', 'Requested'), ('active', 'Active'), ('used', 'Used'), ('expired', 'Expired'), ('cancelled', 'Cancelled')], default='draft', tracking=True)
    days_to_return = fields.Integer(compute='_compute_days', store=True)
    travel_risk = fields.Selection([('green', 'Green'), ('amber', 'Amber'), ('red', 'Red')], compute='_compute_risk', store=True)
    travel_risk_reason = fields.Text(compute='_compute_risk', store=True)
    notes = fields.Html()

    @api.depends('permit_number', 'profile_id.name')
    def _compute_name(self):
        for r in self:
            r.name = '%s — %s' % (r.profile_id.name, r.permit_number or _('Pending'))

    @api.depends('return_before', 'expected_return')
    def _compute_days(self):
        today = fields.Date.context_today(self)
        for r in self:
            d = r.return_before or r.expected_return
            r.days_to_return = (d - today).days if d else 99999

    @api.depends('days_to_return', 'expected_return', 'return_before', 'profile_id.iqama_days', 'profile_id.passport_days', 'state')
    def _compute_risk(self):
        for r in self:
            reasons = []
            risk = 'green'
            if r.days_to_return < 0:
                risk = 'red'
                reasons.append(_('Return validity has expired.'))
            elif r.days_to_return <= 3:
                risk = 'red'
                reasons.append(_('Return validity is within three days.'))
            elif r.days_to_return <= 14:
                risk = 'amber'
                reasons.append(_('Return validity is within two weeks.'))
            if r.expected_return and r.return_before and (r.expected_return > r.return_before):
                risk = 'red'
                reasons.append(_('Expected return is after permitted return-before date.'))
            if r.profile_id.iqama_days < 30:
                risk = 'amber' if risk == 'green' else risk
                reasons.append(_('Iqama validity is short.'))
            if r.profile_id.passport_days < 30:
                risk = 'red'
                reasons.append(_('Passport validity is critically short.'))
            r.travel_risk = risk
            r.travel_risk_reason = ' '.join(reasons)

class MuqeemSponsorTransfer(models.Model):
    _name = 'muqeem.sponsor.transfer'
    _description = 'Muqeem Sponsorship Transfer'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    name = fields.Char(default=lambda self: _('New'), readonly=True, copy=False)
    profile_id = fields.Many2one('muqeem.workforce.profile', required=True, ondelete='restrict')
    current_sponsor_id = fields.Char(required=True)
    current_sponsor_name = fields.Char()
    new_sponsor_id = fields.Char(required=True)
    new_sponsor_name = fields.Char(required=True)
    state = fields.Selection([('draft', 'Draft'), ('eligibility', 'Eligibility'), ('approval', 'Approval'), ('payment', 'Payment'), ('submitted', 'Submitted'), ('acceptance', 'New Sponsor Acceptance'), ('processing', 'Processing'), ('done', 'Completed'), ('rejected', 'Rejected')], default='draft', tracking=True)
    eligibility_score = fields.Float(compute='_compute_eligibility', store=True)
    blockers = fields.Text(compute='_compute_eligibility', store=True)
    fee = fields.Monetary()
    fee_paid = fields.Boolean()
    currency_id = fields.Many2one(related='profile_id.currency_id')
    reason = fields.Text(required=True)
    government_reference = fields.Char()

    @api.model_create_multi
    def create(self, vals_list):
        for v in vals_list:
            if v.get('name', _('New')) == _('New'):
                v['name'] = self.env['ir.sequence'].next_by_code('muqeem.sponsor.transfer') or _('New')
        return super().create(vals_list)

    @api.depends('current_sponsor_id', 'new_sponsor_id', 'profile_id.risk_score', 'profile_id.muqeem_status')
    def _compute_eligibility(self):
        for r in self:
            score = 100
            blockers = []
            if r.current_sponsor_id == r.new_sponsor_id:
                score -= 100
                blockers.append(_('Sponsor identifiers are identical.'))
            if r.profile_id.muqeem_status in ('final_exit', 'suspended'):
                score -= 60
                blockers.append(_('Resident status requires resolution before transfer.'))
            if r.profile_id.risk_score < 40:
                score -= 25
                blockers.append(_('Critical compliance risk requires manager review.'))
            r.eligibility_score = max(0, score)
            r.blockers = '\n'.join(blockers)

    def action_check(self):
        self.write({'state': 'approval' if self.eligibility_score >= 60 else 'eligibility'})

    def action_approve(self):
        self.write({'state': 'payment' if self.fee else 'submitted'})

    def action_pay(self):
        self.write({'fee_paid': True, 'state': 'submitted'})

    def action_submit(self):
        self.write({'state': 'acceptance'})

    def action_accept(self):
        self.write({'state': 'processing'})

    def action_complete(self):
        self.profile_id.write({'sponsor_id': self.new_sponsor_id, 'sponsor_name': self.new_sponsor_name, 'muqeem_status': 'transferred'})
        self.write({'state': 'done', 'government_reference': 'TRANSFER-%07d' % self.id})

class MuqeemOccupationChange(models.Model):
    _name = 'muqeem.occupation.change'
    _description = 'Muqeem Occupation Change'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    name = fields.Char(default=lambda self: _('New'), readonly=True, copy=False)
    profile_id = fields.Many2one('muqeem.workforce.profile', required=True, ondelete='restrict')
    current_occupation = fields.Char(related='profile_id.profession', store=True)
    current_code = fields.Char(related='profile_id.profession_code', store=True)
    new_occupation = fields.Char(required=True)
    new_code = fields.Char()
    reason = fields.Text(required=True)
    state = fields.Selection([('draft', 'Draft'), ('eligibility', 'Eligibility'), ('approval', 'Approval'), ('government', 'Government Review'), ('done', 'Completed'), ('rejected', 'Rejected')], default='draft', tracking=True)
    eligibility_score = fields.Float(compute='_compute_score', store=True)

    @api.model_create_multi
    def create(self, vals_list):
        for v in vals_list:
            if v.get('name', _('New')) == _('New'):
                v['name'] = self.env['ir.sequence'].next_by_code('muqeem.occupation.change') or _('New')
        return super().create(vals_list)

    @api.depends('new_occupation', 'current_occupation', 'profile_id.risk_score')
    def _compute_score(self):
        for r in self:
            score = 100
            if r.new_occupation == r.current_occupation:
                score = 10
            if r.profile_id.risk_score < 40:
                score -= 25
            r.eligibility_score = max(0, score)

    def action_check(self):
        self.write({'state': 'approval' if self.eligibility_score >= 70 else 'eligibility'})

    def action_approve(self):
        self.write({'state': 'government'})

    def action_complete(self):
        self.profile_id.write({'profession': self.new_occupation, 'profession_code': self.new_code})
        self.write({'state': 'done'})

class MuqeemWorkforceDocument(models.Model):
    _name = 'muqeem.workforce.document'
    _description = 'Muqeem Workforce Document'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    name = fields.Char(required=True)
    profile_id = fields.Many2one('muqeem.workforce.profile', required=True, ondelete='cascade')
    document_type = fields.Selection([('iqama', 'Iqama'), ('passport', 'Passport'), ('visa', 'Visa'), ('work_permit', 'Work Permit'), ('insurance', 'Medical Insurance'), ('contract', 'Employment Contract'), ('other', 'Other')], required=True)
    number = fields.Char()
    issue_date = fields.Date()
    expiry_date = fields.Date()
    state = fields.Selection([('draft', 'Draft'), ('valid', 'Valid'), ('expiring', 'Expiring'), ('expired', 'Expired'), ('cancelled', 'Cancelled')], compute='_compute_state', store=True)
    days_remaining = fields.Integer(compute='_compute_state', store=True)
    verification = fields.Selection([('pending', 'Pending'), ('verified', 'Verified'), ('rejected', 'Rejected')], default='pending')
    attachment_id = fields.Many2one('ir.attachment')
    notes = fields.Text()
    active = fields.Boolean(default=True)

    @api.depends('expiry_date', 'active')
    def _compute_state(self):
        today = fields.Date.context_today(self)
        for r in self:
            if not r.active:
                r.state = 'cancelled'
                r.days_remaining = 0
            elif not r.expiry_date:
                r.state = 'valid'
                r.days_remaining = 99999
            else:
                r.days_remaining = (r.expiry_date - today).days
                r.state = 'expired' if r.days_remaining < 0 else 'expiring' if r.days_remaining <= 60 else 'valid'

    def action_verify(self):
        self.write({'verification': 'verified'})

class MuqeemGovernmentCharge(models.Model):
    _name = 'muqeem.government.charge'
    _description = 'Muqeem Government Charge'
    _inherit = ['mail.thread']
    name = fields.Char(required=True)
    profile_id = fields.Many2one('muqeem.workforce.profile', required=True, ondelete='cascade')
    request_id = fields.Many2one('muqeem.service.request', ondelete='cascade')
    fee_type = fields.Selection([('government', 'Government'), ('service', 'Service'), ('insurance', 'Insurance'), ('admin', 'Administrative')], required=True)
    amount = fields.Monetary(required=True)
    vat = fields.Monetary()
    amount_total = fields.Monetary(compute='_compute_total', store=True)
    currency_id = fields.Many2one(related='profile_id.currency_id')
    state = fields.Selection([('unpaid', 'Unpaid'), ('paid', 'Paid'), ('waived', 'Waived'), ('cancelled', 'Cancelled')], default='unpaid', tracking=True)
    due_date = fields.Date()
    paid_date = fields.Date()
    payment_reference = fields.Char()

    @api.depends('amount', 'vat')
    def _compute_total(self):
        for r in self:
            r.amount_total = r.amount + r.vat

    def action_paid(self):
        self.write({'state': 'paid', 'paid_date': fields.Date.context_today(self)})

    def action_waive(self):
        self.write({'state': 'waived'})

class MuqeemCommandCenter(models.TransientModel):
    _name = 'muqeem.command.center'
    _description = 'Muqeem Command Center'
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    as_of = fields.Date(default=fields.Date.context_today)
    residents = fields.Integer(compute='_compute')
    active = fields.Integer(compute='_compute')
    critical = fields.Integer(compute='_compute')
    high = fields.Integer(compute='_compute')
    iqama_expired = fields.Integer(compute='_compute')
    iqama_30 = fields.Integer(compute='_compute')
    iqama_60 = fields.Integer(compute='_compute')
    iqama_90 = fields.Integer(compute='_compute')
    passport_expired = fields.Integer(compute='_compute')
    visa_expired = fields.Integer(compute='_compute')
    open_requests = fields.Integer(compute='_compute')
    overdue_requests = fields.Integer(compute='_compute')
    queued_transactions = fields.Integer(compute='_compute')
    failed_transactions = fields.Integer(compute='_compute')
    unpaid_charges = fields.Monetary(compute='_compute', currency_field='currency_id')
    average_risk = fields.Float(compute='_compute')
    average_travel_readiness = fields.Float(compute='_compute')
    currency_id = fields.Many2one(related='company_id.currency_id')

    def _compute(self):
        Profile = self.env['muqeem.workforce.profile']
        Request = self.env['muqeem.service.request']
        Tx = self.env['muqeem.operation.transaction']
        Charge = self.env['muqeem.government.charge']
        for r in self:
            ps = Profile.search([('company_id', '=', r.company_id.id), ('active', '=', True)])
            r.residents = len(ps)
            r.active = len(ps.filtered(lambda x: x.muqeem_status == 'active'))
            r.critical = len(ps.filtered(lambda x: x.risk_level == 'critical'))
            r.high = len(ps.filtered(lambda x: x.risk_level == 'high'))
            r.iqama_expired = len(ps.filtered(lambda x: x.iqama_days < 0))
            r.iqama_30 = len(ps.filtered(lambda x: 0 <= x.iqama_days <= 30))
            r.iqama_60 = len(ps.filtered(lambda x: 31 <= x.iqama_days <= 60))
            r.iqama_90 = len(ps.filtered(lambda x: 61 <= x.iqama_days <= 90))
            r.passport_expired = len(ps.filtered(lambda x: x.passport_days < 0))
            r.visa_expired = len(ps.filtered(lambda x: x.visa_days < 0))
            req = Request.search([('company_id', '=', r.company_id.id), ('state', 'not in', ('done', 'cancelled', 'rejected'))])
            r.open_requests = len(req)
            r.overdue_requests = len(req.filtered(lambda x: x.sla_state == 'breached'))
            tx = Tx.search([('profile_id.company_id', '=', r.company_id.id)])
            r.queued_transactions = len(tx.filtered(lambda x: x.state in ('queued', 'submitted', 'processing')))
            r.failed_transactions = len(tx.filtered(lambda x: x.state == 'failed'))
            charges = Charge.search([('profile_id.company_id', '=', r.company_id.id), ('state', '=', 'unpaid')])
            r.unpaid_charges = sum(charges.mapped('amount_total'))
            r.average_risk = sum(ps.mapped('risk_score')) / len(ps) if ps else 100
            r.average_travel_readiness = sum(ps.mapped('travel_readiness')) / len(ps) if ps else 100
