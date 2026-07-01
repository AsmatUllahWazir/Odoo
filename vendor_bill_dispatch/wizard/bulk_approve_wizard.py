# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class VendorBillBulkApproveWizard(models.TransientModel):
    _name = 'vendor.bill.bulk.approve.wizard'
    _description = 'Bulk Approve Vendor Bills Wizard'

    invoice_ids = fields.Many2many(
        'account.move',
        string='Invoices',
        required=True,
    )

    approval_type = fields.Selection([
        ('business', 'Business Approval'),
        ('finance', 'Finance Approval'),
    ], string='Approval Type', required=True)

    invoice_count = fields.Integer(
        string='Number of Invoices',
        compute='_compute_invoice_count',
    )

    total_amount = fields.Monetary(
        string='Total Amount',
        compute='_compute_total_amount',
        currency_field='currency_id',
    )

    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id,
    )

    notes = fields.Text(string='Approval Notes')

    @api.depends('invoice_ids')
    def _compute_invoice_count(self):
        for wizard in self:
            wizard.invoice_count = len(wizard.invoice_ids)

    @api.depends('invoice_ids')
    def _compute_total_amount(self):
        for wizard in self:
            wizard.total_amount = sum(wizard.invoice_ids.mapped('amount_total'))

    def action_approve_all(self):
        """Approve all selected invoices"""
        self.ensure_one()

        if not self.invoice_ids:
            raise UserError(_('No invoices selected for approval.'))

        success_count = 0
        error_count = 0
        errors = []

        for invoice in self.invoice_ids:
            try:
                if self.approval_type == 'business':
                    if invoice.can_business_approve:
                        invoice.action_business_approve()
                        success_count += 1
                    else:
                        error_count += 1
                        errors.append(f"{invoice.name or 'New'}: Not in correct state for business approval")

                elif self.approval_type == 'finance':
                    if invoice.can_finance_approve:
                        invoice.action_finance_approve()
                        success_count += 1
                    else:
                        error_count += 1
                        errors.append(f"{invoice.name or 'New'}: Not in correct state for finance approval")

            except Exception as e:
                error_count += 1
                errors.append(f"{invoice.name or 'New'}: {str(e)}")

        if error_count == 0:
            message = _('%d invoices approved successfully.') % success_count
            notif_type = 'success'
        else:
            message = _(
                '%d invoices approved successfully.\n'
                '%d invoices failed.\n\nErrors:\n%s'
            ) % (success_count, error_count, '\n'.join(errors[:5]))
            notif_type = 'warning'

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Bulk Approval Complete'),
                'message': message,
                'type': notif_type,
                'sticky': True,
            }
        }