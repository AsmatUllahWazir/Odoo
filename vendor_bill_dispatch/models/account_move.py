# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    # Dispatch State
    dispatch_state = fields.Selection([
        ('ocr_draft', 'OCR Draft'),
        ('routed', 'Routed'),
        ('to_approve', 'To Approve'),
        ('approved', 'Approved'),
        ('finance_approved', 'Finance Approved'),
        ('rejected', 'Rejected'),
    ], string='Dispatch State', default='ocr_draft', tracking=True, copy=False)

    # Original Company (HUB)
    original_company_id = fields.Many2one(
        'res.company',
        string='Original Company',
        readonly=True,
        copy=False,
        help='HUB company where bill was initially received',
    )

    # Dispatch Information
    dispatch_method = fields.Selection([
        ('automatic', 'Automatic (Rule-based)'),
        ('manual', 'Manual'),
        ('fallback', 'Fallback (No rule matched)'),
    ], string='Dispatch Method', readonly=True, copy=False)

    dispatch_rule_id = fields.Many2one(
        'vendor.bill.dispatch.rule',
        string='Matched Dispatch Rule',
        readonly=True,
        copy=False,
    )

    dispatch_date = fields.Datetime(
        string='Dispatch Date',
        readonly=True,
        copy=False,
    )

    dispatch_user_id = fields.Many2one(
        'res.users',
        string='Dispatched By',
        readonly=True,
        copy=False,
    )

    # OCR Information
    ocr_result_id = fields.Many2one(
        'vendor.bill.ocr.result',
        string='OCR Result',
        readonly=True,
        copy=False,
    )

    ocr_status = fields.Selection([
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('done', 'Done'),
        ('error', 'Error'),
        ('manual', 'Manual Entry'),
    ], string='OCR Status', default='pending', copy=False)

    ocr_confidence = fields.Float(
        string='OCR Confidence %',
        readonly=True,
        copy=False,
    )

    ocr_error_message = fields.Text(
        string='OCR Error',
        readonly=True,
        copy=False,
    )

    # Validation History
    validation_history_ids = fields.One2many(
        'vendor.bill.validation.history',
        'invoice_id',
        string='Validation History',
    )

    # Approval Fields
    business_approved_by = fields.Many2one(
        'res.users',
        string='Business Approved By',
        readonly=True,
        copy=False,
    )

    business_approved_date = fields.Datetime(
        string='Business Approval Date',
        readonly=True,
        copy=False,
    )

    finance_approved_by = fields.Many2one(
        'res.users',
        string='Finance Approved By',
        readonly=True,
        copy=False,
    )

    finance_approved_date = fields.Datetime(
        string='Finance Approval Date',
        readonly=True,
        copy=False,
    )

    rejection_reason = fields.Text(
        string='Rejection Reason',
        readonly=True,
        copy=False,
    )

    rejected_by = fields.Many2one(
        'res.users',
        string='Rejected By',
        readonly=True,
        copy=False,
    )

    rejected_date = fields.Datetime(
        string='Rejection Date',
        readonly=True,
        copy=False,
    )

    # Finance Validation Requirement
    requires_finance_approval = fields.Boolean(
        string='Requires Finance Approval',
        compute='_compute_requires_finance_approval',
        store=True,
    )

    # Computed Fields for Workflow
    can_business_approve = fields.Boolean(
        compute='_compute_workflow_permissions',
    )

    can_finance_approve = fields.Boolean(
        compute='_compute_workflow_permissions',
    )

    can_post = fields.Boolean(
        compute='_compute_workflow_permissions',
    )

    @api.depends('amount_total', 'company_id')
    def _compute_requires_finance_approval(self):
        config = self.env['vendor.bill.dispatch.config'].sudo().get_active_config()
        for invoice in self:
            if config.enable_finance_validation:
                amount_company_currency = invoice.amount_total
                if invoice.currency_id != invoice.company_id.currency_id:
                    amount_company_currency = invoice.currency_id._convert(
                        invoice.amount_total,
                        invoice.company_id.currency_id,
                        invoice.company_id,
                        invoice.date or fields.Date.today(),
                    )
                invoice.requires_finance_approval = amount_company_currency >= config.finance_approval_threshold
            else:
                invoice.requires_finance_approval = False

    @api.depends('dispatch_state', 'state', 'requires_finance_approval')
    def _compute_workflow_permissions(self):
        for invoice in self:
            user = self.env.user

            invoice.can_business_approve = (
                    invoice.dispatch_state == 'to_approve' and
                    user.has_group('vendor_bill_dispatch.group_business_validator')
            )

            invoice.can_finance_approve = (
                    invoice.dispatch_state == 'approved' and
                    invoice.requires_finance_approval and
                    user.has_group('vendor_bill_dispatch.group_finance_validator')
            )

            can_post_state = (
                    invoice.dispatch_state == 'finance_approved' or
                    (invoice.dispatch_state == 'approved' and not invoice.requires_finance_approval)
            )
            invoice.can_post = (
                    can_post_state and
                    invoice.state == 'draft' and
                    user.has_group('account.group_account_invoice')
            )

    @api.constrains('company_id', 'dispatch_state')
    def _check_company_change(self):
        """Prevent company changes after validation based on configuration"""
        config = self.env['vendor.bill.dispatch.config'].sudo().get_active_config()

        for invoice in self:
            if invoice.dispatch_state and invoice.dispatch_state not in ['ocr_draft', 'routed']:
                if config.lock_company_after_validation:
                    if invoice._origin and invoice._origin.company_id and invoice.company_id != invoice._origin.company_id:
                        raise ValidationError(
                            _('Cannot change company after validation has started. Current state: %s') %
                            dict(invoice._fields['dispatch_state'].selection).get(invoice.dispatch_state)
                        )

    def action_process_ocr(self):
        """Trigger OCR processing for the invoice"""
        self.ensure_one()

        if self.move_type != 'in_invoice':
            raise UserError(_('OCR processing is only available for vendor bills.'))

        if not self.message_main_attachment_id:
            raise UserError(_('No attachment found. Please upload a vendor bill document first.'))

        ocr_result = self.env['vendor.bill.ocr.result'].create({
            'invoice_id': self.id,
            'attachment_id': self.message_main_attachment_id.id,
        })

        self.write({
            'ocr_result_id': ocr_result.id,
            'ocr_status': 'processing',
        })

        ocr_result.process_ocr()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('OCR Processing Started'),
                'message': _('OCR processing has been initiated. Results will be available shortly.'),
                'type': 'info',
                'sticky': False,
            }
        }

    def action_auto_dispatch(self):
        """Apply dispatch rules to determine target company"""
        self.ensure_one()

        config = self.env['vendor.bill.dispatch.config'].sudo().get_active_config()

        if not config.auto_dispatch_enabled:
            raise UserError(_('Automatic dispatch is disabled in configuration.'))

        all_rules = self.env['vendor.bill.dispatch.rule'].search([
            ('active', '=', True),
        ], order='priority, sequence')

        matched_rule = None
        for rule in all_rules:
            if rule.match_invoice(self):
                matched_rule = rule
                if rule.stop_on_match:
                    break

        if matched_rule:
            matched_rule.increment_match_count()

            if matched_rule.require_manual_confirmation:
                return {
                    'type': 'ir.actions.act_window',
                    'name': _('Confirm Dispatch'),
                    'res_model': 'vendor.bill.manual.dispatch.wizard',
                    'view_mode': 'form',
                    'target': 'new',
                    'context': {
                        'default_invoice_id': self.id,
                        'default_suggested_company_id': matched_rule.target_company_id.id,
                        'default_matched_rule_id': matched_rule.id,
                    }
                }
            else:
                self._dispatch_to_company(matched_rule.target_company_id, matched_rule, 'automatic')

                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Dispatched Successfully'),
                        'message': _('Invoice dispatched to %s via rule: %s') % (
                            matched_rule.target_company_id.name,
                            matched_rule.name
                        ),
                        'type': 'success',
                        'sticky': False,
                    }
                }
        else:
            if config.fallback_to_manual:
                return {
                    'type': 'ir.actions.act_window',
                    'name': _('Manual Company Selection'),
                    'res_model': 'vendor.bill.manual.dispatch.wizard',
                    'view_mode': 'form',
                    'target': 'new',
                    'context': {'default_invoice_id': self.id}
                }
            elif config.default_fallback_company_id:
                self._dispatch_to_company(config.default_fallback_company_id, None, 'fallback')
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Dispatched to Fallback Company'),
                        'message': _('No rule matched. Dispatched to default company: %s') %
                                   config.default_fallback_company_id.name,
                        'type': 'warning',
                    }
                }
            else:
                raise UserError(_('No dispatch rule matched and no fallback company configured.'))

    def _dispatch_to_company(self, target_company, rule=None, method='automatic'):
        """Internal method to dispatch invoice to target company"""
        self.ensure_one()

        if not self.original_company_id:
            self.write({'original_company_id': self.company_id.id})

        journal = self.env['account.journal'].search([
            ('company_id', '=', target_company.id),
            ('type', '=', 'purchase'),
        ], limit=1)

        if not journal:
            raise UserError(
                _('No purchase journal found for company %s. Please configure one first.') %
                target_company.name
            )

        vals = {
            'company_id': target_company.id,
            'journal_id': journal.id,
            'dispatch_method': method,
            'dispatch_rule_id': rule.id if rule else False,
            'dispatch_date': fields.Datetime.now(),
            'dispatch_user_id': self.env.user.id,
            'dispatch_state': 'routed',
        }

        self.write(vals)

        self._onchange_partner_id()

        self.env['vendor.bill.validation.history'].create({
            'invoice_id': self.id,
            'action': 'dispatched',
            'user_id': self.env.user.id,
            'timestamp': fields.Datetime.now(),
            'old_company_id': self.original_company_id.id,
            'new_company_id': target_company.id,
            'notes': f'Dispatched via {method} method' + (f' (Rule: {rule.name})' if rule else ''),
        })

        config = self.env['vendor.bill.dispatch.config'].sudo().get_active_config()
        if config.notify_on_dispatch:
            self._send_dispatch_notification(target_company)

    def action_submit_for_approval(self):
        """Submit invoice for business approval"""
        self.ensure_one()

        if self.dispatch_state != 'routed':
            raise UserError(_('Invoice must be in Routed state to submit for approval.'))

        self.write({'dispatch_state': 'to_approve'})

        self.env['vendor.bill.validation.history'].create({
            'invoice_id': self.id,
            'action': 'submitted',
            'user_id': self.env.user.id,
            'timestamp': fields.Datetime.now(),
            'notes': 'Submitted for business approval',
        })

        config = self.env['vendor.bill.dispatch.config'].sudo().get_active_config()
        if config.notify_business_validator:
            self._send_approval_notification('business')

        return True

    def action_business_approve(self):
        """Business manager approves the invoice"""
        self.ensure_one()

        if not self.can_business_approve:
            raise UserError(_('You do not have permission to approve this invoice.'))

        self.write({
            'dispatch_state': 'approved',
            'business_approved_by': self.env.user.id,
            'business_approved_date': fields.Datetime.now(),
        })

        self.env['vendor.bill.validation.history'].create({
            'invoice_id': self.id,
            'action': 'business_approved',
            'user_id': self.env.user.id,
            'timestamp': fields.Datetime.now(),
            'notes': 'Business validation approved',
        })

        if self.requires_finance_approval:
            config = self.env['vendor.bill.dispatch.config'].sudo().get_active_config()
            if config.notify_finance_validator:
                self._send_approval_notification('finance')

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Approved'),
                'message': _('Business approval completed successfully.'),
                'type': 'success',
            }
        }

    def action_finance_approve(self):
        """Finance/CFO approves high-value invoice"""
        self.ensure_one()

        if not self.can_finance_approve:
            raise UserError(_('You do not have permission to provide finance approval.'))

        self.write({
            'dispatch_state': 'finance_approved',
            'finance_approved_by': self.env.user.id,
            'finance_approved_date': fields.Datetime.now(),
        })

        self.env['vendor.bill.validation.history'].create({
            'invoice_id': self.id,
            'action': 'finance_approved',
            'user_id': self.env.user.id,
            'timestamp': fields.Datetime.now(),
            'notes': 'Finance validation approved',
        })

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Finance Approved'),
                'message': _('Finance approval completed. Invoice ready for accounting validation.'),
                'type': 'success',
            }
        }

    def action_reject(self):
        """Open rejection wizard"""
        self.ensure_one()

        return {
            'type': 'ir.actions.act_window',
            'name': _('Reject Invoice'),
            'res_model': 'vendor.bill.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_invoice_id': self.id}
        }

    def _send_dispatch_notification(self, target_company):
        """Send notification when invoice is dispatched"""

        group = self.env.ref('vendor_bill_dispatch.group_business_validator')

        users = self.env['res.users'].search([
            ('group_ids', 'in', group.id),
            ('company_ids', 'in', target_company.id),
        ])

        if users:
            self.message_notify(
                subject=_("New Vendor Bill Dispatched"),
                body=_(
                    "A new vendor bill has been dispatched to %s and requires your attention."
                ) % target_company.name,
                partner_ids=users.mapped("partner_id").ids,
            )

    def _send_approval_notification(self, approval_type):
        """Send notification for approval request"""

        if approval_type == 'business':
            group = self.env.ref('vendor_bill_dispatch.group_business_validator')
            subject = _("Business Approval Required")
        else:
            group = self.env.ref('vendor_bill_dispatch.group_finance_validator')
            subject = _("Finance Approval Required")

        users = self.env['res.users'].search([
            ('group_ids', 'in', group.id),
            ('company_ids', 'in', self.company_id.id),
        ])

        if users:
            self.message_notify(
                subject=subject,
                body=_("Vendor bill %s requires your approval.") %
                     (self.name or _("New")),
                partner_ids=users.mapped("partner_id").ids,
            )

    @api.model_create_multi
    def create(self, vals_list):
        """
        Odoo 19 uses @api.model_create_multi.
        'vals_list' is a list of dictionaries.
        """
        # Get config once to avoid multiple hits to the DB
        config = self.env['vendor.bill.dispatch.config'].sudo().search([('active', '=', True)], limit=1)

        for vals in vals_list:
            # Check move_type safely on the dictionary
            if vals.get('move_type') == 'in_invoice' and config:
                # Set Hub Company if missing
                if not vals.get('company_id') and config.hub_company_id:
                    vals['company_id'] = config.hub_company_id.id

                # Set initial dispatch state
                if not vals.get('dispatch_state'):
                    vals['dispatch_state'] = 'ocr_draft'

        # Call super with the modified list
        invoices = super(AccountMove, self).create(vals_list)

        # Handle post-create logic like OCR trigger
        for invoice in invoices:
            if (config and config.auto_ocr_on_upload and
                    invoice.move_type == 'in_invoice' and
                    invoice.message_main_attachment_id):
                invoice.action_process_ocr()

        return invoices

    def button_draft(self):
        """Override to prevent reverting dispatch workflow"""
        for invoice in self:
            if invoice.dispatch_state and invoice.dispatch_state not in ['ocr_draft', 'rejected']:
                raise UserError(
                    _('Cannot reset to draft. Invoice is in dispatch workflow state: %s') %
                    dict(invoice._fields['dispatch_state'].selection).get(invoice.dispatch_state)
                )
        return super(AccountMove, self).button_draft()


