from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class ShippingCustomsItem(models.Model):
    """Customs Declaration Item"""
    _name = 'shipping.customs.item'
    _description = 'Customs Declaration Item'
    _order = 'declaration_id, sequence'
    _rec_name = 'description'

    declaration_id = fields.Many2one(
        'shipping.customs.declaration',
        string='Declaration',
        required=True,
        ondelete='cascade',
        tracking=True,
    )

    sequence = fields.Integer(string='Sequence', default=10)

    # Product Information
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        tracking=True,
    )
    product_name = fields.Char(
        string='Product Name',
        related='product_id.name',
        store=True,
    )

    description = fields.Char(
        string='Description',
        required=True,
        tracking=True,
        help='Detailed description of the item'
    )
    hs_code = fields.Char(
        string='HS Code',
        required=True,
        tracking=True,
        help='Harmonized System (HS) code'
    )
    commodity_code = fields.Char(string='Commodity Code')

    # Quantity
    quantity = fields.Float(
        string='Quantity',
        required=True,
        default=1.0,
        tracking=True,
    )
    uom_id = fields.Many2one(
        'uom.uom',
        string='UoM',
        default=lambda self: self.env.ref('uom.product_uom_unit'),
        required=True,
    )

    # Financial
    unit_value = fields.Monetary(
        string='Unit Value',
        currency_field='currency_id',
        required=True,
        tracking=True,
        help='Value per unit'
    )
    value = fields.Monetary(
        string='Total Value',
        currency_field='currency_id',
        compute='_compute_value',
        store=True,
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
    )

    # Weight
    unit_weight = fields.Float(
        string='Unit Weight (kg)',
        digits='Stock Weight',
        default=0.0,
        help='Weight per unit'
    )
    weight = fields.Float(
        string='Total Weight (kg)',
        digits='Stock Weight',
        compute='_compute_weight',
        store=True,
    )

    # Country
    country_of_origin = fields.Many2one(
        'res.country',
        string='Country of Origin',
        required=True,
        tracking=True,
        help='Country where the goods originated'
    )

    # Tariff Information
    tariff_classification = fields.Char(string='Tariff Classification')
    duty_rate = fields.Float(string='Duty Rate (%)', default=0.0)
    estimated_duty = fields.Monetary(
        string='Estimated Duty',
        currency_field='currency_id',
        compute='_compute_duty',
        store=True,
    )

    # Additional Information
    is_dangerous = fields.Boolean(string='Dangerous Goods', default=False)
    is_restricted = fields.Boolean(string='Restricted Item', default=False)
    is_controlled = fields.Boolean(string='Controlled Item', default=False)
    requires_license = fields.Boolean(string='Requires Export License', default=False)
    license_number = fields.Char(string='License Number')

    # Weight Breakdown
    gross_weight = fields.Float(
        string='Gross Weight (kg)',
        digits='Stock Weight',
        help='Weight including packaging'
    )
    net_weight = fields.Float(
        string='Net Weight (kg)',
        digits='Stock Weight',
        help='Weight excluding packaging'
    )

    # Packaging
    packaging_type = fields.Selection([
        ('box', 'Box'),
        ('crate', 'Crate'),
        ('pallet', 'Pallet'),
        ('drum', 'Drum'),
        ('bag', 'Bag'),
        ('carton', 'Carton'),
        ('container', 'Container'),
        ('other', 'Other'),
    ], string='Packaging Type', default='box')
    packaging_quantity = fields.Integer(string='Number of Packages', default=1)

    # Notes
    notes = fields.Text(string='Notes')

    # Company
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
    )

    _sql_constraints = [
        ('check_quantity_positive', 'CHECK(quantity > 0)',
         'Quantity must be greater than 0.'),
        ('check_unit_value_positive', 'CHECK(unit_value >= 0)',
         'Unit value cannot be negative.'),
        ('check_weight_positive', 'CHECK(unit_weight >= 0)',
         'Unit weight cannot be negative.'),
    ]

    @api.depends('quantity', 'unit_value')
    def _compute_value(self):
        for item in self:
            item.value = item.quantity * item.unit_value

    @api.depends('quantity', 'unit_weight')
    def _compute_weight(self):
        for item in self:
            item.weight = item.quantity * item.unit_weight

    @api.depends('value', 'duty_rate')
    def _compute_duty(self):
        for item in self:
            item.estimated_duty = item.value * (item.duty_rate / 100.0)

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.description = self.product_id.name
            self.uom_id = self.product_id.uom_id.id
            self.unit_weight = self.product_id.weight
            if self.product_id.hs_code:
                self.hs_code = self.product_id.hs_code

    @api.constrains('unit_weight')
    def _check_unit_weight(self):
        for item in self:
            if item.unit_weight < 0:
                raise ValidationError(_('Unit weight cannot be negative.'))

    @api.constrains('duty_rate')
    def _check_duty_rate(self):
        for item in self:
            if item.duty_rate < 0 or item.duty_rate > 100:
                raise ValidationError(_('Duty rate must be between 0 and 100.'))

    def name_get(self):
        result = []
        for item in self:
            name = f"{item.description} - {item.hs_code}"
            if item.value:
                name = f"{name} ({item.value:.2f} {item.currency_id.symbol})"
            result.append((item.id, name))
        return result

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        domain = []
        if name:
            domain = ['|', ('description', operator, name), ('hs_code', operator, name)]
        return self._search(domain + args, limit=limit, access_rights_uid=name_get_uid)
    