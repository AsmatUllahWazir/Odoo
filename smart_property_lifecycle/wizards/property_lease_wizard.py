# -*- coding: utf-8 -*-
"""
Lease Creation Wizard - Create lease from property or viewing
"""

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta


class PropertyLeaseWizard(models.TransientModel):
    """
    Wizard for creating a new lease
    """
    _name = 'property.lease.wizard'
    _description = 'Create Lease Wizard'

    # ==========================================================================
    # Wizard Fields
    # ==========================================================================

    property_id = fields.Many2one(
        'property.property',
        string='Property',
        required=True,
        help='Property to create lease for'
    )

    unit_id = fields.Many2one(
        'property.unit',
        string='Unit',
        help='Specific unit if multi-unit property',
        domain="[('property_id', '=', property_id), ('status', 'in', ['vacant', 'pending_inspection'])]"
    )

    tenant_id = fields.Many2one(
        'res.partner',
        string='Tenant',
        required=True,
        domain="[('is_company', '=', False)]",
        help='Tenant for the lease'
    )

    start_date = fields.Date(
        string='Start Date',
        required=True,
        default=lambda self: fields.Date.today() + timedelta(days=30),
        help='Lease start date'
    )

    end_date = fields.Date(
        string='End Date',
        required=True,
        compute='_compute_end_date',
        store=False,
        help='Lease end date'
    )

    term_months = fields.Integer(
        string='Term (Months)',
        required=True,
        default=12,
        help='Lease duration in months'
    )

    rent_amount = fields.Monetary(
        string='Monthly Rent',
        required=True,
        help='Monthly rent amount'
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

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        related='property_id.currency_id',
        readonly=True
    )

    renewal_options = fields.Selection([
        ('month_to_month', 'Month to Month'),
        ('fixed_term', 'Fixed Term'),
        ('not_renewable', 'Not Renewable'),
    ], string='Renewal Options', default='fixed_term')

    terms_conditions = fields.Html(
        string='Terms & Conditions',
        help='Standard lease terms'
    )

    special_terms = fields.Text(
        string='Special Terms',
        help='Any special provisions'
    )

    create_invoices = fields.Boolean(
        string='Create Invoices',
        default=True,
        help='Automatically create recurring invoices'
    )

    send_signature = fields.Boolean(
        string='Send for Signature',
        default=True,
        help='Send lease for e-signature'
    )

    # ==========================================================================
    # Computed Fields
    # ==========================================================================

    @api.depends('start_date', 'term_months')
    def _compute_end_date(self):
        """Calculate end date from start date and term"""
        for wizard in self:
            if wizard.start_date and wizard.term_months:
                wizard.end_date = wizard.start_date + timedelta(days=wizard.term_months * 30)
            else:
                wizard.end_date = False

    # ==========================================================================
    # Business Methods
    # ==========================================================================

    def action_create_lease(self):
        """Create the lease from wizard data"""
        self.ensure_one()

        # Validate dates
        if self.start_date >= self.end_date:
            raise ValidationError(_("Start date must be before end date."))

        # Check for overlapping leases
        self._check_overlapping_leases()

        # Create lease
        lease_vals = self._prepare_lease_vals()
        lease = self.env['property.lease'].create(lease_vals)

        # Handle signature request
        if self.send_signature and self.env['sign.request']._check_sign_required():
            lease.action_send_signature()

        # Create invoices if requested
        if self.create_invoices:
            lease._create_invoices()

        # Update property/unit status
        self._update_status(lease)

        # Return action to open the lease
        return {
            'type': 'ir.actions.act_window',
            'name': _('Lease Created'),
            'res_model': 'property.lease',
            'res_id': lease.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _prepare_lease_vals(self):
        """Prepare lease creation values"""
        self.ensure_one()
        return {
            'property_id': self.property_id.id,
            'unit_id': self.unit_id.id if self.unit_id else False,
            'tenant_id': self.tenant_id.id,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'term_months': self.term_months,
            'rent_amount': self.rent_amount,
            'deposit_amount': self.deposit_amount,
            'rent_frequency': self.rent_frequency,
            'renewal_options': self.renewal_options,
            'terms_conditions': self.terms_conditions,
            'special_terms': self.special_terms,
            'status': 'draft',
        }

    def _check_overlapping_leases(self):
        """Check for overlapping leases on property/unit"""
        self.ensure_one()

        domain = [
            ('status', 'in', ['signed', 'active']),
            '|', ('start_date', '<=', self.end_date),
            ('end_date', '>=', self.start_date)
        ]

        if self.unit_id:
            domain.append(('unit_id', '=', self.unit_id.id))
        else:
            domain.append(('property_id', '=', self.property_id.id))

        overlapping = self.env['property.lease'].search(domain)
        if overlapping:
            raise ValidationError(
                _("There is already an active lease for this property/unit "
                  "during the specified dates.")
            )

    def _update_status(self, lease):
        """Update property/unit status after lease creation"""
        self.ensure_one()

        # Update unit status if applicable
        if self.unit_id:
            self.unit_id.status = 'pending_inspection'

        # Update property status
        if self.property_id.status in ['draft', 'listed']:
            self.property_id.status = 'under_offer'

    @api.onchange('property_id')
    def _onchange_property_id(self):
        """Set default values from property"""
        if self.property_id:
            self.rent_amount = self.property_id.rental_price or 0.0
            self.deposit_amount = self.property_id.rental_deposit or 0.0
            self.currency_id = self.property_id.currency_id

            # Reset unit domain
            self.unit_id = False

    @api.onchange('unit_id')
    def _onchange_unit_id(self):
        """Set values from unit if selected"""
        if self.unit_id:
            self.rent_amount = self.unit_id.rent_amount or self.rent_amount
            self.deposit_amount = self.unit_id.deposit_amount or self.deposit_amount
            