from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class ShippingReturnItem(models.Model):
    """Return Items"""
    _name = 'shipping.return.item'
    _description = 'Return Item'
    _order = 'return_id, sequence'
    _rec_name = 'product_id'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    return_id = fields.Many2one(
        'shipping.return',
        string='Return',
        required=True,
        ondelete='cascade',
        tracking=True,
    )

    sequence = fields.Integer(string='Sequence', default=10)

    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True,
        tracking=True,
    )
    product_name = fields.Char(
        string='Product Name',
        related='product_id.name',
        store=True,
    )
    product_code = fields.Char(
        string='Product Code',
        related='product_id.default_code',
        store=True,
    )
    product_image = fields.Binary(
        string='Product Image',
        related='product_id.image_128',
        store=True,
    )

    quantity = fields.Integer(
        string='Quantity',
        required=True,
        default=1,
        tracking=True,
    )
    uom_id = fields.Many2one(
        'uom.uom',
        string='UoM',
        related='product_id.uom_id',
        store=True,
    )

    price = fields.Monetary(
        string='Price',
        currency_field='currency_id',
        tracking=True,
        help='Unit price'
    )
    subtotal = fields.Monetary(
        string='Subtotal',
        currency_field='currency_id',
        compute='_compute_subtotal',
        store=True,
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
    )

    reason = fields.Selection([
        ('damaged', 'Damaged'),
        ('defective', 'Defective'),
        ('wrong_item', 'Wrong Item'),
        ('wrong_size', 'Wrong Size'),
        ('wrong_color', 'Wrong Color'),
        ('not_as_described', 'Not as Described'),
        ('change_mind', 'Changed Mind'),
        ('better_price', 'Found Better Price'),
        ('shipping_delay', 'Shipping Delay'),
        ('wrong_address', 'Wrong Address'),
        ('duplicate', 'Duplicate Order'),
        ('other', 'Other'),
    ], string='Reason', default='other', required=True)

    reason_notes = fields.Text(string='Reason Notes')

    condition = fields.Selection([
        ('new', 'New/Unused'),
        ('opened', 'Opened/Used'),
        ('damaged', 'Damaged'),
        ('defective', 'Defective'),
        ('missing_parts', 'Missing Parts'),
        ('used', 'Used'),
    ], string='Condition', default='new', required=True)

    condition_notes = fields.Text(string='Condition Notes')

    # For exchange
    exchange_product_id = fields.Many2one(
        'product.product',
        string='Exchange Product',
        help='Product to exchange for'
    )
    exchange_quantity = fields.Integer(
        string='Exchange Quantity',
        default=1,
        help='Quantity to exchange'
    )
    exchange_reason = fields.Text(string='Exchange Reason')

    # Inspection
    inspected = fields.Boolean(string='Inspected', default=False)
    inspected_by = fields.Many2one(
        'res.users',
        string='Inspected By',
    )
    inspection_date = fields.Datetime(string='Inspection Date')
    inspection_notes = fields.Text(string='Inspection Notes')
    inspection_result = fields.Selection([
        ('pass', 'Pass - Accept Return'),
        ('fail', 'Fail - Reject Return'),
        ('partial', 'Partial - Partial Accept'),
    ], string='Inspection Result')

    # Restocking
    restock_quantity = fields.Integer(
        string='Restock Quantity',
        default=0,
        help='Quantity to restock'
    )
    restock_date = fields.Datetime(string='Restock Date')
    restock_notes = fields.Text(string='Restock Notes')

    # Return Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_return', 'In Return'),
        ('received', 'Received'),
        ('inspected', 'Inspected'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('restocked', 'Restocked'),
        ('exchanged', 'Exchanged'),
        ('refunded', 'Refunded'),
    ], string='Status', default='draft', tracking=True)

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
        ('check_restock_positive', 'CHECK(restock_quantity >= 0)',
         'Restock quantity cannot be negative.'),
    ]

    @api.depends('quantity', 'price')
    def _compute_subtotal(self):
        for item in self:
            item.subtotal = item.quantity * (item.price or 0.0)

    @api.constrains('quantity')
    def _check_quantity(self):
        for item in self:
            if item.quantity <= 0:
                raise ValidationError(_('Quantity must be greater than 0.'))

    @api.constrains('restock_quantity')
    def _check_restock_quantity(self):
        for item in self:
            if item.restock_quantity > item.quantity:
                raise ValidationError(_('Restock quantity cannot exceed returned quantity.'))

    def action_inspect(self):
        """Mark item as inspected"""
        self.ensure_one()
        self.inspected = True
        self.inspected_by = self.env.user
        self.inspection_date = fields.Datetime.now()
        self.state = 'inspected'

    def action_approve(self):
        """Approve return item"""
        self.ensure_one()
        if self.state in ['inspected', 'received']:
            self.state = 'approved'
            self.inspection_result = 'pass'
            self.message_post(body=_('Return item approved.'))

    def action_reject(self):
        """Reject return item"""
        self.ensure_one()
        if self.state in ['inspected', 'received']:
            self.state = 'rejected'
            self.inspection_result = 'fail'
            self.message_post(body=_('Return item rejected.'))

    def action_restock(self):
        """Restock item"""
        self.ensure_one()
        if self.state == 'approved':
            self.state = 'restocked'
            self.restock_date = fields.Datetime.now()
            self.restock_quantity = self.quantity
            self.message_post(body=_('Item restocked.'))

    def action_refund(self):
        """Mark item as refunded"""
        self.ensure_one()
        if self.state in ['approved', 'restocked']:
            self.state = 'refunded'
            self.message_post(body=_('Item refunded.'))

    def name_get(self):
        result = []
        for item in self:
            name = f"{item.product_name} x{item.quantity}"
            if item.price:
                name = f"{name} @ {item.price:.2f}"
            if item.condition != 'new':
                name = f"{name} ({item.condition})"
            result.append((item.id, name))
        return result

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        domain = []
        if name:
            domain = ['|', ('product_name', operator, name), ('product_code', operator, name)]
        return self._search(domain + args, limit=limit, access_rights_uid=name_get_uid)
    