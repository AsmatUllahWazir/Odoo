# -*- coding: utf-8 -*-
"""
Res Partner Extension - Add property-related fields to partners
"""

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    """
    Extend res.partner with property-related fields
    """
    _inherit = 'res.partner'

    # ==========================================================================
    # Property Owner Fields
    # ==========================================================================

    is_property_owner = fields.Boolean(
        string='Is Property Owner',
        help='Whether this partner owns properties'
    )

    owner_property_ids = fields.One2many(
        'property.property',
        'owner_id',
        string='Owned Properties',
        help='Properties owned by this partner'
    )

    owner_property_count = fields.Integer(
        string='Properties Owned',
        compute='_compute_owner_property_count',
        help='Number of properties owned'
    )

    # ==========================================================================
    # Tenant Fields
    # ==========================================================================

    is_tenant = fields.Boolean(
        string='Is Tenant',
        help='Whether this partner is a tenant'
    )

    tenant_lease_ids = fields.One2many(
        'property.lease',
        'tenant_id',
        string='Leases',
        help='Lease agreements for this tenant'
    )

    tenant_lease_count = fields.Integer(
        string='Active Leases',
        compute='_compute_tenant_lease_count',
        help='Number of active leases'
    )

    current_lease_id = fields.Many2one(
        'property.lease',
        string='Current Lease',
        compute='_compute_current_lease',
        help='Current active lease'
    )

    current_property_id = fields.Many2one(
        'property.property',
        string='Current Property',
        compute='_compute_current_property',
        help='Property currently leased'
    )

    # ==========================================================================
    # HOA Fields
    # ==========================================================================

    hoa_board_member_ids = fields.Many2many(
        'property.hoa.association',
        string='HOA Board Memberships',
        help='HOA associations where this partner is a board member'
    )

    hoa_board_member_count = fields.Integer(
        string='HOA Board Memberships',
        compute='_compute_hoa_board_count'
    )

    # ==========================================================================
    # Screening Fields
    # ==========================================================================

    screening_ids = fields.One2many(
        'property.tenant.screening',
        'applicant_id',
        string='Screenings',
        help='Tenant screening applications'
    )

    last_screening_date = fields.Date(
        string='Last Screening Date',
        compute='_compute_last_screening',
        help='Date of most recent screening'
    )

    screening_status = fields.Char(
        string='Screening Status',
        compute='_compute_screening_status',
        help='Most recent screening status'
    )

    # ==========================================================================
    # Computed Fields
    # ==========================================================================

    @api.depends('owner_property_ids')
    def _compute_owner_property_count(self):
        """Compute number of properties owned"""
        for record in self:
            record.owner_property_count = len(record.owner_property_ids)
            record.is_property_owner = bool(record.owner_property_ids)

    @api.depends('tenant_lease_ids', 'tenant_lease_ids.status')
    def _compute_tenant_lease_count(self):
        """Compute number of active leases"""
        for record in self:
            active_leases = record.tenant_lease_ids.filtered(
                lambda l: l.status in ['signed', 'active']
            )
            record.tenant_lease_count = len(active_leases)
            record.is_tenant = bool(active_leases)

    @api.depends('tenant_lease_ids', 'tenant_lease_ids.status')
    def _compute_current_lease(self):
        """Find current active lease"""
        for record in self:
            active_leases = record.tenant_lease_ids.filtered(
                lambda l: l.status == 'active'
            )
            record.current_lease_id = active_leases[:1] if active_leases else False

    @api.depends('current_lease_id.property_id')
    def _compute_current_property(self):
        """Get current property from active lease"""
        for record in self:
            record.current_property_id = record.current_lease_id.property_id if record.current_lease_id else False

    @api.depends('hoa_board_member_ids')
    def _compute_hoa_board_count(self):
        """Compute number of HOA board memberships"""
        for record in self:
            record.hoa_board_member_count = len(record.hoa_board_member_ids)

    @api.depends('screening_ids', 'screening_ids.application_date')
    def _compute_last_screening(self):
        """Get most recent screening date"""
        for record in self:
            if record.screening_ids:
                record.last_screening_date = max(record.screening_ids.mapped('application_date'))
            else:
                record.last_screening_date = False

    @api.depends('screening_ids', 'screening_ids.status')
    def _compute_screening_status(self):
        """Get most recent screening status"""
        for record in self:
            if record.screening_ids:
                latest = record.screening_ids.sorted('application_date', reverse=True)[:1]
                record.screening_status = latest.status if latest else ''
            else:
                record.screening_status = ''

    # ==========================================================================
    # Constraints
    # ==========================================================================

    @api.constrains('email')
    def _check_email_unique(self):
        """Ensure unique email for partners"""
        for record in self:
            if record.email:
                duplicates = self.search([
                    ('email', '=', record.email),
                    ('id', '!=', record.id)
                ])
                if duplicates:
                    raise ValidationError(
                        _("Email address '%s' already exists for another contact.") % record.email
                    )

    # ==========================================================================
    # Business Methods
    # ==========================================================================

    def action_view_owned_properties(self):
        """View all properties owned by this partner"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Owned Properties'),
            'res_model': 'property.property',
            'view_mode': 'tree,kanban,form',
            'domain': [('owner_id', '=', self.id)],
            'context': {'default_owner_id': self.id},
        }

    def action_view_leases(self):
        """View all leases for this tenant"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Leases'),
            'res_model': 'property.lease',
            'view_mode': 'tree,form',
            'domain': [('tenant_id', '=', self.id)],
            'context': {'default_tenant_id': self.id},
        }

    def action_view_screenings(self):
        """View all screenings for this applicant"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Tenant Screenings'),
            'res_model': 'property.tenant.screening',
            'view_mode': 'tree,form',
            'domain': [('applicant_id', '=', self.id)],
            'context': {'default_applicant_id': self.id},
        }

    def action_create_screening(self):
        """Create a new screening for this applicant"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Create Tenant Screening'),
            'res_model': 'property.screening.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_applicant_id': self.id,
            }
        }

    def action_view_hoa_associations(self):
        """View HOA associations for this partner"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('HOA Associations'),
            'res_model': 'property.hoa.association',
            'view_mode': 'tree,form',
            'domain': [('board_member_ids', 'in', self.id)],
        }

    # ==========================================================================
    # Override Methods
    # ==========================================================================

    @api.model
    def create(self, vals):
        """Override create to handle partner type detection"""
        partner = super(ResPartner, self).create(vals)

        # Auto-detect if partner should be an owner or tenant
        # This would typically be done through other business processes

        return partner
    