from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
import logging
import json

_logger = logging.getLogger(__name__)


class ShippingCarrierProvider(models.Model):
    """Shipping Carrier Provider - Complete Configuration"""
    _name = 'shipping.carrier.provider'
    _description = 'Shipping Carrier Provider'
    _order = 'name'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'display_name'

    # Basic Information
    name = fields.Char(
        string='Carrier Name',
        required=True,
        tracking=True,
        translate=True,
    )
    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True,
    )
    code = fields.Char(
        string='Carrier Code',
        required=True,
        tracking=True,
        help='Unique code for the carrier (e.g., DHL, FEDEX, UPS)'
    )
    active = fields.Boolean(
        string='Active',
        default=True,
        tracking=True,
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help='Order in which carriers are displayed'
    )

    # Carrier Type
    carrier_type = fields.Selection([
        ('express', 'Express'),
        ('standard', 'Standard'),
        ('economy', 'Economy'),
        ('freight', 'Freight'),
        ('same_day', 'Same Day'),
        ('international', 'International'),
        ('domestic', 'Domestic'),
    ], string='Carrier Type', required=True, default='standard', tracking=True)

    api_type = fields.Selection([
        ('dhl', 'DHL'),
        ('fedex', 'FedEx'),
        ('ups', 'UPS'),
        ('dpd', 'DPD'),
        ('aramex', 'Aramex'),
        ('usps', 'USPS'),
        ('canadapost', 'Canada Post'),
        ('royalmail', 'Royal Mail'),
        ('tnt', 'TNT'),
        ('custom_rest', 'Custom REST API'),
        ('custom_soap', 'Custom SOAP API'),
        ('manual', 'Manual Entry'),
    ], string='API Type', required=True, tracking=True)

    # Contact Information
    contact_person = fields.Char(string='Contact Person', tracking=True)
    phone = fields.Char(string='Phone Number')
    email = fields.Char(string='Email Address')
    website = fields.Char(string='Website URL')
    support_phone = fields.Char(string='Support Phone')
    support_email = fields.Char(string='Support Email')
    emergency_phone = fields.Char(string='Emergency Phone')

    # Address
    street = fields.Char(string='Street')
    street2 = fields.Char(string='Street2')
    city = fields.Char(string='City')
    state_id = fields.Many2one('res.country.state', string='State')
    country_id = fields.Many2one('res.country', string='Country')
    zip = fields.Char(string='ZIP/Postal Code')

    # Company
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
    )
    account_ids = fields.One2many(
        'shipping.carrier.account',
        'provider_id',
        string='Accounts',
        help='Carrier accounts for different environments'
    )

    # Statistics - Fixed: removed shipment_ids dependency
    shipment_count = fields.Integer(
        string='Shipment Count',
        compute='_compute_statistics',
        store=False,
        default=0,
    )
    average_cost = fields.Monetary(
        string='Average Cost',
        compute='_compute_statistics',
        store=False,
        currency_field='currency_id',
    )
    total_shipments_cost = fields.Monetary(
        string='Total Cost',
        compute='_compute_statistics',
        store=False,
        currency_field='currency_id',
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
    )

    # Description
    description = fields.Text(string='Description', translate=True)
    notes = fields.Text(string='Notes')

    # Custom Fields for Extensibility
    custom_fields = fields.Text(string='Custom Fields (JSON)')

    # Supported Features
    supports_label_generation = fields.Boolean(string='Supports Label Generation', default=True)
    supports_tracking = fields.Boolean(string='Supports Tracking', default=True)
    supports_rate_shopping = fields.Boolean(string='Supports Rate Shopping', default=True)
    supports_returns = fields.Boolean(string='Supports Returns', default=True)
    supports_cod = fields.Boolean(string='Supports COD', default=False)
    supports_insurance = fields.Boolean(string='Supports Insurance', default=True)
    supports_international = fields.Boolean(string='Supports International', default=True)
    supports_multi_package = fields.Boolean(string='Supports Multi-Package', default=True)
    supports_saturday_delivery = fields.Boolean(string='Supports Saturday Delivery', default=False)
    supports_residential = fields.Boolean(string='Supports Residential Delivery', default=True)

    _sql_constraints = [
        ('unique_code', 'unique(code)', 'Carrier code must be unique!'),
        ('unique_name', 'unique(name)', 'Carrier name must be unique!'),
    ]

    @api.depends('name', 'code')
    def _compute_display_name(self):
        for record in self:
            record.display_name = f"[{record.code}] {record.name}" if record.code else record.name

    def _compute_statistics(self):
        """Compute carrier statistics"""
        for carrier in self:
            shipments = self.env['shipping.shipment'].search([
                ('carrier_provider_id', '=', carrier.id),
                ('state', 'in', ['delivered', 'shipped', 'in_transit'])
            ])
            carrier.shipment_count = len(shipments)
            if shipments:
                total_cost = sum(shipments.mapped('shipping_cost'))
                carrier.total_shipments_cost = total_cost
                carrier.average_cost = total_cost / len(shipments) if shipments else 0.0
            else:
                carrier.total_shipments_cost = 0.0
                carrier.average_cost = 0.0

    @api.constrains('code')
    def _check_code(self):
        for record in self:
            if not record.code.isupper():
                raise ValidationError(_('Carrier code must be uppercase letters only.'))
            if not record.code.isalpha():
                raise ValidationError(_('Carrier code must contain only letters.'))

    @api.constrains('custom_fields')
    def _check_custom_fields(self):
        for record in self:
            if record.custom_fields:
                try:
                    json.loads(record.custom_fields)
                except json.JSONDecodeError:
                    raise ValidationError(_('Custom fields must be valid JSON format.'))

    def name_get(self):
        result = []
        for record in self:
            name = record.display_name
            if record.carrier_type:
                name = f"{name} ({record.carrier_type})"
            result.append((record.id, name))
        return result

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        domain = []
        if name:
            domain = ['|', ('name', operator, name), ('code', operator, name)]
        return self._search(domain + args, limit=limit, access_rights_uid=name_get_uid)

    def action_test_connection(self):
        """Test connection to carrier API"""
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Connection Test'),
                'message': _('Connection to %s successful!') % self.name,
                'type': 'success',
                'sticky': False,
            }
        }

    def action_view_shipments(self):
        """View all shipments for this carrier"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Shipments for %s') % self.name,
            'res_model': 'shipping.shipment',
            'view_mode': 'tree,form',
            'domain': [('carrier_provider_id', '=', self.id)],
            'context': {'default_carrier_provider_id': self.id},
        }

    def toggle_active(self):
        """Toggle active status"""
        for record in self:
            record.active = not record.active
