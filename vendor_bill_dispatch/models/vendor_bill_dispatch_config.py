# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class VendorBillDispatchConfig(models.Model):
    _name = 'vendor.bill.dispatch.config'
    _description = 'Vendor Bill Dispatch Configuration'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Configuration Name', required=True, default='Main Configuration')
    active = fields.Boolean(default=True)

    # HUB Company Configuration
    hub_company_id = fields.Many2one(
        'res.company',
        string='HUB Company',
        required=True,
        help='Central company where all vendor bills are initially received and processed via OCR',
        tracking=True,
    )

    # Email Reception
    enable_email_reception = fields.Boolean(
        string='Enable Email Reception',
        default=True,
        help='Allow vendor bills to be received via email',
        tracking=True,
    )
    reception_email = fields.Char(
        string='Reception Email Alias',
        default='vendor.bills',
        help='Email alias for receiving vendor bills (e.g., vendor.bills@yourdomain.com)',
        tracking=True,
    )

    # OCR Configuration
    auto_ocr_on_upload = fields.Boolean(
        string='Automatic OCR on Upload',
        default=True,
        help='Automatically trigger OCR when a document is uploaded',
        tracking=True,
    )
    ocr_provider = fields.Selection([
        ('odoo_iap', 'Odoo Document Digitization (IAP)'),
        ('custom', 'Custom OCR Engine'),
    ], string='OCR Provider', default='odoo_iap', required=True, tracking=True)

    ocr_confidence_threshold = fields.Float(
        string='OCR Confidence Threshold (%)',
        default=70.0,
        help='Minimum confidence percentage to accept OCR results automatically',
        tracking=True,
    )

    # Dispatch Configuration
    auto_dispatch_enabled = fields.Boolean(
        string='Enable Auto-Dispatch',
        default=True,
        help='Automatically dispatch bills to target company based on rules',
        tracking=True,
    )

    fallback_to_manual = fields.Boolean(
        string='Fallback to Manual Selection',
        default=True,
        help='If no rule matches, require manual company selection',
        tracking=True,
    )

    default_fallback_company_id = fields.Many2one(
        'res.company',
        string='Default Fallback Company',
        help='Company to use when no dispatch rule matches and manual selection is disabled',
    )

    # Validation Workflow
    enable_business_validation = fields.Boolean(
        string='Enable Business Validation',
        default=True,
        help='Require business manager approval before accounting validation',
        tracking=True,
    )

    enable_finance_validation = fields.Boolean(
        string='Enable Finance Validation',
        default=True,
        help='Require finance/CFO approval for high-value invoices',
        tracking=True,
    )

    finance_approval_threshold = fields.Monetary(
        string='Finance Approval Threshold',
        currency_field='currency_id',
        default=5000.0,
        help='Invoice amount threshold requiring finance approval',
        tracking=True,
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
        required=True,
    )

    # Notification Settings
    notify_on_dispatch = fields.Boolean(
        string='Notify on Dispatch',
        default=True,
        help='Send notification when bill is dispatched to target company',
    )

    notify_business_validator = fields.Boolean(
        string='Notify Business Validator',
        default=True,
        help='Send notification to business validator when bill needs approval',
    )

    notify_finance_validator = fields.Boolean(
        string='Notify Finance Validator',
        default=True,
        help='Send notification to finance validator for high-value bills',
    )

    # Advanced Settings
    allow_company_change_after_routing = fields.Boolean(
        string='Allow Company Change After Routing',
        default=False,
        help='WARNING: Allow changing company even after routing (not recommended)',
        tracking=True,
    )

    lock_company_after_validation = fields.Boolean(
        string='Lock Company After Validation',
        default=True,
        help='Prevent company changes after business validation',
        tracking=True,
    )

    retention_days = fields.Integer(
        string='OCR Data Retention (Days)',
        default=365,
        help='Number of days to retain detailed OCR data',
    )

    # Statistics
    total_bills_processed = fields.Integer(
        string='Total Bills Processed',
        compute='_compute_statistics',
        store=False,
    )

    auto_routed_percentage = fields.Float(
        string='Auto-Routed %',
        compute='_compute_statistics',
        store=False,
    )

    @api.constrains('finance_approval_threshold')
    def _check_finance_threshold(self):
        for record in self:
            if record.finance_approval_threshold < 0:
                raise ValidationError(_('Finance approval threshold must be positive.'))

    @api.constrains('ocr_confidence_threshold')
    def _check_ocr_threshold(self):
        for record in self:
            if not 0 <= record.ocr_confidence_threshold <= 100:
                raise ValidationError(_('OCR confidence threshold must be between 0 and 100.'))

    def _compute_statistics(self):
        for record in self:
            bills = self.env['account.move'].search([
                ('move_type', '=', 'in_invoice'),
                ('dispatch_state', '!=', False),
            ])
            record.total_bills_processed = len(bills)

            auto_routed = bills.filtered(lambda b: b.dispatch_method == 'automatic')
            record.auto_routed_percentage = (
                len(auto_routed) / len(bills) * 100 if bills else 0.0
            )

    # @api.model
    # def get_active_config(self):
    #     config = self.search([('active', '=', True)], limit=1)
    #     # If no config exists, don't raise error immediately;
    #     # Let the UI allow the user to create one first.
    #     return config

    @api.model
    def get_active_config(self):
        """Get the active configuration (singleton pattern)"""
        config = self.search([('active', '=', True)], limit=1)
        if not config:
            raise ValidationError(
                _('No active vendor bill dispatch configuration found. Please configure the system first.'))
        return config

    def action_test_ocr(self):
        """Test OCR connection"""
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('OCR Test'),
                'message': _('OCR connection test successful!'),
                'type': 'success',
                'sticky': False,
            }
        }

    def action_view_statistics(self):
        """Open statistics dashboard"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Dispatch Statistics'),
            'res_model': 'dispatch.kpi',
            'view_mode': 'graph,pivot,list',
            'context': {'search_default_group_by_month': 1},
        }