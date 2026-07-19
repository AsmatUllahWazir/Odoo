# -*- coding: utf-8 -*-
"""
Property Lease Model - Lease agreements with full lifecycle management
"""

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class PropertyLease(models.Model):
    """
    Property Lease - Complete lease agreement management
    """
    _name = 'property.lease'
    _description = 'Property Lease'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'start_date desc'
    _rec_name = 'display_name'

    # ==========================================================================
    # Basic Information
    # ==========================================================================

    name = fields.Char(
        string='Lease Reference',
        required=True,
        copy=False,
        default=lambda self: self.env['ir.sequence'].next_by_code('property.lease') or _('New')
    )

    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True
    )

    property_id = fields.Many2one(
        'property.property',
        string='Property',
        required=True,
        tracking=True,
        ondelete='restrict'
    )

    unit_id = fields.Many2one(
        'property.unit',
        string='Unit',
        help='Specific unit if this is a multi-unit property',
        ondelete='restrict'
    )

    tenant_id = fields.Many2one(
        'res.partner',
        string='Tenant',
        required=True,
        tracking=True,
        domain="[('is_company', '=', False)]"
    )

    status = fields.Selection([
        ('draft', 'Draft'),
        ('pending_signature', 'Pending Signature'),
        ('signed', 'Signed'),
        ('active', 'Active'),
        ('terminated', 'Terminated'),
        ('expired', 'Expired'),
        ('renewal_pending', 'Renewal Pending'),
    ], string='Status', required=True, default='draft', tracking=True)

    # ==========================================================================
    # Dates & Duration
    # ==========================================================================

    start_date = fields.Date(
        string='Start Date',
        required=True,
        tracking=True,
        help='Lease commencement date'
    )

    end_date = fields.Date(
        string='End Date',
        required=True,
        tracking=True,
        help='Lease termination date'
    )

    renewal_date = fields.Date(
        string='Renewal Date',
        compute='_compute_renewal_dates',
        store=True,
        help='Date when renewal should be processed'
    )

    notice_date = fields.Date(
        string='Notice Deadline',
        compute='_compute_renewal_dates',
        store=True,
        help='Last date to provide notice'
    )

    term_months = fields.Integer(
        string='Term (Months)',
        required=True,
        default=12,
        help='Lease term in months'
    )

    # ==========================================================================
    # Financial Terms
    # ==========================================================================

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        related='property_id.currency_id',
        store=True,
        readonly=True
    )

    rent_amount = fields.Monetary(
        string='Monthly Rent',
        required=True,
        tracking=True,
        help='Base monthly rent amount'
    )

    deposit_amount = fields.Monetary(
        string='Security Deposit',
        required=True,
        help='Security deposit amount'
    )

    rent_frequency = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('semi_annual', 'Semi-Annual'),
        ('annual', 'Annual'),
    ], string='Rent Frequency', required=True, default='monthly')

    lease_fees = fields.Monetary(
        string='Lease Fees',
        help='Additional fees (administration, etc.)'
    )

    late_fee_amount = fields.Monetary(
        string='Late Fee Amount',
        help='Amount charged for late payments'
    )

    late_fee_percent = fields.Float(
        string='Late Fee Percentage',
        help='Percentage of rent charged for late payments'
    )

    grace_period_days = fields.Integer(
        string='Grace Period (Days)',
        default=5,
        help='Days allowed before late fees apply'
    )

    paid_amount = fields.Monetary(
        string='Total Paid',
        compute='_compute_paid_amount',
        store=True,
        help='Total amount paid to date'
    )

    outstanding_amount = fields.Monetary(
        string='Outstanding Amount',
        compute='_compute_paid_amount',
        store=True,
        help='Amount still owed'
    )

    # ==========================================================================
    # Legal & Documentation
    # ==========================================================================

    terms_conditions = fields.Html(
        string='Terms & Conditions',
        help='Full lease terms and conditions'
    )

    special_terms = fields.Text(
        string='Special Terms',
        help='Any special provisions or agreements'
    )

    signed = fields.Boolean(
        string='Signed',
        default=False,
        tracking=True,
        help='Whether all parties have signed'
    )

    signed_date = fields.Date(
        string='Signed Date',
        help='Date when lease was fully signed'
    )

    contract_attachment = fields.Binary(
        string='Contract Document',
        attachment=True,
        help='Upload signed contract document'
    )

    contract_filename = fields.Char(
        string='Contract Filename'
    )

    # ==========================================================================
    # Renewal & Termination
    # ==========================================================================

    renewal_options = fields.Selection([
        ('month_to_month', 'Month to Month'),
        ('fixed_term', 'Fixed Term'),
        ('not_renewable', 'Not Renewable'),
    ], string='Renewal Options', default='fixed_term')

    renewal_terms = fields.Text(
        string='Renewal Terms',
        help='Special terms for renewal'
    )

    termination_reason = fields.Text(
        string='Termination Reason',
        help='Reason for lease termination'
    )

    termination_date = fields.Date(
        string='Termination Date',
        help='Actual date of termination'
    )

    deposit_returned = fields.Boolean(
        string='Deposit Returned',
        default=False,
        help='Whether security deposit has been returned'
    )

    deposit_return_date = fields.Date(
        string='Deposit Return Date',
        help='Date deposit was returned'
    )

    # ==========================================================================
    # Relationships
    # ==========================================================================

    invoice_ids = fields.One2many(
        'account.move',
        'lease_id',
        string='Invoices',
        help='Related invoices for this lease'
    )

    viewing_ids = fields.One2many(
        'property.viewing',
        'lease_id',
        string='Viewings',
        help='Viewings associated with this lease'
    )

    maintenance_ids = fields.One2many(
        'property.maintenance.request',
        'lease_id',
        string='Maintenance Requests',
        help='Maintenance requests during lease'
    )

    # ==========================================================================
    # Computed Fields
    # ==========================================================================

    @api.depends('name', 'tenant_id', 'property_id')
    def _compute_display_name(self):
        """Compute display name"""
        for record in self:
            tenant_name = record.tenant_id.name if record.tenant_id else ''
            property_name = record.property_id.name if record.property_id else ''
            record.display_name = f"{record.name} - {tenant_name} - {property_name}"

    @api.depends('start_date', 'end_date', 'term_months')
    def _compute_renewal_dates(self):
        """Compute renewal notice dates"""
        for record in self:
            if record.start_date and record.end_date:
                # Notice deadline is 60 days before end date
                record.notice_date = record.end_date - timedelta(days=60)
                # Renewal date is 30 days before end date
                record.renewal_date = record.end_date - timedelta(days=30)
            else:
                record.notice_date = False
                record.renewal_date = False

    @api.depends('invoice_ids', 'invoice_ids.state', 'invoice_ids.amount_total',
                 'invoice_ids.amount_residual')
    def _compute_paid_amount(self):
        """Compute paid and outstanding amounts from invoices"""
        for record in self:
            total_invoiced = 0.0
            total_paid = 0.0

            # Consider only posted invoices
            invoices = record.invoice_ids.filtered(
                lambda i: i.state in ['posted', 'paid']
            )

            for invoice in invoices:
                total_invoiced += invoice.amount_total
                # Calculate paid amount (total - residual)
                total_paid += invoice.amount_total - invoice.amount_residual

            record.paid_amount = total_paid
            record.outstanding_amount = total_invoiced - total_paid

    # ==========================================================================
    # Constraints
    # ==========================================================================

    _sql_constraints = [
        ('lease_name_unique', 'unique(name)',
         'Lease reference must be unique!'),
        ('check_rent_positive', 'CHECK(rent_amount >= 0)',
         'Rent amount cannot be negative'),
        ('check_deposit_positive', 'CHECK(deposit_amount >= 0)',
         'Deposit amount cannot be negative'),
        ('check_term_months_positive', 'CHECK(term_months > 0)',
         'Term must be greater than 0 months'),
        ('check_dates_valid', 'CHECK(start_date <= end_date)',
         'Start date must be before or equal to end date'),
    ]

    # @api.constrains('start_date', 'end_date')
    # def _check_dates(self):
    #     """Validate date ranges"""
    #     for record in self:
    #         if record.start_date and record.end_date:
    #             if record.start_date > record.end_date:
    #                 raise ValidationError(
    #                     _("Start date cannot be after end date.")
    #                 )
    #             if record.start_date < fields.Date.today() - timedelta(days=30):
    #                 raise ValidationError(
    #                     _("Start date cannot be more than 30 days in the past.")
    #                 )

    @api.constrains('property_id', 'unit_id', 'start_date', 'end_date')
    def _check_overlapping_leases(self):
        """Check for overlapping leases on same property/unit"""
        for record in self:
            if record.status == 'draft':
                continue

            domain = [
                ('id', '!=', record.id),
                ('status', 'in', ['signed', 'active']),
            ]

            if record.unit_id:
                domain.append(('unit_id', '=', record.unit_id.id))
            else:
                domain.append(('property_id', '=', record.property_id.id))

            overlapping = self.search([
                *domain,
                '|', ('start_date', '<=', record.end_date),
                ('end_date', '>=', record.start_date)
            ])

            if overlapping:
                raise ValidationError(
                    _("There is already an active lease for this property/unit "
                      "during the specified dates.")
                )

    # ==========================================================================
    # Business Methods
    # ==========================================================================

    def action_send_signature(self):
        """Send lease for e-signature"""
        self.ensure_one()
        if self.signed:
            raise UserError(_("This lease is already signed."))

        self.status = 'pending_signature'

        # Check if sign module is installed
        if 'sign' in self.env.registry._init_modules:
            try:
                sign_request = self.env['sign.request'].create({
                    'name': f"Lease Contract - {self.name}",
                    'partner_ids': [(4, self.tenant_id.id)],
                    'template_id': self.env.ref('smart_property_lifecycle.lease_template', raise_if_not_found=False).id,
                    'state': 'sent',
                })
                self.message_post(
                    body=_("Signature request sent to tenant."),
                    message_type='notification'
                )
            except Exception as e:
                _logger.error(f"Error creating signature request: {e}")
                self.message_post(
                    body=_("Signature module not available. Please send contract manually."),
                    message_type='notification'
                )
        else:
            self.message_post(
                body=_("E-signature not available. Please send contract manually."),
                message_type='notification'
            )

        return True

    def action_mark_signed(self):
        """Mark lease as signed"""
        for record in self:
            if record.signed:
                continue
            record.signed = True
            record.signed_date = fields.Date.today()
            record.status = 'signed'
            record.message_post(
                body=_("Lease signed by all parties."),
                message_type='notification'
            )

    def action_activate(self):
        """Activate lease (start leasing period)"""
        for record in self:
            if not record.signed:
                raise UserError(_("Lease must be signed before activation."))

            if record.status == 'active':
                raise UserError(_("Lease is already active."))

            record.status = 'active'

            # Create initial invoices
            record._create_invoices()

            # Update property status
            if record.property_id:
                record.property_id.action_mark_leased()

            # Send welcome notification
            record._send_activation_notification()

            record.message_post(
                body=_("Lease activated. Invoices created."),
                message_type='notification'
            )

    def action_terminate(self):
        """Terminate lease early"""
        for record in self:
            if record.status in ['terminated', 'expired']:
                raise UserError(_("This lease is already terminated or expired."))

            # Open termination wizard
            return {
                'type': 'ir.actions.act_window',
                'name': _('Terminate Lease'),
                'res_model': 'property.lease.terminate.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_lease_id': record.id,
                    'default_termination_date': fields.Date.today(),
                }
            }

    def action_renew(self):
        """Renew lease"""
        for record in self:
            if record.status not in ['active', 'renewal_pending']:
                raise UserError(_("Only active leases can be renewed."))

            # Create renewal wizard
            return {
                'type': 'ir.actions.act_window',
                'name': _('Renew Lease'),
                'res_model': 'property.lease.renewal.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_lease_id': record.id,
                }
            }

    def _create_invoices(self):
        """Create recurring invoices for the lease"""
        for record in self:
            if not record.rent_amount:
                return

            # Determine invoice frequency
            frequency_days = {
                'monthly': 30,
                'quarterly': 90,
                'semi_annual': 180,
                'annual': 365,
            }.get(record.rent_frequency, 30)

            current_date = record.start_date
            while current_date <= record.end_date:
                record._create_single_invoice(current_date)
                current_date += timedelta(days=frequency_days)

    def _create_single_invoice(self, invoice_date):
        """Create a single invoice for the lease"""
        self.ensure_one()

        # Calculate invoice amount (pro-rate if needed)
        amount = self.rent_amount

        # Find income account
        income_account = self.env['account.account'].search([
            ('account_type', '=', 'income'),
            ('company_id', '=', self.env.company.id)
        ], limit=1)

        if not income_account:
            _logger.warning("No income account found for invoice creation")
            return False

        # Create invoice
        invoice_vals = {
            'partner_id': self.tenant_id.id,
            'move_type': 'out_invoice',
            'invoice_date': invoice_date,
            'invoice_date_due': invoice_date + timedelta(days=30),
            'lease_id': self.id,
            'is_lease_invoice': True,
            'invoice_line_ids': [(0, 0, {
                'name': f"Rent - {self.name} - {invoice_date.strftime('%B %Y')}",
                'quantity': 1.0,
                'price_unit': amount,
                'account_id': income_account.id,
            })],
        }

        invoice = self.env['account.move'].create(invoice_vals)
        invoice.action_post()

        return invoice

    def _send_activation_notification(self):
        """Send notification on lease activation"""
        self.ensure_one()
        # Email notification logic would go here
        pass

    @api.model
    def _cron_check_renewal_dates(self):
        """Cron job to check for upcoming renewals"""
        today = fields.Date.today()
        notice_date = today + timedelta(days=60)

        leases = self.search([
            ('status', '=', 'active'),
            ('end_date', '<=', notice_date),
            ('renewal_options', '!=', 'not_renewable'),
        ])

        for lease in leases:
            lease.status = 'renewal_pending'
            lease.message_post(
                body=_("Lease renewal pending. 60-day notice period has started."),
                message_type='notification'
            )

    @api.model
    def _cron_check_expired_leases(self):
        """Cron job to mark expired leases"""
        today = fields.Date.today()
        expired = self.search([
            ('status', '=', 'active'),
            ('end_date', '<', today),
        ])

        for lease in expired:
            lease.status = 'expired'
            lease.message_post(
                body=_("Lease has expired."),
                message_type='notification'
            )
