from odoo import api, fields, models, _

class SaudiBulkReminderWizard(models.TransientModel):
    _name = 'saudi.bulk.reminder.wizard'
    _description = 'Saudi Compliance Bulk Reminder Wizard'
    document_ids = fields.Many2many('saudi.compliance.document')
    recipient_mode = fields.Selection([('manager', 'Employee Manager'), ('owner', 'Compliance Owner'), ('manual', 'Manual User')], default='manager', required=True)
    user_id = fields.Many2one('res.users')
    subject = fields.Char(default='Saudi HR compliance reminder', required=True)
    body = fields.Html(default='<p>Please review the attached compliance item.</p>')

    def action_send(self):
        Mail = self.env['mail.mail'].sudo()
        for document in self.document_ids:
            recipient = False
            if self.recipient_mode == 'manager':
                recipient = document.employee_id.parent_id.work_email
            elif self.recipient_mode == 'owner':
                recipient = self.env['res.config.settings'].sudo().get_values().get('default_document_owner_id')
            elif self.recipient_mode == 'manual' and self.user_id:
                recipient = self.user_id.partner_id.email
            if isinstance(recipient, str) and recipient:
                Mail.create({'subject': self.subject, 'body_html': self.body, 'email_to': recipient}).send()
        return {'type': 'ir.actions.act_window_close'}
