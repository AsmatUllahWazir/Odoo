# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class DocumentRenewWizard(models.TransientModel):
    _name = 'document.renew.wizard'
    _description = 'Renew Document Expiry'

    document_id = fields.Many2one('document.expiry', required=True, string='Document')
    old_expiry_date = fields.Date(related='document_id.expiry_date', string='Current Expiry Date', readonly=True)
    new_issue_date = fields.Date(string='New Issue Date')
    new_expiry_date = fields.Date(required=True, string='New Expiry Date')
    note = fields.Text(string='Renewal Note')

    @api.constrains('new_expiry_date', 'new_issue_date')
    def _check_dates(self):
        for rec in self:
            if rec.new_issue_date and rec.new_expiry_date and rec.new_issue_date > rec.new_expiry_date:
                raise ValidationError(_("The new expiry date must be after the new issue date."))

    def action_renew(self):
        self.ensure_one()
        document = self.document_id
        vals = {
            'expiry_date': self.new_expiry_date,
            'state': 'valid',
            'reminders_sent': '',
        }
        if self.new_issue_date:
            vals['issue_date'] = self.new_issue_date
        document.write(vals)
        body = _("Document renewed. New expiry date: %s.") % self.new_expiry_date
        if self.note:
            body += "<br/>%s" % self.note
        document.message_post(body=body)
        return {'type': 'ir.actions.act_window_close'}
