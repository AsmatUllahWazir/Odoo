# -*- coding: utf-8 -*-
"""
Property Property Model - Main property entity
Manages all property types with full lifecycle tracking
"""

from odoo import api, fields, models, tools, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta
import logging
import math

_logger = logging.getLogger(__name__)


class PropertyProperty(models.Model):
    """
    Main property model for real estate management
    Inherits mail.thread for messaging, mail.activity.mixin for activities,
    image.mixin for image handling
    """
    _name = 'property.property'
    _description = 'Property'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'image.mixin']
    _order = 'create_date desc'
    _rec_name = 'display_name'

    # ==========================================================================
    # Basic Information
    # ==========================================================================

    name = fields.Char(
        string='Property Name',
        required=True,
        tracking=True,
        help='Name or title of the property'
    )

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        help='Company associated with this property'
    )

    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True,
        index=True
    )

    property_code = fields.Char(
        string='Property Code',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: self.env['ir.sequence'].next_by_code('property.property') or _('New'),
        help='Unique property identification code'
    )

    type = fields.Selection([
        ('residential', 'Residential'),
        ('commercial', 'Commercial'),
        ('industrial', 'Industrial'),
        ('land', 'Land/Plot'),
        ('mixed_use', 'Mixed Use'),
        ('condo', 'Condo/Apartment'),
        ('multi_unit', 'Multi-Unit Building'),
    ], string='Property Type', required=True, tracking=True, default='residential')

    category = fields.Selection([
        ('sale', 'For Sale'),
        ('rent', 'For Rent'),
        ('sale_rent', 'Both Sale and Rent'),
    ], string='Category', required=True, tracking=True, default='sale')

    status = fields.Selection([
        ('draft', 'Draft'),
        ('listed', 'Listed'),
        ('under_offer', 'Under Offer'),
        ('pending_inspection', 'Pending Inspection'),
        ('leased', 'Leased'),
        ('sold', 'Sold'),
        ('maintenance', 'Under Maintenance'),
        ('archived', 'Archived'),
    ], string='Status', required=True, default='draft', tracking=True)

    active = fields.Boolean(
        string='Active',
        default=True,
        help='Inactive properties are hidden from views'
    )

    # ==========================================================================
    # Address Information
    # ==========================================================================

    partner_id = fields.Many2one(
        'res.partner',
        string='Associated Partner',
        help='Partner record for this property (for address management)'
    )

    street = fields.Char(string='Street', help='Street address')
    street2 = fields.Char(string='Street2', help='Additional address details')
    city = fields.Char(string='City', help='City name')
    state_id = fields.Many2one('res.country.state', string='State', help='State/Province')
    country_id = fields.Many2one('res.country', string='Country', help='Country')
    zip = fields.Char(string='ZIP', help='Postal code')

    latitude = fields.Float(string='Latitude', digits=(10, 6), help='GPS Latitude for maps')
    longitude = fields.Float(string='Longitude', digits=(10, 6), help='GPS Longitude for maps')

    full_address = fields.Char(
        string='Full Address',
        compute='_compute_full_address',
        store=True,
        help='Complete formatted address'
    )

    # ==========================================================================
    # Property Specifications
    # ==========================================================================

    bedrooms = fields.Integer(
        string='Bedrooms',
        help='Number of bedrooms',
        tracking=True
    )

    bathrooms = fields.Float(
        string='Bathrooms',
        help='Number of bathrooms (can be decimal for half baths)'
    )

    area_total = fields.Float(
        string='Total Area (sq ft)',
        help='Total square footage of the property',
        tracking=True
    )

    area_living = fields.Float(
        string='Living Area (sq ft)',
        help='Usable living space square footage'
    )

    area_land = fields.Float(
        string='Land Area (sq ft)',
        help='Total land area including grounds'
    )

    area_unit = fields.Selection([
        ('sqft', 'Square Feet'),
        ('sqm', 'Square Meters'),
        ('acres', 'Acres'),
        ('hectares', 'Hectares'),
    ], string='Area Unit', default='sqft')

    year_built = fields.Integer(
        string='Year Built',
        help='Construction year',
        tracking=True
    )

    year_renovated = fields.Integer(
        string='Year Renovated',
        help='Last major renovation year'
    )

    energy_rating = fields.Selection([
        ('a_plus', 'A+'),
        ('a', 'A'),
        ('b', 'B'),
        ('c', 'C'),
        ('d', 'D'),
        ('e', 'E'),
        ('f', 'F'),
        ('g', 'G'),
        ('not_rated', 'Not Rated'),
    ], string='Energy Rating', default='not_rated', help='Energy efficiency rating')

    description = fields.Html(
        string='Description',
        help='Detailed property description for marketing'
    )

    features = fields.Html(
        string='Features & Amenities',
        help='List of property features and amenities'
    )

    # ==========================================================================
    # Pricing Information
    # ==========================================================================

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        required=True,
        default=lambda self: self.env.company.currency_id,
        help='Currency used for pricing'
    )

    base_price = fields.Monetary(
        string='Base Price',
        currency_field='currency_id',
        required=True,
        tracking=True,
        help='Initial listing price'
    )

    dynamic_price = fields.Monetary(
        string='Dynamic Price',
        currency_field='currency_id',
        compute='_compute_dynamic_price',
        store=True,
        tracking=True,
        help='Current price adjusted by market factors'
    )

    price_sqft = fields.Monetary(
        string='Price per Sq Ft',
        currency_field='currency_id',
        compute='_compute_price_sqft',
        store=True,
        help='Price per square foot (base price)'
    )

    minimum_price = fields.Monetary(
        string='Minimum Price',
        currency_field='currency_id',
        help='Minimum acceptable price (for negotiations)'
    )

    rental_price = fields.Monetary(
        string='Rental Price',
        currency_field='currency_id',
        tracking=True,
        help='Monthly rental price if applicable'
    )

    rental_deposit = fields.Monetary(
        string='Rental Deposit',
        currency_field='currency_id',
        help='Security deposit amount'
    )

    hoa_fees = fields.Monetary(
        string='HOA/Maintenance Fees',
        currency_field='currency_id',
        help='Monthly HOA or maintenance fees'
    )

    total_revenue = fields.Monetary(
        string='Total Revenue',
        currency_field='currency_id',
        compute='_compute_total_revenue',
        store=True,
        help='Total revenue generated from this property'
    )

    # ==========================================================================
    # Ownership & Management
    # ==========================================================================

    owner_id = fields.Many2one(
        'res.partner',
        string='Owner',
        domain="[('is_company', '=', True)]",
        required=True,
        tracking=True,
        help='Property owner (company or individual)'
    )

    manager_id = fields.Many2one(
        'res.users',
        string='Property Manager',
        default=lambda self: self.env.user,
        tracking=True,
        help='Person responsible for managing this property'
    )

    sales_person_id = fields.Many2one(
        'res.users',
        string='Sales Person',
        help='Sales person responsible for this property'
    )

    # ==========================================================================
    # Marketing & Media
    # ==========================================================================

    website_published = fields.Boolean(
        string='Published on Website',
        default=False,
        help='Whether property is displayed on the website'
    )

    website_url = fields.Char(
        string='Website URL',
        compute='_compute_website_url',
        help='URL to property on website'
    )

    virtual_tour_url = fields.Char(
        string='Virtual Tour URL',
        help='Link to 3D virtual tour or 360° view'
    )

    ar_preview_url = fields.Char(
        string='AR Preview URL',
        help='Link to AR preview or 3D model'
    )

    youtube_video = fields.Char(
        string='YouTube Video ID',
        help='YouTube video ID for property video tour'
    )

    # ==========================================================================
    # IoT & Smart Features
    # ==========================================================================

    iot_device_ids = fields.One2many(
        'property.iot.device',
        'property_id',
        string='IoT Devices',
        help='Smart devices and sensors installed in property'
    )

    iot_enabled = fields.Boolean(
        string='IoT Enabled',
        compute='_compute_iot_enabled',
        store=True,
        help='Whether property has any IoT devices'
    )

    smart_lock_enabled = fields.Boolean(
        string='Smart Lock Enabled',
        help='Whether smart lock system is active'
    )

    security_system_enabled = fields.Boolean(
        string='Security System Enabled',
        help='Whether security system is active'
    )

    # ==========================================================================
    # Relationships
    # ==========================================================================

    unit_ids = fields.One2many(
        'property.unit',
        'property_id',
        string='Units',
        help='Individual units in multi-unit properties'
    )

    lease_ids = fields.One2many(
        'property.lease',
        'property_id',
        string='Leases',
        help='Property lease agreements'
    )

    active_lease_id = fields.Many2one(
        'property.lease',
        string='Active Lease',
        compute='_compute_active_lease',
        store=True,
        help='Current active lease for this property'
    )

    viewing_ids = fields.One2many(
        'property.viewing',
        'property_id',
        string='Viewings',
        help='Property viewing appointments'
    )

    maintenance_request_ids = fields.One2many(
        'property.maintenance.request',
        'property_id',
        string='Maintenance Requests',
        help='Maintenance and repair requests'
    )

    hoa_association_ids = fields.Many2many(
        'property.hoa.association',
        string='HOA Associations',
        help='HOA or condo associations this property belongs to'
    )

    # ==========================================================================
    # Computed Fields - Basic
    # ==========================================================================

    @api.depends('name', 'property_code')
    def _compute_display_name(self):
        """Compute display name with property code"""
        for record in self:
            record.display_name = f"{record.property_code} - {record.name}"

    @api.depends('street', 'street2', 'city', 'state_id', 'country_id', 'zip')
    def _compute_full_address(self):
        """Compute complete formatted address"""
        for record in self:
            parts = []
            if record.street:
                parts.append(record.street)
            if record.street2:
                parts.append(record.street2)
            if record.city:
                parts.append(record.city)
            if record.state_id:
                parts.append(record.state_id.name)
            if record.zip:
                parts.append(record.zip)
            if record.country_id:
                parts.append(record.country_id.name)
            record.full_address = ', '.join(parts)

    @api.depends('base_price', 'area_total')
    def _compute_price_sqft(self):
        """Compute price per square foot"""
        for record in self:
            if record.area_total and record.area_total > 0:
                record.price_sqft = record.base_price / record.area_total
            else:
                record.price_sqft = 0.0

    # ==========================================================================
    # Computed Fields - Dynamic Pricing
    # ==========================================================================

    @api.depends('base_price', 'type', 'status', 'year_built', 'energy_rating',
                 'bedrooms', 'bathrooms', 'area_living', 'area_land')
    def _compute_dynamic_price(self):
        """
        Compute dynamic price based on multiple factors
        Placeholder for pricing algorithm
        """
        for record in self:
            if record.base_price <= 0:
                record.dynamic_price = 0.0
                continue

            # Base price
            price = record.base_price

            # Type multiplier (placeholders)
            type_multipliers = {
                'residential': 1.0,
                'commercial': 1.2,
                'industrial': 1.15,
                'land': 0.8,
                'mixed_use': 1.25,
                'condo': 1.1,
                'multi_unit': 0.95,
            }
            price *= type_multipliers.get(record.type, 1.0)

            # Status multiplier
            if record.status in ['leased', 'sold']:
                price *= 0.9  # Adjusted for off-market

            # Year built adjustment (newer = higher)
            if record.year_built > 0:
                year_factor = 1 + (datetime.now().year - record.year_built) * 0.001
                price *= min(year_factor, 1.2)  # Cap at 20% increase

            # Energy rating premium
            energy_premiums = {
                'a_plus': 0.15,
                'a': 0.12,
                'b': 0.08,
                'c': 0.05,
                'd': 0.0,
                'e': -0.05,
                'f': -0.08,
                'g': -0.12,
                'not_rated': 0.0,
            }
            price *= (1 + energy_premiums.get(record.energy_rating, 0))

            # Apply minimum price constraint if set
            if record.minimum_price > 0:
                price = max(price, record.minimum_price)

            record.dynamic_price = price

    # ==========================================================================
    # Computed Fields - Occupancy & Revenue
    # ==========================================================================

    @api.depends('lease_ids', 'lease_ids.status', 'lease_ids.rent_amount',
                 'unit_ids', 'unit_ids.lease_ids')
    def _compute_total_revenue(self):
        """Compute total revenue from all leases"""
        for record in self:
            total = 0.0
            if record.lease_ids:
                active_leases = record.lease_ids.filtered(
                    lambda l: l.status in ['active', 'signed']
                )
                # Sum monthly rent for active leases
                for lease in active_leases:
                    total += lease.rent_amount or 0.0

                    # Add any lease charges
                    if lease.lease_fees and lease.lease_fees > 0:
                        total += lease.lease_fees

            # For multi-unit, sum all unit revenues
            if record.unit_ids:
                for unit in record.unit_ids:
                    if unit.lease_ids:
                        unit_total = sum(
                            l.rent_amount or 0.0
                            for l in unit.lease_ids
                            if l.status in ['active', 'signed']
                        )
                        total += unit_total

            record.total_revenue = total

    @api.depends('unit_ids', 'unit_ids.lease_ids', 'lease_ids')
    def _compute_active_lease(self):
        """Find current active lease"""
        for record in self:
            active_lease = False
            # Check property-level leases
            for lease in record.lease_ids:
                if lease.status == 'active':
                    active_lease = lease
                    break

            # If not found, check unit-level leases
            if not active_lease and record.unit_ids:
                for unit in record.unit_ids:
                    if unit.lease_ids.filtered(lambda l: l.status == 'active'):
                        active_lease = unit.lease_ids.filtered(
                            lambda l: l.status == 'active'
                        )[0]
                        break

            record.active_lease_id = active_lease

    @api.depends('iot_device_ids')
    def _compute_iot_enabled(self):
        """Check if property has IoT devices"""
        for record in self:
            record.iot_enabled = bool(record.iot_device_ids)

    @api.depends('website_published', 'property_code', 'name')
    def _compute_website_url(self):
        """Generate website URL for property"""
        for record in self:
            if record.website_published:
                record.website_url = f"/property/{record.property_code}"
            else:
                record.website_url = False

    # ==========================================================================
    # Computed Fields - Analytics
    # ==========================================================================

    occupancy_rate = fields.Float(
        string='Occupancy Rate (%)',
        compute='_compute_occupancy_rate',
        store=True,
        help='Percentage of units/space occupied'
    )

    next_maintenance_date = fields.Date(
        string='Next Maintenance Due',
        compute='_compute_next_maintenance',
        store=True,
        help='Scheduled date for next maintenance'
    )

    @api.depends('unit_ids', 'unit_ids.lease_ids', 'lease_ids')
    def _compute_occupancy_rate(self):
        """Calculate occupancy rate based on active leases"""
        for record in self:
            total_units = len(record.unit_ids) if record.unit_ids else 1
            occupied_units = 0

            # Check property-level lease
            if record.lease_ids.filtered(lambda l: l.status == 'active'):
                occupied_units += 1

            # Check unit-level leases
            for unit in record.unit_ids:
                if unit.lease_ids.filtered(lambda l: l.status == 'active'):
                    occupied_units += 1

            if total_units > 0:
                record.occupancy_rate = (occupied_units / total_units) * 100
            else:
                record.occupancy_rate = 100.0 if occupied_units > 0 else 0.0

    @api.depends('maintenance_request_ids', 'maintenance_request_ids.status',
                 'maintenance_request_ids.scheduled_date')
    def _compute_next_maintenance(self):
        """Find next scheduled maintenance date"""
        for record in self:
            upcoming = record.maintenance_request_ids.filtered(
                lambda m: m.status in ['pending', 'scheduled'] and m.scheduled_date
            )
            if upcoming:
                record.next_maintenance_date = min(upcoming.mapped('scheduled_date'))
            else:
                record.next_maintenance_date = False

    # ==========================================================================
    # SQL Constraints
    # ==========================================================================

    _sql_constraints = [
        ('property_code_unique', 'unique(property_code)',
         'Property code must be unique!'),
        ('check_area_positive', 'CHECK(area_total >= 0)',
         'Total area cannot be negative'),
        ('check_price_positive', 'CHECK(base_price >= 0)',
         'Price cannot be negative'),
        ('check_bedrooms_positive', 'CHECK(bedrooms >= 0)',
         'Bedrooms cannot be negative'),
        ('check_bathrooms_positive', 'CHECK(bathrooms >= 0)',
         'Bathrooms cannot be negative'),
        ('check_year_built_valid', 'CHECK(year_built <= EXTRACT(YEAR FROM CURRENT_DATE) + 1)',
         'Year built cannot be in the future'),
        ('check_rental_price_positive', 'CHECK(rental_price >= 0)',
         'Rental price cannot be negative'),
    ]

    # ==========================================================================
    # Constraints and Validation
    # ==========================================================================

    @api.constrains('base_price', 'minimum_price')
    def _check_price_constraints(self):
        """Ensure minimum price doesn't exceed base price"""
        for record in self:
            if record.minimum_price and record.base_price:
                if record.minimum_price > record.base_price:
                    raise ValidationError(
                        _("Minimum price cannot exceed base price.")
                    )

    @api.constrains('year_built')
    def _check_year_built(self):
        """Validate year built is reasonable"""
        current_year = datetime.now().year
        for record in self:
            if record.year_built and record.year_built > current_year + 1:
                raise ValidationError(
                    _("Year built cannot be more than one year in the future.")
                )
            if record.year_built and record.year_built < 1800:
                raise ValidationError(
                    _("Year built seems too old. Please verify the year.")
                )

    @api.constrains('bedrooms', 'bathrooms')
    def _check_room_count(self):
        """Validate room counts are reasonable"""
        for record in self:
            if record.bedrooms and record.bedrooms > 50:
                raise ValidationError(
                    _("Bedroom count seems too high. Please verify the number.")
                )
            if record.bathrooms and record.bathrooms > 30:
                raise ValidationError(
                    _("Bathroom count seems too high. Please verify the number.")
                )

    @api.constrains('area_living', 'area_total')
    def _check_areas(self):
        """Ensure living area doesn't exceed total area"""
        for record in self:
            if record.area_living and record.area_total:
                if record.area_living > record.area_total:
                    raise ValidationError(
                        _("Living area cannot exceed total area.")
                    )

    # ==========================================================================
    # Business Methods
    # ==========================================================================

    @api.model
    def create(self, vals):
        """Override create to set default partner if not provided"""
        if not vals.get('partner_id'):
            # Create partner for property address
            partner_vals = self._prepare_partner_vals(vals)
            if partner_vals:
                partner = self.env['res.partner'].create(partner_vals)
                vals['partner_id'] = partner.id

        return super(PropertyProperty, self).create(vals)

    def write(self, vals):
        """Override write to handle partner updates"""
        result = super(PropertyProperty, self).write(vals)

        # Update partner if address changed
        if any(field in vals for field in ['street', 'street2', 'city',
                                           'state_id', 'country_id', 'zip']):
            for record in self:
                if record.partner_id:
                    partner_vals = self._prepare_partner_vals(vals)
                    if partner_vals:
                        record.partner_id.write(partner_vals)

        return result

    def _prepare_partner_vals(self, vals):
        """Prepare partner values from property vals"""
        partner_vals = {}
        field_mapping = {
            'street': 'street',
            'street2': 'street2',
            'city': 'city',
            'state_id': 'state_id',
            'country_id': 'country_id',
            'zip': 'zip',
        }

        # Map property fields to partner fields
        for prop_field, partner_field in field_mapping.items():
            if prop_field in vals and vals[prop_field]:
                partner_vals[partner_field] = vals[prop_field]

        # Set partner name from property name
        if vals.get('name'):
            partner_vals['name'] = f"Property: {vals['name']}"

        # Make partner a company
        partner_vals['is_company'] = True

        # Add tags for identification
        if not partner_vals.get('category_id'):
            category = self.env.ref('base.res_partner_category_0', raise_if_not_found=False)
            if category:
                partner_vals['category_id'] = [(4, category.id)]

        return partner_vals

    def action_publish_website(self):
        """Publish property on website"""
        for record in self:
            record.website_published = True
            record.status = 'listed'
            record.message_post(
                body=_("Property published on website."),
                message_type='notification'
            )

    def action_unpublish_website(self):
        """Unpublish property from website"""
        for record in self:
            record.website_published = False
            record.message_post(
                body=_("Property unpublished from website."),
                message_type='notification'
            )

    def action_mark_sold(self):
        """Mark property as sold"""
        for record in self:
            if record.status == 'sold':
                raise UserError(_("This property is already marked as sold."))

            # Check for active leases
            if record.active_lease_id:
                raise UserError(
                    _("Cannot mark as sold while there's an active lease. "
                      "Please terminate the lease first.")
                )

            record.status = 'sold'
            record.website_published = False
            record.message_post(
                body=_("Property marked as sold."),
                message_type='notification'
            )

    def action_mark_leased(self):
        """Mark property as leased"""
        for record in self:
            if record.status == 'leased':
                raise UserError(_("This property is already leased."))

            if not record.active_lease_id:
                raise UserError(
                    _("Cannot mark as leased without an active lease. "
                      "Please create a lease first.")
                )

            record.status = 'leased'
            record.website_published = False
            record.message_post(
                body=_("Property marked as leased."),
                message_type='notification'
            )

    def action_create_lease(self):
        """Create a new lease from property"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Create Lease'),
            'res_model': 'property.lease.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_property_id': self.id,
                'default_tenant_id': self.env.user.partner_id.id,
            }
        }

    def action_schedule_viewing(self):
        """Schedule a viewing for this property"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Schedule Viewing'),
            'res_model': 'property.viewing',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_property_id': self.id,
                'default_scheduled_time': fields.Datetime.now() + timedelta(days=2),
            }
        }

    def action_show_leases(self):
        """Show all leases for this property"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Leases'),
            'res_model': 'property.lease',
            'view_mode': 'tree,form',
            'domain': [('property_id', '=', self.id)],
            'context': {'default_property_id': self.id},
        }

    def action_show_maintenance(self):
        """Show maintenance requests for this property"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Maintenance Requests'),
            'res_model': 'property.maintenance.request',
            'view_mode': 'tree,form',
            'domain': [('property_id', '=', self.id)],
            'context': {'default_property_id': self.id},
        }

    def action_archive_property(self):
        """Archive the property"""
        for record in self:
            if record.status in ['active', 'listed']:
                raise UserError(
                    _("Cannot archive an active or listed property. "
                      "Please mark it as sold or leased first.")
                )
            record.active = False
            record.website_published = False
            record.status = 'archived'
            record.message_post(
                body=_("Property archived."),
                message_type='notification'
            )

    def action_restore_property(self):
        """Restore archived property"""
        for record in self:
            record.active = True
            record.status = 'listed'
            record.message_post(
                body=_("Property restored from archive."),
                message_type='notification'
            )

    def _get_leaseable_units(self):
        """Get all leaseable units for this property"""
        self.ensure_one()
        if self.type == 'multi_unit':
            return self.unit_ids.filtered(lambda u: u.status == 'vacant')
        return self

    def _get_smart_stats(self):
        """Get IoT and smart feature statistics"""
        self.ensure_one()
        stats = {
            'total_iot_devices': len(self.iot_device_ids),
            'online_devices': len(self.iot_device_ids.filtered(lambda d: d.status == 'online')),
            'offline_devices': len(self.iot_device_ids.filtered(lambda d: d.status == 'offline')),
            'maintenance_alerts': len(self.iot_device_ids.filtered(lambda d: d.has_alert)),
        }
        return stats

    # ==========================================================================
    # Override Methods
    # ==========================================================================

    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        """Override for custom view handling"""
        return super(PropertyProperty, self)._get_view(view_id, view_type, **options)

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        """Enhanced name search with property code"""
        args = args or []
        domain = []
        if name:
            domain = ['|', ('name', operator, name),
                      ('property_code', operator, name)]
        return super(PropertyProperty, self).name_search(
            name, args + domain, operator=operator, limit=limit
        )

    def name_get(self):
        """Custom name_get for better display in many2one fields"""
        result = []
        for record in self:
            name = record.display_name
            result.append((record.id, name))
        return result
