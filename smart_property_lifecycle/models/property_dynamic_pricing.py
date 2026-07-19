# -*- coding: utf-8 -*-
"""
Property Dynamic Pricing Model - Manage pricing rules and algorithms
"""

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)


class PropertyDynamicPricingRule(models.Model):
    """
    Dynamic Pricing Rules - Configure pricing algorithms
    """
    _name = 'property.dynamic.pricing.rule'
    _description = 'Dynamic Pricing Rule'
    _order = 'priority'

    name = fields.Char(
        string='Rule Name',
        required=True
    )

    active = fields.Boolean(
        string='Active',
        default=True
    )

    priority = fields.Integer(
        string='Priority',
        default=10,
        help='Lower number = higher priority'
    )

    property_type = fields.Selection([
        ('all', 'All Types'),
        ('residential', 'Residential'),
        ('commercial', 'Commercial'),
        ('industrial', 'Industrial'),
        ('land', 'Land'),
        ('mixed_use', 'Mixed Use'),
        ('condo', 'Condo'),
        ('multi_unit', 'Multi-Unit'),
    ], string='Property Type', default='all')

    rule_type = fields.Selection([
        ('seasonal', 'Seasonal Adjustment'),
        ('market', 'Market Based'),
        ('occupancy', 'Occupancy Based'),
        ('demand', 'Demand Based'),
        ('maintenance', 'Maintenance Based'),
        ('custom', 'Custom Formula'),
    ], string='Rule Type', required=True)

    # ==========================================================================
    # Rule Parameters
    # ==========================================================================

    adjustment_type = fields.Selection([
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount'),
    ], string='Adjustment Type', default='percentage')

    adjustment_value = fields.Float(
        string='Adjustment Value',
        help='Positive for increase, negative for decrease'
    )

    min_adjustment = fields.Float(
        string='Minimum Adjustment',
        help='Minimum adjustment value (if percentage, this is %)'
    )

    max_adjustment = fields.Float(
        string='Maximum Adjustment',
        help='Maximum adjustment value (if percentage, this is %)'
    )

    # ==========================================================================
    # Conditions
    # ==========================================================================

    apply_from_month = fields.Integer(
        string='Apply From Month',
        help='1-12 for seasonal rules'
    )

    apply_to_month = fields.Integer(
        string='Apply To Month',
        help='1-12 for seasonal rules'
    )

    occupancy_threshold = fields.Float(
        string='Occupancy Threshold (%)',
        help='Apply when occupancy is above/below this value'
    )

    days_on_market = fields.Integer(
        string='Days on Market',
        help='Apply after property has been listed this many days'
    )

    demand_factor = fields.Float(
        string='Demand Factor',
        help='1.0 = neutral, >1 = high demand, <1 = low demand'
    )

    competitor_price_ratio = fields.Float(
        string='Competitor Price Ratio',
        help='Adjust based on competitor pricing'
    )

    maintenance_factor = fields.Float(
        string='Maintenance Factor',
        help='Adjust based on maintenance history'
    )

    custom_formula = fields.Text(
        string='Custom Formula',
        help='Python formula for custom rules (uses dynamic_price variable)'
    )

    # ==========================================================================
    # Application
    # ==========================================================================

    apply_to_field = fields.Selection([
        ('base_price', 'Base Price'),
        ('rental_price', 'Rental Price'),
        ('both', 'Both'),
    ], string='Apply To', default='both')

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company
    )

    # ==========================================================================
    # Methods
    # ==========================================================================

    def apply_rule(self, property_record):
        """Apply this pricing rule to a property"""
        self.ensure_one()

        if not self._check_conditions(property_record):
            return 0.0

        adjustment = self._calculate_adjustment(property_record)
        return adjustment

    def _check_conditions(self, property_record):
        """Check if property meets rule conditions"""
        # Property type check
        if self.property_type != 'all' and property_record.type != self.property_type:
            return False

        # Seasonal check
        if self.rule_type == 'seasonal':
            current_month = datetime.now().month
            if self.apply_from_month and self.apply_to_month:
                if self.apply_from_month <= self.apply_to_month:
                    if not (self.apply_from_month <= current_month <= self.apply_to_month):
                        return False
                else:
                    # Cross-year (e.g., Nov to Feb)
                    if not (current_month >= self.apply_from_month or
                            current_month <= self.apply_to_month):
                        return False

        # Days on market check
        if self.days_on_market > 0:
            create_date = property_record.create_date
            if create_date:
                days = (datetime.now() - create_date).days
                if days < self.days_on_market:
                    return False

        # Occupancy check (for rental properties)
        if self.occupancy_threshold > 0 and property_record.occupancy_rate:
            if property_record.occupancy_rate < self.occupancy_threshold:
                return False

        return True

    def _calculate_adjustment(self, property_record):
        """Calculate adjustment value"""
        if self.rule_type == 'custom' and self.custom_formula:
            try:
                # Execute custom formula
                local_dict = {
                    'dynamic_price': property_record.dynamic_price,
                    'base_price': property_record.base_price,
                    'occupancy': property_record.occupancy_rate,
                    'days_on_market': (datetime.now() - property_record.create_date).days,
                }
                result = eval(self.custom_formula, {}, local_dict)
                return float(result)
            except Exception as e:
                _logger.error(f"Error in custom pricing formula: {e}")
                return 0.0

        # Standard adjustment
        if self.adjustment_type == 'percentage':
            base_value = property_record.base_price if self.apply_to_field in ['base_price',
                                                                               'both'] else property_record.rental_price
            adjustment = base_value * (self.adjustment_value / 100.0)
        else:
            adjustment = self.adjustment_value

        # Apply min/max limits
        if self.min_adjustment:
            if self.adjustment_type == 'percentage':
                min_value = property_record.base_price * (self.min_adjustment / 100.0)
                adjustment = max(adjustment, min_value)
            else:
                adjustment = max(adjustment, self.min_adjustment)

        if self.max_adjustment:
            if self.adjustment_type == 'percentage':
                max_value = property_record.base_price * (self.max_adjustment / 100.0)
                adjustment = min(adjustment, max_value)
            else:
                adjustment = min(adjustment, self.max_adjustment)

        return adjustment

    # ==========================================================================
    # Constraint
    # ==========================================================================

    @api.constrains('adjustment_value')
    def _check_adjustment_value(self):
        """Validate adjustment value"""
        for record in self:
            if record.adjustment_value == 0:
                raise ValidationError(
                    _("Adjustment value must be non-zero.")
                )

    @api.constrains('apply_from_month', 'apply_to_month')
    def _check_seasonal_months(self):
        """Validate seasonal month range"""
        for record in self:
            if record.rule_type == 'seasonal':
                if not (1 <= record.apply_from_month <= 12 and
                        1 <= record.apply_to_month <= 12):
                    raise ValidationError(
                        _("Months must be between 1 and 12.")
                    )
