from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class ShippingShipmentPackage(models.Model):
    """Shipment Package"""
    _name = 'shipping.shipment.package'
    _description = 'Shipment Package'
    _order = 'shipment_id, sequence'
    _rec_name = 'name'

    name = fields.Char(
        string='Package Name',
        default=lambda self: _('New Package'),
        required=True,
    )
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
        default=1.0,
    )
    length = fields.Float(
        string='Length',
        digits='Stock Dimension',
        help='Length in cm',
        default=0.0,
    )
    width = fields.Float(
        string='Width',
        digits='Stock Dimension',
        help='Width in cm',
        default=0.0,
    )
    height = fields.Float(
        string='Height',
        digits='Stock Dimension',
        help='Height in cm',
        default=0.0,
    )

    package_type = fields.Selection([
        ('box', 'Box'),
        ('envelope', 'Envelope'),
        ('pallet', 'Pallet'),
        ('tube', 'Tube'),
        ('custom', 'Custom'),
        ('letter', 'Letter'),
        ('parcel', 'Parcel'),
        ('large_parcel', 'Large Parcel'),
        ('freight', 'Freight'),
    ], string='Package Type', default='box', required=True)

    package_material = fields.Selection([
        ('cardboard', 'Cardboard'),
        ('plastic', 'Plastic'),
        ('wood', 'Wood'),
        ('metal', 'Metal'),
        ('foam', 'Foam'),
        ('other', 'Other'),
    ], string='Package Material', default='cardboard')

    # Content
    description = fields.Text(string='Description')
    declared_value = fields.Float(string='Declared Value')
    content_type = fields.Selection([
        ('document', 'Document'),
        ('gift', 'Gift'),
        ('sample', 'Sample'),
        ('commercial', 'Commercial'),
        ('return', 'Return'),
        ('repair', 'Repair'),
    ], string='Content Type', default='commercial')

    content_ids = fields.Many2many(
        'product.product',
        string='Contents',
        help='Products in this package'
    )

    # Handling
    handling_instructions = fields.Text(string='Handling Instructions')
    fragile = fields.Boolean(string='Fragile')
    hazardous = fields.Boolean(string='Hazardous Materials')
    temperature_sensitive = fields.Boolean(string='Temperature Sensitive')
    temperature_range = fields.Char(string='Temperature Range')

    # Tracking
    tracking_number = fields.Char(string='Tracking Number', copy=False)

    # Computed
    volume = fields.Float(
        string='Volume (cm³)',
        compute='_compute_volume',
        store=True,
        help='Volume in cubic centimeters'
    )
    dimensional_weight = fields.Float(
        string='Dimensional Weight (kg)',
        compute='_compute_dimensional_weight',
        store=True,
        help='Dimensional weight in kg'
    )
    chargeable_weight = fields.Float(
        string='Chargeable Weight (kg)',
        compute='_compute_chargeable_weight',
        store=True,
        help='Weight used for shipping charges (max of actual and dimensional)'
    )

    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('ready', 'Ready'),
        ('packed', 'Packed'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
    ], string='Status', default='draft', tracking=True)

    # Company
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
    )

    _sql_constraints = [
        ('check_weight_positive', 'CHECK(weight >= 0)', 'Weight cannot be negative.'),
        ('check_dimensions_positive', 'CHECK(length >= 0 AND width >= 0 AND height >= 0)',
         'Dimensions cannot be negative.'),
    ]

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

    @api.depends('weight', 'dimensional_weight')
    def _compute_chargeable_weight(self):
        for package in package:
            package.chargeable_weight = max(package.weight, package.dimensional_weight)

    @api.constrains('weight')
    def _check_weight(self):
        for package in self:
            if package.weight <= 0:
                raise ValidationError(_('Package weight must be greater than 0.'))

    def name_get(self):
        result = []
        for package in self:
            name = package.name
            if package.shipment_id:
                name = f"{package.shipment_id.name} - {name}"
            if package.package_type:
                name = f"{name} ({package.package_type})"
            result.append((package.id, name))
        return result

    def action_view_shipment(self):
        """View parent shipment"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Shipment'),
            'res_model': 'shipping.shipment',
            'res_id': self.shipment_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
    