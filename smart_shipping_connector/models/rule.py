from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import logging
import json

_logger = logging.getLogger(__name__)


class ShippingRule(models.Model):
    """Intelligent Shipping Rule - Complete Implementation"""
    _name = 'shipping.rule'
    _description = 'Shipping Rule'
    _order = 'priority, name'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'display_name'

    # Basic Information
    name = fields.Char(
        string='Rule Name',
        required=True,
        tracking=True,
        translate=True,
    )
    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True,
    )
    active = fields.Boolean(
        string='Active',
        default=True,
        tracking=True,
    )
    priority = fields.Integer(
        string='Priority',
        default=10,
        help='Lower number = higher priority. First matching rule wins.'
    )
    description = fields.Text(string='Description', translate=True)

    # Rule Type
    rule_type = fields.Selection([
        ('weight', 'Weight Based'),
        ('value', 'Value Based'),
        ('destination', 'Destination Based'),
        ('international', 'International/ Domestic'),
        ('product', 'Product Based'),
        ('combined', 'Combined Conditions'),
    ], string='Rule Type', default='combined', required=True)

    # ==================== CONDITIONS ====================

    # Weight Conditions
    condition_weight_min = fields.Float(
        string='Min Weight (kg)',
        default=0.0,
        digits='Stock Weight',
        help='Minimum weight in kg'
    )
    condition_weight_max = fields.Float(
        string='Max Weight (kg)',
        default=999999.0,
        digits='Stock Weight',
        help='Maximum weight in kg'
    )
    condition_weight_inclusive = fields.Boolean(
        string='Weight Range Inclusive',
        default=True,
        help='Include the min and max values in the range'
    )

    # Value Conditions
    condition_value_min = fields.Monetary(
        string='Min Declared Value',
        currency_field='currency_id',
        help='Minimum declared value'
    )
    condition_value_max = fields.Monetary(
        string='Max Declared Value',
        currency_field='currency_id',
        help='Maximum declared value'
    )

    # Destination Conditions
    condition_country_ids = fields.Many2many(
        'res.country',
        string='Country Conditions',
        help='Apply rule only for these countries'
    )
    condition_country_group_ids = fields.Many2many(
        'res.country.group',
        string='Country Group Conditions',
        help='Apply rule for these country groups'
    )
    condition_state_ids = fields.Many2many(
        'res.country.state',
        string='State/Province Conditions',
        help='Apply rule only for these states/provinces'
    )
    condition_zip_prefix = fields.Char(
        string='ZIP Code Prefix',
        help='Apply rule for ZIP codes starting with this prefix'
    )
    condition_zip_range_start = fields.Char(
        string='ZIP Range Start',
        help='Starting ZIP code for range'
    )
    condition_zip_range_end = fields.Char(
        string='ZIP Range End',
        help='Ending ZIP code for range'
    )

    # International/Domestic
    condition_international = fields.Boolean(
        string='International Only',
        help='Apply only to international shipments'
    )
    condition_domestic = fields.Boolean(
        string='Domestic Only',
        help='Apply only to domestic shipments'
    )

    # Product Conditions
    condition_product_ids = fields.Many2many(
        'product.product',
        string='Product Conditions',
        help='Apply rule only for these products'
    )
    condition_product_category_ids = fields.Many2many(
        'product.category',
        string='Product Categories',
        help='Apply rule only for these product categories'
    )
    condition_product_tags = fields.Many2many(
        'product.tag',
        string='Product Tags',
        help='Apply rule only for products with these tags'
    )

    # Package Conditions
    condition_min_packages = fields.Integer(
        string='Min Packages',
        default=1,
        help='Minimum number of packages'
    )
    condition_max_packages = fields.Integer(
        string='Max Packages',
        default=999,
        help='Maximum number of packages'
    )

    # Time Conditions
    condition_days_of_week = fields.Selection([
        ('monday', 'Monday'),
        ('tuesday', 'Tuesday'),
        ('wednesday', 'Wednesday'),
        ('thursday', 'Thursday'),
        ('friday', 'Friday'),
        ('saturday', 'Saturday'),
        ('sunday', 'Sunday'),
        ('all', 'All Days'),
    ], string='Days of Week', default='all')
    condition_time_start = fields.Float(
        string='Time Start',
        help='Start time in 24-hour format (e.g., 9.00 for 9:00 AM)'
    )
    condition_time_end = fields.Float(
        string='Time End',
        help='End time in 24-hour format (e.g., 17.00 for 5:00 PM)'
    )

    # ==================== ACTIONS ====================

    # Carrier Selection
    action_carrier_provider_id = fields.Many2one(
        'shipping.carrier.provider',
        string='Select Carrier',
        required=True,
        help='Carrier to use when this rule matches'
    )
    action_service_type = fields.Char(
        string='Service Type',
        help='Specific service type to use'
    )
    action_carrier_service_id = fields.Many2one(
        'shipping.carrier.service',
        string='Carrier Service',
        domain="[('provider_id', '=', action_carrier_provider_id)]",
        help='Specific carrier service to use'
    )
    action_account_id = fields.Many2one(
        'shipping.carrier.account',
        string='Select Account',
        domain="[('provider_id', '=', action_carrier_provider_id)]",
        help='Carrier account to use'
    )

    # Cost Overrides
    action_override_cost = fields.Monetary(
        string='Override Cost',
        currency_field='currency_id',
        help='Override the shipping cost with this amount'
    )
    action_cost_multiplier = fields.Float(
        string='Cost Multiplier',
        default=1.0,
        help='Multiplier to apply to the base cost'
    )
    action_cost_adjustment = fields.Monetary(
        string='Cost Adjustment',
        currency_field='currency_id',
        help='Adjustment amount to add to or subtract from cost'
    )

    # Delivery Overrides
    action_delivery_days = fields.Integer(
        string='Override Delivery Days',
        help='Override estimated delivery days'
    )
    action_delivery_date = fields.Datetime(
        string='Override Delivery Date',
        help='Override estimated delivery date'
    )

    # Additional Actions
    action_require_signature = fields.Boolean(
        string='Require Signature',
        help='Require signature on delivery'
    )
    action_insurance_required = fields.Boolean(
        string='Insurance Required',
        help='Require insurance'
    )
    action_insurance_amount = fields.Monetary(
        string='Insurance Amount',
        currency_field='currency_id',
        help='Amount of insurance required'
    )
    action_cod = fields.Boolean(
        string='Cash on Delivery',
        help='Enable COD for this rule'
    )
    action_cod_amount = fields.Monetary(
        string='COD Amount',
        currency_field='currency_id',
        help='COD amount to collect'
    )

    # Discounts/Promotions
    action_discount_percent = fields.Float(
        string='Discount %',
        default=0.0,
        help='Discount percentage to apply'
    )
    action_promotion_code = fields.Char(
        string='Promotion Code',
        help='Promotion code to apply'
    )

    # Email/Notification
    action_notify_customer = fields.Boolean(
        string='Notify Customer',
        default=True,
        help='Send notification to customer'
    )
    action_email_template_id = fields.Many2one(
        'mail.template',
        string='Email Template',
        domain="[('model', '=', 'shipping.shipment')]",
        help='Email template to use for notification'
    )

    # Currency
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
    )

    # Company
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
    )

    # Statistical Tracking
    match_count = fields.Integer(
        string='Times Matched',
        default=0,
        help='Number of times this rule has matched'
    )
    last_match_date = fields.Datetime(
        string='Last Match Date',
        help='Date this rule was last matched'
    )

    _sql_constraints = [
        ('check_weight_range', 'CHECK(condition_weight_min <= condition_weight_max)',
         'Minimum weight must be less than or equal to maximum weight.'),
        ('check_value_range', 'CHECK(condition_value_min <= condition_value_max)',
         'Minimum value must be less than or equal to maximum value.'),
    ]

    @api.depends('name', 'priority')
    def _compute_display_name(self):
        for rule in self:
            self.display_name = f"{rule.name} (Priority: {rule.priority})"

    @api.constrains('action_discount_percent')
    def _check_discount(self):
        for rule in self:
            if rule.action_discount_percent < 0 or rule.action_discount_percent > 100:
                raise ValidationError(_('Discount percentage must be between 0 and 100.'))

    def apply_rule(self, shipment_data):
        """Apply this rule to shipment data and return carrier if matches"""
        self.ensure_one()

        # Check all conditions
        if not self._check_weight_condition(shipment_data):
            return False
        if not self._check_value_condition(shipment_data):
            return False
        if not self._check_destination_condition(shipment_data):
            return False
        if not self._check_international_condition(shipment_data):
            return False
        if not self._check_product_condition(shipment_data):
            return False
        if not self._check_package_condition(shipment_data):
            return False
        if not self._check_time_condition():
            return False

        # If all conditions match, increment match count
        self.match_count += 1
        self.last_match_date = fields.Datetime.now()

        # Build action result
        result = {
            'carrier_provider_id': self.action_carrier_provider_id.id,
            'service_type': self.action_service_type,
            'carrier_service_id': self.action_carrier_service_id.id if self.action_carrier_service_id else None,
            'account_id': self.action_account_id.id if self.action_account_id else None,
            'override_cost': self.action_override_cost,
            'cost_multiplier': self.action_cost_multiplier,
            'cost_adjustment': self.action_cost_adjustment,
            'delivery_days': self.action_delivery_days,
            'delivery_date': self.action_delivery_date,
            'require_signature': self.action_require_signature,
            'insurance_required': self.action_insurance_required,
            'insurance_amount': self.action_insurance_amount,
            'cod': self.action_cod,
            'cod_amount': self.action_cod_amount,
            'discount_percent': self.action_discount_percent,
            'notify_customer': self.action_notify_customer,
        }

        return result

    def _check_weight_condition(self, data):
        """Check weight condition"""
        weight = data.get('weight', 0)
        if self.condition_weight_inclusive:
            return self.condition_weight_min <= weight <= self.condition_weight_max
        else:
            return self.condition_weight_min < weight < self.condition_weight_max

    def _check_value_condition(self, data):
        """Check value condition"""
        value = data.get('declared_value', 0)
        if self.condition_value_min and self.condition_value_max:
            return self.condition_value_min <= value <= self.condition_value_max
        elif self.condition_value_min:
            return value >= self.condition_value_min
        elif self.condition_value_max:
            return value <= self.condition_value_max
        return True

    def _check_destination_condition(self, data):
        """Check destination conditions"""
        country_code = data.get('country_code')

        # Check country list
        if self.condition_country_ids:
            if not country_code:
                return False
            matching_countries = self.condition_country_ids.filtered(
                lambda c: c.code == country_code
            )
            if not matching_countries:
                return False

        # Check country groups
        if self.condition_country_group_ids:
            if not country_code:
                return False
            for group in self.condition_country_group_ids:
                if country_code in group.country_ids.mapped('code'):
                    return True
            return False

        # Check ZIP prefix
        if self.condition_zip_prefix:
            zip_code = data.get('zip_code', '')
            if not zip_code.startswith(self.condition_zip_prefix):
                return False

        return True

    def _check_international_condition(self, data):
        """Check international/domestic condition"""
        is_international = data.get('is_international', False)

        if self.condition_international and not is_international:
            return False
        if self.condition_domestic and is_international:
            return False

        return True

    def _check_product_condition(self, data):
        """Check product conditions"""
        product_ids = data.get('product_ids', [])

        if self.condition_product_ids:
            if not product_ids:
                return False
            matching_products = self.condition_product_ids.filtered(
                lambda p: p.id in product_ids
            )
            if not matching_products:
                return False

        return True

    def _check_package_condition(self, data):
        """Check package conditions"""
        packages = data.get('total_packages', 0)
        return self.condition_min_packages <= packages <= self.condition_max_packages

    def _check_time_condition(self):
        """Check time condition"""
        if self.condition_days_of_week == 'all':
            return True

        from datetime import datetime
        now = datetime.now()
        day_name = now.strftime('%A').lower()

        if day_name != self.condition_days_of_week:
            return False

        if self.condition_time_start and self.condition_time_end:
            current_hour = now.hour + now.minute / 60.0
            return self.condition_time_start <= current_hour <= self.condition_time_end

        return True

    def action_test_rule(self):
        """Test this rule with sample data"""
        self.ensure_one()

        # Get sample shipment data
        sample_data = {
            'weight': 5.0,
            'declared_value': 100.0,
            'country_code': 'US',
            'is_international': False,
            'zip_code': '90210',
            'total_packages': 1,
        }

        result = self.apply_rule(sample_data)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Rule Test Results'),
                'message': _('Rule matches!' if result else 'Rule does not match.'),
                'type': 'success' if result else 'warning',
                'sticky': False,
            }
        }

    def action_view_matches(self):
        """View shipments that matched this rule"""
        self.ensure_one()
        # TODO: Implement matching history
        return {
            'type': 'ir.actions.act_window',
            'name': _('Rule Matches'),
            'res_model': 'shipping.shipment',
            'view_mode': 'tree,form',
            'domain': [('rule_id', '=', self.id)],
        }
    