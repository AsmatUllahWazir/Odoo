from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class ShippingCarrierService(models.Model):
    """Carrier Service Levels"""
    _name = 'shipping.carrier.service'
    _description = 'Carrier Service Level'
    _order = 'provider_id, sequence'
    _rec_name = 'name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        string='Service Name',
        required=True,
        tracking=True,
        translate=True,
    )
    code = fields.Char(
        string='Service Code',
        required=True,
        tracking=True,
    )
    description = fields.Text(
        string='Description',
        translate=True,
    )
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=True, tracking=True)

    provider_id = fields.Many2one(
        'shipping.carrier.provider',
        string='Carrier Provider',
        required=True,
        ondelete='cascade',
        tracking=True,
    )

    service_type = fields.Selection([
        ('same_day', 'Same Day'),
        ('next_day', 'Next Day'),
        ('expedited', 'Expedited'),
        ('standard', 'Standard'),
        ('economy', 'Economy'),
        ('ground', 'Ground'),
        ('air', 'Air'),
        ('freight', 'Freight'),
        ('international', 'International'),
        ('domestic', 'Domestic'),
    ], string='Service Type', default='standard', tracking=True)

    delivery_time = fields.Char(string='Delivery Time')
    min_delivery_days = fields.Integer(string='Min Delivery Days')
    max_delivery_days = fields.Integer(string='Max Delivery Days')

    # Pricing
    base_rate = fields.Monetary(
        string='Base Rate',
        currency_field='currency_id',
        tracking=True,
    )
    fuel_surcharge_percent = fields.Float(
        string='Fuel Surcharge %',
        default=0.0,
    )
    residential_surcharge = fields.Monetary(
        string='Residential Surcharge',
        currency_field='currency_id',
    )
    saturday_surcharge = fields.Monetary(
        string='Saturday Surcharge',
        currency_field='currency_id',
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
    )

    # Restrictions
    max_weight = fields.Float(
        string='Max Weight (kg)',
        digits='Stock Weight',
        help='Maximum weight allowed in kg'
    )
    min_weight = fields.Float(
        string='Min Weight (kg)',
        digits='Stock Weight',
        help='Minimum weight allowed in kg'
    )
    max_length = fields.Float(
        string='Max Length (cm)',
        digits='Stock Dimension',
    )
    max_width = fields.Float(
        string='Max Width (cm)',
        digits='Stock Dimension',
    )
    max_height = fields.Float(
        string='Max Height (cm)',
        digits='Stock Dimension',
    )
    max_volume = fields.Float(
        string='Max Volume (cm³)',
        help='Maximum volume in cubic centimeters'
    )

    # Countries
    country_ids = fields.Many2many(
        'res.country',
        'shipping_carrier_service_country_rel',
        'service_id',
        'country_id',
        string='Available Countries',
        help='Countries where this service is available'
    )
    country_group_ids = fields.Many2many(
        'res.country.group',
        'shipping_carrier_service_country_group_rel',
        'service_id',
        'country_group_id',
        string='Country Groups',
        help='Country groups where this service is available'
    )
    excluded_country_ids = fields.Many2many(
        'res.country',
        'shipping_carrier_service_excluded_country_rel',
        'service_id',
        'excluded_country_id',
        string='Excluded Countries',
        help='Countries where this service is NOT available'
    )

    # Features
    is_international = fields.Boolean(
        string='International Service',
        tracking=True,
        help='This is an international shipping service'
    )
    requires_customs = fields.Boolean(
        string='Requires Customs Declaration',
        help='This service requires customs documentation'
    )
    supports_cod = fields.Boolean(
        string='Supports COD',
        help='Supports Cash on Delivery'
    )
    supports_insurance = fields.Boolean(
        string='Supports Insurance',
        help='Supports shipping insurance'
    )
    requires_signature = fields.Boolean(
        string='Requires Signature',
        help='Signature required on delivery'
    )
    supports_saturday = fields.Boolean(
        string='Supports Saturday Delivery',
        help='Can deliver on Saturdays'
    )
    supports_residential = fields.Boolean(
        string='Supports Residential Delivery',
        default=True,
        help='Can deliver to residential addresses'
    )

    # API Reference
    api_service_code = fields.Char(
        string='API Service Code',
        help='Service code used in API calls'
    )
    api_service_name = fields.Char(
        string='API Service Name',
        help='Service name used in API calls'
    )

    # Additional
    notes = fields.Text(string='Notes')

    # Company
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
    )

    # Statistics
    usage_count = fields.Integer(
        string='Times Used',
        compute='_compute_usage_count',
        store=False,
        default=0,
    )

    _sql_constraints = [
        ('unique_service_code', 'unique(provider_id, code)',
         'Service code must be unique per carrier!'),
        ('check_weight_positive', 'CHECK(max_weight >= 0 AND min_weight >= 0)',
         'Weight values cannot be negative.'),
    ]

    def _compute_usage_count(self):
        """Compute usage count from shipment records"""
        for service in self:
            count = self.env['shipping.shipment'].search_count([
                ('carrier_service_id', '=', service.id)
            ])
            service.usage_count = count

    @api.onchange('provider_id')
    def _onchange_provider_id(self):
        if self.provider_id:
            self.currency_id = self.provider_id.currency_id.id
            self.company_id = self.provider_id.company_id.id

    @api.constrains('min_weight', 'max_weight')
    def _check_weight_range(self):
        for service in self:
            if service.min_weight > service.max_weight:
                raise ValidationError(_('Minimum weight cannot be greater than maximum weight.'))

    @api.constrains('min_delivery_days', 'max_delivery_days')
    def _check_delivery_days(self):
        for service in self:
            if service.min_delivery_days and service.max_delivery_days:
                if service.min_delivery_days > service.max_delivery_days:
                    raise ValidationError(_('Minimum delivery days cannot be greater than maximum delivery days.'))

    def name_get(self):
        result = []
        for record in self:
            name = record.name
            if record.service_type:
                name = f"{name} ({record.service_type})"
            if record.provider_id:
                name = f"[{record.provider_id.code}] {name}"
            result.append((record.id, name))
        return result

    def action_view_shipments(self):
        """View shipments using this service"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Shipments'),
            'res_model': 'shipping.shipment',
            'view_mode': 'tree,form',
            'domain': [('carrier_service_id', '=', self.id)],
        }

    def toggle_active(self):
        """Toggle active status"""
        for record in self:
            record.active = not record.active
