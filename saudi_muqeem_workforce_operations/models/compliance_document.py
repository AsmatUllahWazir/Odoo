from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import timedelta

class SaudiComplianceDocumentType(models.Model):
    _name = 'saudi.compliance.document.type'
    _description = 'Saudi Compliance Document Type'
    _order = 'sequence, name'
    name = fields.Char(required=True, translate=True)
    code = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    required_for_non_saudi = fields.Boolean(default=True)
    required_for_saudi = fields.Boolean(default=False)
    expiry_required = fields.Boolean(default=True)
    reminder_days = fields.Integer(default=30)
    color = fields.Integer(default=1)
    active = fields.Boolean(default=True)
    description = fields.Text(translate=True)
    _sql_constraints = [('code_unique', 'unique(code)', 'Document type code must be unique.')]

class SaudiComplianceDocument(models.Model):
    _name = 'saudi.compliance.document'
    _description = 'Saudi Employee Compliance Document'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'expiry_date asc, id desc'
    name = fields.Char(required=True, tracking=True)
    employee_id = fields.Many2one('hr.employee', required=True, ondelete='cascade', tracking=True)
    company_id = fields.Many2one(related='employee_id.company_id', store=True)
    document_type_id = fields.Many2one('saudi.compliance.document.type', required=True, tracking=True)
    document_number = fields.Char(tracking=True)
    issue_date = fields.Date(tracking=True)
    expiry_date = fields.Date(tracking=True)
    reminder_days = fields.Integer(related='document_type_id.reminder_days', store=True)
    state = fields.Selection([('draft', 'Draft'), ('valid', 'Valid'), ('expiring', 'Expiring Soon'), ('expired', 'Expired'), ('cancelled', 'Cancelled')], compute='_compute_state', store=True, tracking=True)
    days_to_expiry = fields.Integer(compute='_compute_state', store=True)
    is_required = fields.Boolean(compute='_compute_required', store=True)
    attachment_id = fields.Many2one('ir.attachment', string='Primary Attachment')
    attachment_count = fields.Integer(compute='_compute_attachment_count')
    notes = fields.Text()
    active = fields.Boolean(default=True)

    @api.depends('expiry_date', 'reminder_days', 'active')
    def _compute_state(self):
        today = fields.Date.context_today(self)
        for rec in self:
            if not rec.active:
                rec.state = 'cancelled'
                rec.days_to_expiry = 0
                continue
            if not rec.expiry_date:
                rec.state = 'draft'
                rec.days_to_expiry = 0
                continue
            rec.days_to_expiry = (rec.expiry_date - today).days
            if rec.expiry_date < today:
                rec.state = 'expired'
            elif rec.expiry_date <= today + timedelta(days=rec.reminder_days or 30):
                rec.state = 'expiring'
            else:
                rec.state = 'valid'

    @api.depends('employee_id.saudi_employee_type', 'document_type_id.required_for_non_saudi', 'document_type_id.required_for_saudi')
    def _compute_required(self):
        for rec in self:
            if rec.employee_id.saudi_employee_type == 'saudi':
                rec.is_required = rec.document_type_id.required_for_saudi
            else:
                rec.is_required = rec.document_type_id.required_for_non_saudi

    def _compute_attachment_count(self):
        Attachment = self.env['ir.attachment']
        for rec in self:
            rec.attachment_count = Attachment.search_count([('res_model', '=', self._name), ('res_id', '=', rec.id)])

    @api.constrains('issue_date', 'expiry_date')
    def _check_dates(self):
        for rec in self:
            if rec.issue_date and rec.expiry_date and (rec.expiry_date < rec.issue_date):
                raise ValidationError(_('Expiry date cannot be before issue date.'))

    def action_open_attachments(self):
        self.ensure_one()
        return {'type': 'ir.actions.act_window', 'name': _('Attachments'), 'res_model': 'ir.attachment', 'view_mode': 'kanban,tree,form', 'domain': [('res_model', '=', self._name), ('res_id', '=', self.id)], 'context': {'default_res_model': self._name, 'default_res_id': self.id}}

    @api.model
    def cron_refresh_states(self):
        records = self.search([('active', '=', True)])
        records._compute_state()
        expiring = records.filtered(lambda r: r.state in ('expiring', 'expired'))
        for rec in expiring:
            if rec.employee_id.parent_id.user_id:
                rec.activity_schedule('mail.mail_activity_data_todo', user_id=rec.employee_id.parent_id.user_id.id, summary=_('Compliance document requires attention'), note=_('%s for %s is %s.') % (rec.name, rec.employee_id.name, rec.state))
        return True
