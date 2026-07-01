# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class VendorBillRejectWizard(models.TransientModel):
    _name = 'vendor.bill.reject.wizard'
    _description = 'Vendor Bill Rejection Wizard'

    invoice_id = fields.Many2one(
        'account.move',
        string='Invoice',
        required=True,
        ondelete='cascade',
    )

    rejection_reason = fields.Text(
        string='Rejection Reason',
        required=True,
        help='Please provide a detailed reason for rejection',
    )

    notify_submitter = fields.Boolean(
        string='Notify Submitter',
        default=True,
        help='Send notification to the person who submitted this invoice',
    )

    @api.constrains('rejection_reason')
    def _check_rejection_reason(self):
        for wizard in self:
            if not wizard.rejection_reason or len(wizard.rejection_reason.strip()) < 10:
                raise ValidationError(_('Rejection reason must be at least 10 characters long.'))

    def action_reject(self):
        """Reject the invoice with reason"""
        self.ensure_one()

        self.invoice_id.write({
            'dispatch_state': 'rejected',
            'rejection_reason': self.rejection_reason,
            'rejected_by': self.env.user.id,
            'rejected_date': fields.Datetime.now(),
        })

        self.env['vendor.bill.validation.history'].create({
            'invoice_id': self.invoice_id.id,
            'action': 'rejected',
            'user_id': self.env.user.id,
            'timestamp': fields.Datetime.now(),
            'rejection_reason': self.rejection_reason,
            'notes': f'Rejected by {self.env.user.name}',
        })

        if self.notify_submitter and self.invoice_id.dispatch_user_id:
            self.invoice_id.message_post(
                subject=_('Invoice Rejected'),
                body=_(
                    'Your invoice has been rejected by %s.<br/><br/>'
                    '<strong>Reason:</strong><br/>%s'
                ) % (self.env.user.name, self.rejection_reason),
                partner_ids=[self.invoice_id.dispatch_user_id.partner_id.id],
                message_type='notification',
            )

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Invoice Rejected'),
                'message': _('Invoice has been rejected successfully.'),
                'type': 'warning',
                'sticky': False,
            }
        }