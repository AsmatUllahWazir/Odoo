from odoo import api, fields, models, _
import logging
import json

_logger = logging.getLogger(__name__)


class ShippingRuleCondition(models.Model):
    """Individual Rule Conditions for Complex Rules"""
    _name = 'shipping.rule.condition'
    _description = 'Shipping Rule Condition'
    _order = 'rule_id, sequence'
    _rec_name = 'display_name'

    rule_id = fields.Many2one(
        'shipping.rule',
        string='Rule',
        required=True,
        ondelete='cascade',
    )

    sequence = fields.Integer(string='Sequence', default=10)
    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True,
    )

    condition_type = fields.Selection([
        ('weight_min', 'Minimum Weight'),
        ('weight_max', 'Maximum Weight'),
        ('value_min', 'Minimum Value'),
        ('value_max', 'Maximum Value'),
        ('country', 'Country'),
        ('country_group', 'Country Group'),
        ('state', 'State/Province'),
        ('zip_prefix', 'ZIP Prefix'),
        ('international', 'International'),
        ('domestic', 'Domestic'),
        ('product', 'Product'),
        ('product_category', 'Product Category'),
        ('product_tag', 'Product Tag'),
        ('min_packages', 'Minimum Packages'),
        ('max_packages', 'Maximum Packages'),
        ('day_of_week', 'Day of Week'),
        ('time_range', 'Time Range'),
        ('custom', 'Custom Condition'),
    ], string='Condition Type', required=True)

    # Value Fields (different types based on condition_type)
    value_float = fields.Float(string='Value (Float)')
    value_int = fields.Integer(string='Value (Integer)')
    value_char = fields.Char(string='Value (Text)')
    value_m2o = fields.Many2oneReference(
        string='Value (Reference)',
        model_field='reference_model',
    )
    reference_model = fields.Char(string='Reference Model')

    # For Many2many values
    value_m2m_ids = fields.Many2many(
        'res.country',
        string='Value (Countries)',
    )

    # Operators
    operator = fields.Selection([
        ('eq', 'Equals'),
        ('ne', 'Not Equals'),
        ('gt', 'Greater Than'),
        ('gte', 'Greater Than or Equal'),
        ('lt', 'Less Than'),
        ('lte', 'Less Than or Equal'),
        ('in', 'In'),
        ('not_in', 'Not In'),
        ('contains', 'Contains'),
        ('starts_with', 'Starts With'),
        ('ends_with', 'Ends With'),
        ('between', 'Between'),
    ], string='Operator', default='eq', required=True)

    value_float2 = fields.Float(string='Second Value (For Between)')

    # Active
    active = fields.Boolean(string='Active', default=True)

    # Description
    description = fields.Text(string='Description')

    @api.depends('condition_type', 'value_char', 'value_float', 'value_int')
    def _compute_display_name(self):
        for condition in self:
            name = condition.condition_type
            if condition.value_char:
                name = f"{name}: {condition.value_char}"
            elif condition.value_float:
                name = f"{name}: {condition.value_float}"
            elif condition.value_int:
                name = f"{name}: {condition.value_int}"
            condition.display_name = name

    def evaluate(self, context_data):
        """Evaluate this condition against context data"""
        self.ensure_one()

        # Get the value from context based on condition type
        context_value = self._get_context_value(context_data)

        if context_value is None:
            return False

        # Evaluate based on operator
        return self._evaluate_operator(context_value)

    def _get_context_value(self, context_data):
        """Extract value from context data"""
        mapping = {
            'weight_min': 'weight',
            'weight_max': 'weight',
            'value_min': 'declared_value',
            'value_max': 'declared_value',
            'country': 'country_code',
            'state': 'state_code',
            'zip_prefix': 'zip_code',
            'international': 'is_international',
            'domestic': 'is_international',
            'min_packages': 'total_packages',
            'max_packages': 'total_packages',
        }

        key = mapping.get(self.condition_type)
        if key:
            return context_data.get(key)

        return None

    def _evaluate_operator(self, context_value):
        """Evaluate the operator with context value"""
        if self.operator == 'eq':
            return context_value == self._get_value()
        elif self.operator == 'ne':
            return context_value != self._get_value()
        elif self.operator == 'gt':
            return context_value > self._get_value()
        elif self.operator == 'gte':
            return context_value >= self._get_value()
        elif self.operator == 'lt':
            return context_value < self._get_value()
        elif self.operator == 'lte':
            return context_value <= self._get_value()
        elif self.operator == 'in':
            return context_value in self._get_value()
        elif self.operator == 'not_in':
            return context_value not in self._get_value()
        elif self.operator == 'contains':
            return self._get_value() in context_value
        elif self.operator == 'starts_with':
            return str(context_value).startswith(str(self._get_value()))
        elif self.operator == 'ends_with':
            return str(context_value).endswith(str(self._get_value()))
        elif self.operator == 'between':
            return self.value_float <= context_value <= self.value_float2

        return False

    def _get_value(self):
        """Get the value based on condition type"""
        if self.value_float:
            return self.value_float
        elif self.value_int:
            return self.value_int
        elif self.value_char:
            return self.value_char
        elif self.value_m2o:
            return self.value_m2o
        elif self.value_m2m_ids:
            return self.value_m2m_ids
        return None
    