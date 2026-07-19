# -*- coding: utf-8 -*-
"""
Property Tenant Screening Model - Background check and approval workflow
"""

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class PropertyTenantScreening(models.Model):
    """
    Property Tenant Screening - Complete tenant screening and approval
    """
    _name = 'property.tenant.screening'
    _description = 'Property Tenant Screening'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'
    _rec_name = 'display_name'

    # ==========================================================================
    # Basic Information
    # ==========================================================================

    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True
    )

    applicant_id = fields.Many2one(
        'res.partner',
        string='Applicant',
        required=True,
        tracking=True,
        domain="[('is_company', '=', False)]"
    )

    property_id = fields.Many2one(
        'property.property',
        string='Property',
        required=True,
        tracking=True
    )

    unit_id = fields.Many2one(
        'property.unit',
        string='Unit',
        help='Specific unit applicant is interested in'
    )

    viewing_id = fields.Many2one(
        'property.viewing',
        string='Viewing',
        help='Related viewing appointment'
    )

    sales_person_id = fields.Many2one(
        'res.users',
        string='Sales Person',
        default=lambda self: self.env.user,
        tracking=True
    )

    # ==========================================================================
    # Screening Details
    # ==========================================================================

    status = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('in_review', 'In Review'),
        ('additional_info', 'Additional Info Required'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('waitlisted', 'Waitlisted'),
    ], string='Status', required=True, default='draft', tracking=True)

    application_date = fields.Date(
        string='Application Date',
        default=fields.Date.today,
        required=True
    )

    decision_date = fields.Date(
        string='Decision Date',
        help='Date of final decision'
    )

    # ==========================================================================
    # Background Information
    # ==========================================================================

    credit_score = fields.Integer(
        string='Credit Score',
        tracking=True,
        help='Applicant credit score'
    )

    income_monthly = fields.Monetary(
        string='Monthly Income',
        currency_field='currency_id',
        help='Applicant monthly income'
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        related='property_id.currency_id',
        store=True,
        readonly=True
    )

    employment_status = fields.Selection([
        ('employed', 'Employed'),
        ('self_employed', 'Self-Employed'),
        ('retired', 'Retired'),
        ('student', 'Student'),
        ('unemployed', 'Unemployed'),
    ], string='Employment Status', tracking=True)

    employer_name = fields.Char(
        string='Employer Name',
        help='Current employer'
    )

    employment_duration = fields.Char(
        string='Employment Duration',
        help='Duration of current employment'
    )

    previous_address = fields.Char(
        string='Previous Address',
        help='Applicant previous address'
    )

    previous_landlord = fields.Char(
        string='Previous Landlord',
        help='Reference from previous landlord'
    )

    reference_1 = fields.Char(
        string='Reference 1',
        help='First reference contact'
    )

    reference_2 = fields.Char(
        string='Reference 2',
        help='Second reference contact'
    )

    # ==========================================================================
    # Screening Questions
    # ==========================================================================

    criminal_background = fields.Selection([
        ('clear', 'Clear'),
        ('minor', 'Minor Issues'),
        ('major', 'Major Issues'),
        ('pending', 'Pending Review'),
    ], string='Criminal Background', default='pending')

    eviction_history = fields.Selection([
        ('none', 'None'),
        ('1_year', 'Within 1 Year'),
        ('2_years', 'Within 2 Years'),
        ('over_2_years', 'Over 2 Years Ago'),
    ], string='Eviction History', default='none')

    pets_allowed = fields.Boolean(
        string='Pets Allowed',
        help='Whether applicant has pets'
    )

    pet_details = fields.Text(
        string='Pet Details',
        help='Description of pets (type, breed, size)'
    )

    smoking = fields.Boolean(
        string='Smoking Allowed',
        help='Whether applicant is a smoker'
    )

    move_in_date = fields.Date(
        string='Preferred Move-in Date',
        help='Date applicant wishes to move in'
    )

    # ==========================================================================
    # Scoring and Decision
    # ==========================================================================

    screening_score = fields.Float(
        string='Screening Score',
        compute='_compute_screening_score',
        store=True,
        help='Calculated screening score (0-100)'
    )

    approval_recommendation = fields.Selection([
        ('strong_approve', 'Strong Approve'),
        ('approve', 'Approve'),
        ('conditional', 'Conditional'),
        ('reject', 'Reject'),
    ], string='Approval Recommendation', compute='_compute_screening_score', store=True)

    risk_level = fields.Selection([
        ('low', 'Low Risk'),
        ('medium', 'Medium Risk'),
        ('high', 'High Risk'),
    ], string='Risk Level', compute='_compute_screening_score', store=True)

    decision_notes = fields.Text(
        string='Decision Notes',
        help='Notes on approval/rejection decision'
    )

    # ==========================================================================
    # Documents
    # ==========================================================================

    document_ids = fields.One2many(
        'ir.attachment',
        'res_id',
        domain=[('res_model', '=', 'property.tenant.screening')],
        string='Documents',
        help='Uploaded screening documents'
    )

    id_verification = fields.Boolean(
        string='ID Verified',
        default=False,
        help='Whether applicant ID has been verified'
    )

    income_verified = fields.Boolean(
        string='Income Verified',
        default=False,
        help='Whether income has been verified'
    )

    # ==========================================================================
    # Computed Fields
    # ==========================================================================

    @api.depends('applicant_id', 'property_id')
    def _compute_display_name(self):
        """Compute display name"""
        for record in self:
            applicant = record.applicant_id.name if record.applicant_id else ''
            property_name = record.property_id.name if record.property_id else ''
            record.display_name = f"Screening - {applicant} - {property_name}"

    @api.depends('credit_score', 'income_monthly', 'criminal_background',
                 'eviction_history', 'employment_status')
    def _compute_screening_score(self):
        """
        Compute comprehensive screening score based on multiple factors
        """
        for record in self:
            score = 0
            risk = 'medium'
            recommendation = 'conditional'

            # Credit Score (max 25 points)
            if record.credit_score:
                if record.credit_score >= 750:
                    score += 25
                    risk = 'low'
                elif record.credit_score >= 700:
                    score += 20
                    risk = 'low'
                elif record.credit_score >= 650:
                    score += 15
                    risk = 'medium'
                elif record.credit_score >= 600:
                    score += 10
                    risk = 'medium'
                else:
                    score += 5
                    risk = 'high'

            # Income vs Rent Ratio (max 20 points)
            if record.income_monthly and record.property_id.rental_price:
                ratio = record.income_monthly / record.property_id.rental_price if record.property_id.rental_price > 0 else 0
                if ratio >= 3.0:
                    score += 20
                elif ratio >= 2.5:
                    score += 15
                elif ratio >= 2.0:
                    score += 10
                else:
                    score += 5

            # Criminal Background (max 15 points)
            if record.criminal_background == 'clear':
                score += 15
            elif record.criminal_background == 'minor':
                score += 8
            elif record.criminal_background == 'pending':
                score += 5
            else:
                score += 0

            # Eviction History (max 15 points)
            if record.eviction_history == 'none':
                score += 15
            elif record.eviction_history == 'over_2_years':
                score += 10
            elif record.eviction_history == '2_years':
                score += 5
            else:
                score += 0

            # Employment Status (max 15 points)
            if record.employment_status in ['employed', 'self_employed']:
                score += 15
                risk = 'low'
            elif record.employment_status == 'retired':
                score += 10
            else:
                score += 5

            # References (max 10 points)
            if record.reference_1 and record.reference_2:
                score += 10
            elif record.reference_1:
                score += 5

            # Additional points for verification (max 10 points)
            if record.id_verification:
                score += 5
            if record.income_verified:
                score += 5

            # Determine recommendation
            if score >= 80:
                recommendation = 'strong_approve'
                risk = 'low'
            elif score >= 70:
                recommendation = 'approve'
                risk = 'low'
            elif score >= 60:
                recommendation = 'conditional'
                risk = 'medium'
            else:
                recommendation = 'reject'
                risk = 'high'

            record.screening_score = min(score, 100)
            record.approval_recommendation = recommendation
            record.risk_level = risk

    # ==========================================================================
    # Constraints
    # ==========================================================================

    @api.constrains('credit_score')
    def _check_credit_score(self):
        """Validate credit score range"""
        for record in self:
            if record.credit_score and (record.credit_score < 300 or record.credit_score > 850):
                raise ValidationError(
                    _("Credit score must be between 300 and 850.")
                )

    @api.constrains('income_monthly')
    def _check_income(self):
        """Validate income is positive"""
        for record in self:
            if record.income_monthly and record.income_monthly < 0:
                raise ValidationError(
                    _("Income cannot be negative.")
                )

    # ==========================================================================
    # Business Methods
    # ==========================================================================

    def action_submit(self):
        """Submit screening for review"""
        for record in self:
            if record.status != 'draft':
                raise ValidationError(_("Only draft screenings can be submitted."))
            record.status = 'submitted'
            record.message_post(
                body=_("Screening submitted for review."),
                message_type='notification'
            )

    def action_start_review(self):
        """Start reviewing screening"""
        for record in self:
            if record.status != 'submitted':
                raise ValidationError(_("Only submitted screenings can be reviewed."))
            record.status = 'in_review'
            record.message_post(
                body=_("Screening review started."),
                message_type='notification'
            )

    def action_request_info(self):
        """Request additional information"""
        for record in self:
            if record.status not in ['in_review', 'submitted']:
                raise ValidationError(_("Cannot request additional info at this stage."))
            record.status = 'additional_info'
            record.message_post(
                body=_("Additional information requested from applicant."),
                message_type='notification'
            )

    def action_approve(self):
        """Approve the screening"""
        for record in self:
            if record.status in ['approved', 'rejected']:
                raise ValidationError(_("This screening has already been decided."))
            record.status = 'approved'
            record.decision_date = fields.Date.today()
            record.message_post(
                body=_("Screening approved."),
                message_type='notification'
            )

    def action_reject(self):
        """Reject the screening"""
        for record in self:
            if record.status in ['approved', 'rejected']:
                raise ValidationError(_("This screening has already been decided."))
            record.status = 'rejected'
            record.decision_date = fields.Date.today()
            record.message_post(
                body=_("Screening rejected."),
                message_type='notification'
            )

    def action_create_lease(self):
        """Create a lease from approved screening"""
        self.ensure_one()
        if self.status != 'approved':
            raise ValidationError(_("Screening must be approved to create a lease."))

        # Create lease with default values
        lease_vals = {
            'property_id': self.property_id.id,
            'tenant_id': self.applicant_id.id,
            'unit_id': self.unit_id.id if self.unit_id else False,
            'start_date': self.move_in_date or fields.Date.today() + timedelta(days=30),
            'end_date': fields.Date.today() + timedelta(days=30 * 12),
            'rent_amount': self.property_id.rental_price,
            'deposit_amount': self.property_id.rental_deposit,
            'term_months': 12,
        }

        lease = self.env['property.lease'].create(lease_vals)

        return {
            'type': 'ir.actions.act_window',
            'name': _('Create Lease'),
            'res_model': 'property.lease',
            'res_id': lease.id,
            'view_mode': 'form',
            'target': 'current',
        }
    