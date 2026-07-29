from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class ShippingPackage(models.Model):
    """Package inside a shipment"""
    _name = 'shipping.package'
    _description = 'Shipping Package'
    _order = 'shipment_id, sequence'
    _rec_name = 'name'

    name = fields.Char(string='Package Name', default=lambda self: _('New Package'))
    sequence = fields.Integer(string='Sequence', default=10)

    shipment_id = fields.Many2one(
        'shipping.shipment',
        string='Shipment',
        required=True,
        ondelete='cascade',
    )

    # Dimensions
    weight = fields.Float(
        string='Weight',
        required=True,
        digits='Stock Weight',
        help='Weight in kg',
    )
    length = fields.Float(
        string='Length',
        digits='Stock Dimension',
        help='Length in cm',
    )
    width = fields.Float(
        string='Width',
        digits='Stock Dimension',
        help='Width in cm',
    )
    height = fields.Float(
        string='Height',
        digits='Stock Dimension',
        help='Height in cm',
    )

    package_type = fields.Selection([
        ('box', 'Box'),
        ('envelope', 'Envelope'),
        ('pallet', 'Pallet'),
        ('tube', 'Tube'),
        ('custom', 'Custom'),
    ], string='Package Type', default='box', required=True)

    # Content
    description = fields.Text(string='Description')
    declared_value = fields.Float(string='Declared Value')

    tracking_number = fields.Char(string='Tracking Number')

    # Computed
    volume = fields.Float(
        string='Volume',
        compute='_compute_volume',
        store=True,
        help='Volume in cubic cm',
    )
    dimensional_weight = fields.Float(
        string='Dimensional Weight',
        compute='_compute_dimensional_weight',
        store=True,
        help='Dimensional weight in kg',
    )

    @api.depends('length', 'width', 'height')
    def _compute_volume(self):
        for package in self:
            package.volume = package.length * package.width * package.height

    @api.depends('length', 'width', 'height')
    def _compute_dimensional_weight(self):
        for package in self:
            # Standard dimensional factor (5000 for cm/kg)
            if package.length and package.width and package.height:
                package.dimensional_weight = (package.length * package.width * package.height) / 5000.0
            else:
                package.dimensional_weight = 0.0
