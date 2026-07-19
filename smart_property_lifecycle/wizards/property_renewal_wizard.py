# -*- coding: utf-8 -*-
"""
Lease Renewal Wizard - Handle lease renewals
"""

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta


class PropertyLeaseRenewalWizard(models.TransientModel):
    """
    Wizard for renewing a lease
    """
    _name = 'property.lease.renewal.wizard'
    _description = 'Lease Renewal Wizard'

    # ==========================================================================
    # Wizard Fields
    # ==========================================================================

    lease_id = fields.Many2one(
        'property.lease',
        string='Lease',
        required=True,
        help='Lease to renew'
    )

    renewal_type = fields.Selection([
        ('fixed_term', 'Fixed Term'),
        ('month_to_month', 'Month to Month'),
    ], string='Renewal Type', required=True, default='fixed_term')

    new_start_date = fields.Date(
        string='New Start Date',
        required=True,
        help='Start date for renewed lease'
    )

    new_end_date = fields.Date(
        string='New End Date',
        compute='_compute_new_end_date',
        store=False,
        help='End date for renewed lease'
    )

    renewal_term = fields.Integer(
        string='Renewal Term (Months)',
        required=True,
        default=12,
        help='Duration of renewal'
    )

    new_rent_amount = fields.Monetary(
        string='New Rent Amount',
        required=True,
        help='Rent amount for renewed lease'
    )

    rent_increase_percent = fields.Float(
        string='Rent Increase (%)',
        help='Percentage increase in rent'
    )

    new_deposit_amount = fields.Monetary(
        string='New Deposit Amount',
        help='Deposit amount for renewed lease'
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        related='lease_id.currency_id',
        readonly=True
    )

    renewal_notes = fields.Text(
        string='Renewal Notes',
        help='Notes about the renewal'
    )

    create_new_lease = fields.Boolean(
        string='Create New Lease',
        default=True,
        help='Create new lease record for renewal'
    )

    update_existing = fields.Boolean(
        string='Update Existing Lease',
        default=False,
        help='Update existing lease with new dates'
    )

    # ==========================================================================
    # Computed Fields
    # ==========================================================================

    @api.depends('new_start_date', 'renewal_term')
    def _compute_new_end_date(self):
        """Calculate new end date"""
        for wizard in self:
            if wizard.new_start_date and wizard.renewal_term:
                wizard.new_end_date = wizard.new_start_date + timedelta(days=wizard.renewal_term * 30)
            else:
                wizard.new_end_date = False

    # ==========================================================================
    # Business Methods
    # ==========================================================================

    def action_renew_lease(self):
        """Process the lease renewal"""
        self.ensure_one()

        if self.renewal_type == 'month_to_month':
            self.renewal_term = 1  # Month to month

        # Validate dates
        if self.new_start_date >= self.new_end_date:
            raise ValidationError(_("Start date must be before end date."))

        if self.new_start_date < fields.Date.today():
            raise ValidationError(_("Start date cannot be in the past."))

        # Process renewal
        if self.create_new_lease:
            result = self._create_renewal_lease()
        else:
            result = self._update_existing_lease()

        return result

    def _create_renewal_lease(self):
        """Create a new lease for the renewal"""
        self.ensure_one()

        # Get existing lease data
        old_lease = self.lease_id

        # Create new lease
        lease_vals = {
            'property_id': old_lease.property_id.id,
            'unit_id': old_lease.unit_id.id if old_lease.unit_id else False,
            'tenant_id': old_lease.tenant_id.id,
            'start_date': self.new_start_date,
            'end_date': self.new_end_date,
            'term_months': self.renewal_term,
            'rent_amount': self.new_rent_amount,
            'deposit_amount': self.new_deposit_amount or old_lease.deposit_amount,
            'rent_frequency': old_lease.rent_frequency,
            'renewal_options': self.renewal_type,
            'terms_conditions': old_lease.terms_conditions,
            'special_terms': old_lease.special_terms or self.renewal_notes,
            'status': 'draft',
        }

        new_lease = self.env['property.lease'].create(lease_vals)

        # Mark old lease as terminated with renewal note
        old_lease.status = 'terminated'
        old_lease.termination_reason = f"Renewed - New lease {new_lease.name}"
        old_lease.termination_date = self.new_start_date - timedelta(days=1)

        # Return action to open new lease
        return {
            'type': 'ir.actions.act_window',
            'name': _('Renewed Lease'),
            'res_model': 'property.lease',
            'res_id': new_lease.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _update_existing_lease(self):
        """Update the existing lease with new dates"""
        self.ensure_one()

        old_lease = self.lease_id

        # Update old lease
        old_lease.write({
            'start_date': self.new_start_date,
            'end_date': self.new_end_date,
            'term_months': self.renewal_term,
            'rent_amount': self.new_rent_amount,
            'deposit_amount': self.new_deposit_amount or old_lease.deposit_amount,
            'renewal_options': self.renewal_type,
            'renewal_terms': self.renewal_notes,
            'status': 'active',
        })

        old_lease.message_post(
            body=_("Lease renewed. New end date: %s, New rent: %s") % (
                self.new_end_date,
                self.new_rent_amount
            ),
            message_type='notification'
        )

        return {
            'type': 'ir.actions.act_window',
            'name': _('Updated Lease'),
            'res_model': 'property.lease',
            'res_id': old_lease.id,
            'view_mode': 'form',
            'target': 'current',
        }

    @api.onchange('lease_id')
    def _onchange_lease_id(self):
        """Set default values from existing lease"""
        if self.lease_id:
            self.new_start_date = self.lease_id.end_date + timedelta(days=1)
            self.new_rent_amount = self.lease_id.rent_amount
            self.new_deposit_amount = self.lease_id.deposit_amount
            self.renewal_term = self.lease_id.term_months

            # Calculate suggested rent increase (3%)
            if self.lease_id.rent_amount > 0:
                self.rent_increase_percent = 3.0
                self.new_rent_amount = self.lease_id.rent_amount * 1.03

    @api.onchange('rent_increase_percent')
    def _onchange_rent_increase(self):
        """Calculate new rent from percentage increase"""
        if self.lease_id and self.rent_increase_percent:
            self.new_rent_amount = self.lease_id.rent_amount * (1 + self.rent_increase_percent / 100)


class PropertyLeaseTerminateWizard(models.TransientModel):
    """
    Wizard for terminating a lease
    """
    _name = 'property.lease.terminate.wizard'
    _description = 'Terminate Lease Wizard'

    # ==========================================================================
    # Wizard Fields
    # ==========================================================================

    lease_id = fields.Many2one(
        'property.lease',
        string='Lease',
        required=True,
        help='Lease to terminate'
    )

    termination_date = fields.Date(
        string='Termination Date',
        required=True,
        default=fields.Date.today,
        help='Date of termination'
    )

    termination_reason = fields.Selection([
        ('mutual', 'Mutual Agreement'),
        ('tenant', 'Tenant Initiated'),
        ('owner', 'Owner Initiated'),
        ('breach', 'Breach of Contract'),
        ('non_payment', 'Non-Payment'),
        ('sale', 'Property Sold'),
        ('other', 'Other'),
    ], string='Reason for Termination', required=True, default='mutual')

    termination_notes = fields.Text(
        string='Notes',
        help='Additional notes about termination'
    )

    return_deposit = fields.Boolean(
        string='Return Deposit',
        default=True,
        help='Return security deposit'
    )

    deposit_return_date = fields.Date(
        string='Deposit Return Date',
        help='Date deposit is returned'
    )

    deposit_deductions = fields.Monetary(
        string='Deposit Deductions',
        help='Amount to deduct from deposit'
    )

    deposit_returned_amount = fields.Monetary(
        string='Deposit Returned Amount',
        compute='_compute_deposit_returned',
        store=False,
        help='Amount to return after deductions'
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        related='lease_id.currency_id',
        readonly=True
    )

    # ==========================================================================
    # Computed Fields
    # ==========================================================================

    @api.depends('lease_id.deposit_amount', 'deposit_deductions')
    def _compute_deposit_returned(self):
        """Calculate deposit amount to return"""
        for wizard in self:
            if wizard.lease_id and wizard.return_deposit:
                wizard.deposit_returned_amount = wizard.lease_id.deposit_amount - (wizard.deposit_deductions or 0.0)
            else:
                wizard.deposit_returned_amount = 0.0

    # ==========================================================================
    # Business Methods
    # ==========================================================================

    def action_terminate_lease(self):
        """Process the lease termination"""
        self.ensure_one()

        lease = self.lease_id

        # Update lease
        lease.write({
            'status': 'terminated',
            'termination_date': self.termination_date,
            'termination_reason': f"{self.termination_reason}: {self.termination_notes}" if self.termination_notes else self.termination_reason,
            'deposit_returned': self.return_deposit,
            'deposit_return_date': self.deposit_return_date if self.return_deposit else False,
        })

        # Post message
        lease.message_post(
            body=_("Lease terminated on %s. Reason: %s") % (
                self.termination_date,
                dict(self._fields['termination_reason'].selection).get(self.termination_reason)
            ),
            message_type='notification'
        )

        # Update property status
        if lease.property_id:
            lease.property_id.status = 'listed'

        # Update unit status
        if lease.unit_id:
            lease.unit_id.status = 'vacant'

        return {
            'type': 'ir.actions.act_window',
            'name': _('Lease Terminated'),
            'res_model': 'property.lease',
            'res_id': lease.id,
            'view_mode': 'form',
            'target': 'current',
        }
    