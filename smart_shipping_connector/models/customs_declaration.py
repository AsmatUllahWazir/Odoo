from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class ShippingCustomsDeclaration(models.Model):
    """Customs Declaration for International Shipments"""
    _name = 'shipping.customs.declaration'
    _description = 'Customs Declaration'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'
    _rec_name = 'name'

    name = fields.Char(
        string='Declaration Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
        tracking=True,
    )

    shipment_id = fields.Many2one(
        'shipping.shipment',
        string='Shipment',
        required=True,
        ondelete='cascade',
        tracking=True,
    )

    # Declaration Type
    declaration_type = fields.Selection([
        ('export', 'Export Declaration'),
        ('import', 'Import Declaration'),
        ('transit', 'Transit Declaration'),
    ], string='Declaration Type', default='export', required=True)

    # Customs Authority
    customs_authority = fields.Char(string='Customs Authority', required=True)
    customs_office = fields.Char(string='Customs Office')
    customs_officer = fields.Char(string='Customs Officer')

    # Declaration Details
    declaration_date = fields.Datetime(
        string='Declaration Date',
        default=fields.Datetime.now,
        required=True,
    )
    declaration_number = fields.Char(string='Declaration Number')

    # Customs Tariff
    tariff_code = fields.Char(string='Tariff Code (HS Code)')
    commodity_code = fields.Char(string='Commodity Code')
    country_of_origin = fields.Many2one(
        'res.country',
        string='Country of Origin',
        required=True,
    )
    country_of_destination = fields.Many2one(
        'res.country',
        string='Country of Destination',
        required=True,
    )

    # Commercial Items
    item_ids = fields.One2many(
        'shipping.customs.item',
        'declaration_id',
        string='Items',
        help='Commercial items in the shipment'
    )

    # Financial
    total_value = fields.Monetary(
        string='Total Value',
        currency_field='currency_id',
        compute='_compute_totals',
        store=True,
    )
    total_weight = fields.Float(
        string='Total Weight (kg)',
        digits='Stock Weight',
        compute='_compute_totals',
        store=True,
    )
    total_quantity = fields.Integer(
        string='Total Quantity',
        compute='_compute_totals',
        store=True,
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
    )

    # Duties and Taxes
    estimated_duties = fields.Monetary(
        string='Estimated Duties',
        currency_field='currency_id',
        help='Estimated customs duties'
    )
    estimated_taxes = fields.Monetary(
        string='Estimated Taxes',
        currency_field='currency_id',
        help='Estimated customs taxes'
    )
    total_duties_taxes = fields.Monetary(
        string='Total Duties & Taxes',
        currency_field='currency_id',
        compute='_compute_duties_taxes',
        store=True,
    )

    # Import/Export Permits
    permit_number = fields.Char(string='Permit Number')
    permit_expiry = fields.Datetime(string='Permit Expiry Date')
    license_number = fields.Char(string='License Number')

    # Special Conditions
    is_restricted = fields.Boolean(string='Restricted Items')
    is_controlled = fields.Boolean(string='Controlled Items')
    is_dangerous = fields.Boolean(string='Dangerous Goods')

    # Additional Information
    additional_info = fields.Text(string='Additional Information')
    notes = fields.Text(string='Notes')

    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('prepared', 'Prepared'),
        ('submitted', 'Submitted'),
        ('in_process', 'In Process'),
        ('cleared', 'Cleared'),
        ('held', 'Held'),
        ('released', 'Released'),
        ('rejected', 'Rejected'),
    ], string='Status', default='draft', tracking=True)

    # Company
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
    )

    _sql_constraints = [
        ('unique_declaration', 'unique(declaration_number)', 'Declaration number must be unique!'),
    ]

    @api.depends('item_ids', 'item_ids.value', 'item_ids.weight', 'item_ids.quantity')
    def _compute_totals(self):
        for declaration in self:
            declaration.total_value = sum(declaration.item_ids.mapped('value'))
            declaration.total_weight = sum(declaration.item_ids.mapped('weight'))
            declaration.total_quantity = sum(declaration.item_ids.mapped('quantity'))

    @api.depends('estimated_duties', 'estimated_taxes')
    def _compute_duties_taxes(self):
        for declaration in self:
            declaration.total_duties_taxes = declaration.estimated_duties + declaration.estimated_taxes

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('shipping.customs.declaration') or _('New')
        return super(ShippingCustomsDeclaration, self).create(vals)

    def action_submit(self):
        """Submit customs declaration"""
        self.ensure_one()
        if self.state == 'prepared':
            self.state = 'submitted'
            self.message_post(body=_('Customs declaration submitted.'))

    def action_clear(self):
        """Mark as cleared"""
        self.ensure_one()
        if self.state in ['submitted', 'in_process']:
            self.state = 'cleared'
            self.message_post(body=_('Customs declaration cleared.'))

    def action_release(self):
        """Release customs declaration"""
        self.ensure_one()
        if self.state == 'cleared':
            self.state = 'released'
            self.message_post(body=_('Customs declaration released.'))

    def action_hold(self):
        """Hold customs declaration"""
        self.ensure_one()
        if self.state not in ['released', 'rejected']:
            self.state = 'held'
            self.message_post(body=_('Customs declaration on hold.'))

    def action_reject(self):
        """Reject customs declaration"""
        self.ensure_one()
        if self.state not in ['released']:
            self.state = 'rejected'
            self.message_post(body=_('Customs declaration rejected.'))

    def action_generate_pdf(self):
        """Generate customs declaration PDF"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Customs Declaration PDF'),
            'res_model': 'shipping.customs.declaration',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'pdf_report': 'smart_shipping_connector.customs_declaration_report',
            },
        }


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
    )

    sequence = fields.Integer(string='Sequence', default=10)

    # Product Information
    product_id = fields.Many2one(
        'product.product',
        string='Product',
    )
    description = fields.Char(string='Description', required=True)
    hs_code = fields.Char(string='HS Code', required=True)
    commodity_code = fields.Char(string='Commodity Code')

    # Quantity
    quantity = fields.Float(string='Quantity', required=True, default=1.0)
    uom_id = fields.Many2one(
        'uom.uom',
        string='UoM',
        default=lambda self: self.env.ref('uom.product_uom_unit'),
    )

    # Financial
    unit_value = fields.Monetary(
        string='Unit Value',
        currency_field='currency_id',
        required=True,
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
    unit_weight = fields.Float(string='Unit Weight (kg)', digits='Stock Weight')
    weight = fields.Float(string='Total Weight (kg)', digits='Stock Weight', compute='_compute_weight', store=True)

    # Country
    country_of_origin = fields.Many2one(
        'res.country',
        string='Country of Origin',
        required=True,
    )

    # Additional Info
    is_dangerous = fields.Boolean(string='Dangerous Goods')
    is_restricted = fields.Boolean(string='Restricted Item')
    notes = fields.Text(string='Notes')

    # Company
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
    )

    @api.depends('quantity', 'unit_value')
    def _compute_value(self):
        for item in self:
            item.value = item.quantity * item.unit_value

    @api.depends('quantity', 'unit_weight')
    def _compute_weight(self):
        for item in self:
            item.weight = item.quantity * (item.unit_weight or 0.0)

    def name_get(self):
        result = []
        for item in self:
            name = f"{item.description} - {item.hs_code}"
            if item.value:
                name = f"{name} ({item.value:.2f})"
            result.append((item.id, name))
        return result
    