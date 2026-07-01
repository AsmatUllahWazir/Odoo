# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class VendorBillManualDispatchWizard(models.TransientModel):
    _name = 'vendor.bill.manual.dispatch.wizard'
    _description = 'Manual Vendor Bill Dispatch Wizard'

    invoice_id = fields.Many2one(
        'account.move',
        string='Invoice',
        required=True,
        ondelete='cascade',
    )

    suggested_company_id = fields.Many2one(
        'res.company',
        string='Suggested Company',
        help='Company suggested by dispatch rule (if any)',
    )

    matched_rule_id = fields.Many2one(
        'vendor.bill.dispatch.rule',
        string='Matched Rule',
        help='Rule that matched this invoice',
    )

    target_company_id = fields.Many2one(
        'res.company',
        string='Target Company',
        required=True,
        help='Select the company to which this invoice should be dispatched',
    )

    notes = fields.Text(
        string='Notes',
        help='Optional notes about this manual dispatch',
    )

    @api.onchange('suggested_company_id')
    def _onchange_suggested_company(self):
        if self.suggested_company_id and not self.target_company_id:
            self.target_company_id = self.suggested_company_id

    def action_dispatch(self):
        """Manually dispatch the invoice to selected company"""
        self.ensure_one()

        if not self.target_company_id:
            raise ValidationError(_('Please select a target company.'))

        self.invoice_id._dispatch_to_company(
            self.target_company_id,
            self.matched_rule_id if self.matched_rule_id else None,
            'manual'
        )

        if self.notes:
            last_history = self.env['vendor.bill.validation.history'].search([
                ('invoice_id', '=', self.invoice_id.id),
                ('action', '=', 'dispatched'),
            ], order='timestamp desc', limit=1)

            if last_history:
                last_history.write({
                    'notes': (last_history.notes or '') + '\n\n' + self.notes
                })

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Dispatched Successfully'),
                'message': _('Invoice manually dispatched to %s') % self.target_company_id.name,
                'type': 'success',
                'sticky': False,
            }
        }