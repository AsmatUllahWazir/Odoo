# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class VendorBillValidationHistory(models.Model):
    _name = 'vendor.bill.validation.history'
    _description = 'Vendor Bill Validation History'
    _order = 'timestamp desc'

    invoice_id = fields.Many2one(
        'account.move',
        string='Invoice',
        required=True,
        ondelete='cascade',
        index=True,
    )

    action = fields.Selection([
        ('created', 'Created'),
        ('ocr_processed', 'OCR Processed'),
        ('dispatched', 'Dispatched'),
        ('submitted', 'Submitted for Approval'),
        ('business_approved', 'Business Approved'),
        ('finance_approved', 'Finance Approved'),
        ('rejected', 'Rejected'),
        ('company_changed', 'Company Changed'),
        ('posted', 'Posted to Accounting'),
        ('manual_edit', 'Manual Edit'),
    ], string='Action', required=True)

    user_id = fields.Many2one(
        'res.users',
        string='User',
        required=True,
        default=lambda self: self.env.user,
        ondelete='restrict',
    )

    timestamp = fields.Datetime(
        string='Timestamp',
        required=True,
        default=fields.Datetime.now,
    )

    # Context Information
    old_company_id = fields.Many2one(
        'res.company',
        string='Previous Company',
        ondelete='restrict',
    )

    new_company_id = fields.Many2one(
        'res.company',
        string='New Company',
        ondelete='restrict',
    )

    old_state = fields.Char(string='Previous State')
    new_state = fields.Char(string='New State')

    notes = fields.Text(string='Notes')
    rejection_reason = fields.Text(string='Rejection Reason')

    ip_address = fields.Char(string='IP Address')
    session_id = fields.Char(string='Session ID')

    def name_get(self):
        result = []
        for record in self:
            name = f"{record.timestamp.strftime('%Y-%m-%d %H:%M')} - {dict(record._fields['action'].selection).get(record.action)} by {record.user_id.name}"
            result.append((record.id, name))
        return result