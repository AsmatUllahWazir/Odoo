# -*- coding: utf-8 -*-
"""
Property Unit Model - For multi-unit buildings and sub-units
"""

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class PropertyUnit(models.Model):
    """
    Property Unit - Individual units within a multi-unit property
    """
    _name = 'property.unit'
    _description = 'Property Unit'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'unit_number'
    _rec_name = 'display_name'

    # ==========================================================================
    # Basic Information
    # ==========================================================================

    property_id = fields.Many2one(
        'property.property',
        string='Property',
        required=True,
        ondelete='cascade',
        help='Parent property building'
    )

    unit_number = fields.Char(
        string='Unit Number',
        required=True,
        help='Unit designation (e.g., A101, 2B, PH)'
    )

    floor_number = fields.Integer(
        string='Floor Number',
        help='Floor level (0 for ground)'
    )

    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True,
        help='Unit full display name'
    )

    unit_type = fields.Selection([
        ('studio', 'Studio'),
        ('1_bed', '1 Bedroom'),
        ('2_bed', '2 Bedroom'),
        ('3_bed', '3 Bedroom'),
        ('4_bed', '4+ Bedroom'),
        ('loft', 'Loft'),
        ('penthouse', 'Penthouse'),
        ('commercial', 'Commercial Space'),
    ], string='Unit Type', required=True, default='1_bed')

    status = fields.Selection([
        ('vacant', 'Vacant'),
        ('occupied', 'Occupied'),
        ('under_maintenance', 'Under Maintenance'),
        ('pending_inspection', 'Pending Inspection'),
        ('archived', 'Archived'),
    ], string='Status', required=True, default='vacant', tracking=True)

    # ==========================================================================
    # Specifications
    # ==========================================================================

    unit_area = fields.Float(
        string='Unit Area (sq ft)',
        required=True,
        help='Unit square footage'
    )

    bedrooms = fields.Integer(
        string='Bedrooms',
        help='Number of bedrooms in this unit'
    )

    bathrooms = fields.Float(
        string='Bathrooms',
        help='Number of bathrooms (can be decimal for half baths)'
    )

    balcony_area = fields.Float(
        string='Balcony Area (sq ft)',
        help='Balcony/patio square footage'
    )

    parking_spaces = fields.Integer(
        string='Parking Spaces',
        default=0,
        help='Number of parking spaces included'
    )

    storage_unit = fields.Boolean(
        string='Has Storage Unit',
        help='Whether unit has a dedicated storage space'
    )

    # ==========================================================================
    # Pricing & Financial
    # ==========================================================================

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        related='property_id.currency_id',
        store=True,
        readonly=True
    )

    unit_price = fields.Monetary(
        string='Unit Price',
        currency_field='currency_id',
        help='Price for this individual unit'
    )

    rent_amount = fields.Monetary(
        string='Monthly Rent',
        currency_field='currency_id',
        help='Monthly rent for this unit'
    )

    deposit_amount = fields.Monetary(
        string='Deposit Amount',
        currency_field='currency_id',
        help='Security deposit for this unit'
    )

    hoa_fees = fields.Monetary(
        string='HOA Fees (Monthly)',
        currency_field='currency_id',
        help='Monthly HOA fees for this unit'
    )

    # ==========================================================================
    # Relationships
    # ==========================================================================

    lease_ids = fields.One2many(
        'property.lease',
        'unit_id',
        string='Leases',
        help='Lease agreements for this unit'
    )

    active_lease_id = fields.Many2one(
        'property.lease',
        string='Active Lease',
        compute='_compute_active_lease',
        store=True,
        help='Current active lease for this unit'
    )

    current_tenant_id = fields.Many2one(
        'res.partner',
        string='Current Tenant',
        compute='_compute_current_tenant',
        store=True,
        help='Current tenant occupying this unit'
    )

    maintenance_request_ids = fields.One2many(
        'property.maintenance.request',
        'unit_id',
        string='Maintenance Requests',
        help='Maintenance requests for this unit'
    )

    # ==========================================================================
    # Computed Fields
    # ==========================================================================

    @api.depends('property_id.name', 'unit_number', 'property_id.property_code')
    def _compute_display_name(self):
        """Compute full display name with property and unit number"""
        for record in self:
            if record.property_id:
                record.display_name = f"{record.property_id.name} - Unit {record.unit_number}"
            else:
                record.display_name = f"Unit {record.unit_number}"

    @api.depends('lease_ids', 'lease_ids.status')
    def _compute_active_lease(self):
        """Find current active lease for this unit"""
        for record in self:
            active = record.lease_ids.filtered(lambda l: l.status == 'active')
            record.active_lease_id = active[:1] if active else False

    @api.depends('active_lease_id.tenant_id')
    def _compute_current_tenant(self):
        """Get current tenant from active lease"""
        for record in self:
            record.current_tenant_id = record.active_lease_id.tenant_id if record.active_lease_id else False

    @api.depends('lease_ids')
    def _compute_occupancy(self):
        """Compute if unit is occupied"""
        for record in self:
            record.is_occupied = bool(record.active_lease_id)

    is_occupied = fields.Boolean(
        string='Is Occupied',
        compute='_compute_occupancy',
        store=True
    )

    # ==========================================================================
    # Constraints
    # ==========================================================================

    _sql_constraints = [
        ('unit_number_property_unique',
         'unique(property_id, unit_number)',
         'Unit number must be unique within the property!'),
        ('check_unit_area_positive', 'CHECK(unit_area > 0)',
         'Unit area must be positive'),
        ('check_rent_positive', 'CHECK(rent_amount >= 0)',
         'Rent amount cannot be negative'),
        ('check_price_positive', 'CHECK(unit_price >= 0)',
         'Unit price cannot be negative'),
    ]

    @api.constrains('unit_area', 'property_id.area_total')
    def _check_area_constraints(self):
        """Ensure unit area doesn't exceed property total area"""
        for record in self:
            if record.property_id and record.property_id.area_total:
                if record.unit_area > record.property_id.area_total:
                    raise ValidationError(
                        _("Unit area cannot exceed total property area.")
                    )

    # ==========================================================================
    # Business Methods
    # ==========================================================================

    def action_vacate_unit(self):
        """Vacate the unit (end all active leases)"""
        for record in self:
            active_leases = record.lease_ids.filtered(lambda l: l.status == 'active')
            if active_leases:
                for lease in active_leases:
                    lease.action_terminate()
                record.status = 'vacant'
                record.message_post(
                    body=_("Unit vacated and all active leases terminated."),
                    message_type='notification'
                )
            else:
                record.status = 'vacant'

    def action_occupy_unit(self):
        """Mark unit as occupied"""
        for record in self:
            if not record.active_lease_id:
                raise ValidationError(
                    _("Cannot mark unit as occupied without an active lease.")
                )
            record.status = 'occupied'

    def action_maintenance_unit(self):
        """Mark unit for maintenance"""
        for record in self:
            if record.status == 'occupied' and record.active_lease_id:
                # Notify tenant
                record.message_post(
                    body=_("Unit going into maintenance mode. Tenant will be notified."),
                    message_type='notification'
                )
            record.status = 'under_maintenance'

    def _get_tenant_notification_list(self):
        """Get list of users/partners to notify about unit events"""
        recipients = []
        if self.current_tenant_id:
            recipients.append(self.current_tenant_id)
        if self.property_id.manager_id:
            recipients.append(self.property_id.manager_id.partner_id)
        return recipients
    