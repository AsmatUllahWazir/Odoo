# -*- coding: utf-8 -*-
"""
Tenant Screening Wizard - Quick screening creation
"""

from odoo import api, fields, models, _


class PropertyTenantScreeningWizard(models.TransientModel):
    """
    Wizard for creating a tenant screening
    """
    _name = 'property.screening.wizard'
    _description = 'Create Tenant Screening Wizard'

    # ==========================================================================
    # Wizard Fields
    # ==========================================================================

    applicant_id = fields.Many2one(
        'res.partner',
        string='Applicant',
        required=True,
        domain="[('is_company', '=', False)]",
        help='Applicant to screen'
    )

    property_id = fields.Many2one(
        'property.property',
        string='Property',
        required=True,
        help='Property being applied for'
    )

    unit_id = fields.Many2one(
        'property.unit',
        string='Unit',
        help='Specific unit if multi-unit',
        domain="[('property_id', '=', property_id)]"
    )

    viewing_id = fields.Many2one(
        'property.viewing',
        string='Viewing',
        help='Related viewing if applicable'
    )

    credit_score = fields.Integer(
        string='Credit Score',
        help='Applicant credit score (300-850)'
    )

    income_monthly = fields.Monetary(
        string='Monthly Income',
        help='Applicant monthly income'
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        related='property_id.currency_id',
        readonly=True
    )

    employment_status = fields.Selection([
        ('employed', 'Employed'),
        ('self_employed', 'Self-Employed'),
        ('retired', 'Retired'),
        ('student', 'Student'),
        ('unemployed', 'Unemployed'),
    ], string='Employment Status')

    employer_name = fields.Char(
        string='Employer Name'
    )

    employment_duration = fields.Char(
        string='Employment Duration'
    )

    previous_address = fields.Char(
        string='Previous Address'
    )

    previous_landlord = fields.Char(
        string='Previous Landlord'
    )

    reference_1 = fields.Char(
        string='Reference 1'
    )

    reference_2 = fields.Char(
        string='Reference 2'
    )

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
        string='Pets Allowed'
    )

    pet_details = fields.Text(
        string='Pet Details',
        attrs="{'invisible': [('pets_allowed', '=', False)]}"
    )

    smoking = fields.Boolean(
        string='Smoking Allowed'
    )

    move_in_date = fields.Date(
        string='Preferred Move-in Date'
    )

    notes = fields.Text(
        string='Additional Notes'
    )

    # ==========================================================================
    # Business Methods
    # ==========================================================================

    def action_create_screening(self):
        """Create the tenant screening"""
        self.ensure_one()

        # Create screening
        screening_vals = self._prepare_screening_vals()
        screening = self.env['property.tenant.screening'].create(screening_vals)

        # Link to viewing if provided
        if self.viewing_id:
            self.viewing_id.screening_id = screening.id

        # Return action to open screening
        return {
            'type': 'ir.actions.act_window',
            'name': _('Tenant Screening'),
            'res_model': 'property.tenant.screening',
            'res_id': screening.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _prepare_screening_vals(self):
        """Prepare screening creation values"""
        self.ensure_one()
        return {
            'applicant_id': self.applicant_id.id,
            'property_id': self.property_id.id,
            'unit_id': self.unit_id.id if self.unit_id else False,
            'viewing_id': self.viewing_id.id if self.viewing_id else False,
            'credit_score': self.credit_score or 0,
            'income_monthly': self.income_monthly or 0.0,
            'employment_status': self.employment_status,
            'employer_name': self.employer_name,
            'employment_duration': self.employment_duration,
            'previous_address': self.previous_address,
            'previous_landlord': self.previous_landlord,
            'reference_1': self.reference_1,
            'reference_2': self.reference_2,
            'criminal_background': self.criminal_background,
            'eviction_history': self.eviction_history,
            'pets_allowed': self.pets_allowed,
            'pet_details': self.pet_details,
            'smoking': self.smoking,
            'move_in_date': self.move_in_date,
            'status': 'draft',
            'sales_person_id': self.env.user.id,
        }

    @api.onchange('property_id')
    def _onchange_property_id(self):
        """Reset unit when property changes"""
        self.unit_id = False

    @api.onchange('credit_score')
    def _onchange_credit_score(self):
        """Validate credit score range"""
        if self.credit_score and (self.credit_score < 300 or self.credit_score > 850):
            return {
                'warning': {
                    'title': _("Invalid Credit Score"),
                    'message': _("Credit score must be between 300 and 850."),
                }
            }
