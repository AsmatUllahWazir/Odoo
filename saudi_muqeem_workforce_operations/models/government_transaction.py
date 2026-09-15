from odoo import api, fields, models, _
from odoo.exceptions import UserError

class SaudiGovernmentTransaction(models.Model):
    _name = 'saudi.government.transaction'
    _description = 'Saudi Government Transaction'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'request_date desc, id desc'
    name = fields.Char(default='New', required=True, copy=False, tracking=True)
    employee_id = fields.Many2one('hr.employee', required=True, ondelete='cascade', tracking=True)
    company_id = fields.Many2one(related='employee_id.company_id', store=True)
    service_type = fields.Selection([('iqama_renewal', 'Iqama Renewal'), ('iqama_issue', 'Iqama Issue'), ('iqama_transfer', 'Sponsorship Transfer'), ('exit_reentry_issue', 'Issue Exit/Re-entry'), ('exit_reentry_extend', 'Extend Exit/Re-entry'), ('exit_reentry_cancel', 'Cancel Exit/Re-entry'), ('final_exit', 'Final Exit'), ('final_exit_cancel', 'Cancel Final Exit'), ('visa_issue', 'Visa Issue'), ('visa_cancel', 'Visa Cancellation'), ('profession_change', 'Profession Change'), ('work_permit', 'Work Permit'), ('contract_update', 'Employment Contract Update'), ('gosi_update', 'GOSI Update'), ('other', 'Other')], required=True, tracking=True)
    provider = fields.Selection([('manual', 'Manual'), ('muqeem', 'Muqeem'), ('qiwa', 'Qiwa'), ('gosi', 'GOSI'), ('mudad', 'Mudad'), ('other', 'Other')], default='manual', required=True)
    request_date = fields.Datetime(default=fields.Datetime.now, required=True, tracking=True)
    requested_by = fields.Many2one('res.users', default=lambda self: self.env.user, readonly=True)
    reference = fields.Char(tracking=True)
    external_reference = fields.Char(string='Government Reference', tracking=True)
    state = fields.Selection([('draft', 'Draft'), ('submitted', 'Submitted'), ('processing', 'Processing'), ('done', 'Completed'), ('failed', 'Failed'), ('cancelled', 'Cancelled')], default='draft', tracking=True)
    request_payload = fields.Text(string='Request Data')
    response_payload = fields.Text(string='Response Data')
    error_message = fields.Text()
    result_date = fields.Datetime(readonly=True)
    old_value = fields.Char()
    new_value = fields.Char()
    attachment_ids = fields.Many2many('ir.attachment', string='Government Documents')
    notes = fields.Text()

    def action_submit(self):
        for rec in self:
            if rec.state != 'draft':
                continue
            if rec.name == 'New':
                rec.name = self.env['ir.sequence'].next_by_code('saudi.government.transaction') or 'New'
            rec.write({'state': 'submitted'})
        return True

    def action_start_processing(self):
        self.write({'state': 'processing'})
        return True

    def action_complete(self):
        self.write({'state': 'done', 'result_date': fields.Datetime.now()})
        return True

    def action_fail(self):
        self.write({'state': 'failed', 'result_date': fields.Datetime.now()})
        return True

    def action_cancel(self):
        self.write({'state': 'cancelled'})
        return True

    def action_retry(self):
        for rec in self:
            if rec.state != 'failed':
                raise UserError(_('Only failed transactions can be retried.'))
            rec.write({'state': 'submitted', 'error_message': False})
        return True
