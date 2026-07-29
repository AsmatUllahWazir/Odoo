from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from odoo.addons import decimal_precision as dp
import logging
import base64
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)


class ShippingReturnOrder(models.Model):
    """Complete Return Order Management"""
    _name = 'shipping.return'
    _description = 'Shipping Return Order'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'
    _rec_name = 'name'

    # ==================== BASIC INFORMATION ====================
    name = fields.Char(
        string='Return Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
        tracking=True,
    )

    state = fields.Selection([
        ('draft', 'Draft'),
        ('requested', 'Requested'),
        ('approved', 'Approved'),
        ('label_generated', 'Label Generated'),
        ('shipped', 'Shipped'),
        ('received', 'Received'),
        ('inspected', 'Inspected'),
        ('completed', 'Completed'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True, required=True)

    return_type = fields.Selection([
        ('customer_return', 'Customer Return'),
        ('damaged_return', 'Damaged Return'),
        ('exchange', 'Exchange'),
        ('warranty', 'Warranty'),
        ('recall', 'Product Recall'),
        ('repair', 'Repair'),
        ('restock', 'Restock'),
    ], string='Return Type', required=True, tracking=True)

    priority = fields.Selection([
        ('0', 'Normal'),
        ('1', 'Urgent'),
        ('2', 'High'),
        ('3', 'Critical'),
    ], string='Priority', default='0', tracking=True)

    # ==================== RELATED DOCUMENTS ====================
    original_shipment_id = fields.Many2one(
        'shipping.shipment',
        string='Original Shipment',
        tracking=True,
        help='Original shipment being returned'
    )
    sale_order_id = fields.Many2one(
        'sale.order',
        string='Sales Order',
        tracking=True,
    )
    customer_id = fields.Many2one(
        'res.partner',
        string='Customer',
        required=True,
        tracking=True,
    )
    user_id = fields.Many2one(
        'res.users',
        string='Responsible',
        default=lambda self: self.env.user,
        tracking=True,
    )

    # ==================== RETURN DETAILS ====================
    reason = fields.Text(string='Return Reason', required=True)
    description = fields.Text(string='Description')
    notes = fields.Text(string='Notes')
    internal_notes = fields.Text(string='Internal Notes')

    # ==================== ITEMS ====================
    item_ids = fields.One2many(
        'shipping.return.item',
        'return_id',
        string='Return Items',
        help='Items being returned'
    )

    total_items = fields.Integer(
        string='Total Items',
        compute='_compute_item_totals',
        store=True,
    )
    total_quantity = fields.Integer(
        string='Total Quantity',
        compute='_compute_item_totals',
        store=True,
    )
    total_value = fields.Monetary(
        string='Total Value',
        currency_field='currency_id',
        compute='_compute_item_totals',
        store=True,
    )

    # ==================== SHIPPING ====================
    carrier_provider_id = fields.Many2one(
        'shipping.carrier.provider',
        string='Carrier Provider',
        required=True,
        tracking=True,
    )
    carrier_account_id = fields.Many2one(
        'shipping.carrier.account',
        string='Carrier Account',
        required=True,
        tracking=True,
        domain="[('provider_id', '=', carrier_provider_id)]"
    )
    carrier_service_id = fields.Many2one(
        'shipping.carrier.service',
        string='Carrier Service',
        tracking=True,
        domain="[('provider_id', '=', carrier_provider_id)]"
    )

    service_type = fields.Char(string='Service Type', tracking=True)
    tracking_number = fields.Char(string='Tracking Number', tracking=True)
    tracking_url = fields.Char(string='Tracking URL', readonly=True)

    # ==================== LABEL ====================
    label_pdf = fields.Binary(string='Return Label', attachment=True)
    label_filename = fields.Char(string='Label Filename')
    label_generated_date = fields.Datetime(string='Label Generated Date')

    # ==================== PACKAGE ====================
    weight = fields.Float(string='Weight (kg)', digits='Stock Weight')
    length = fields.Float(string='Length (cm)', digits='Stock Dimension')
    width = fields.Float(string='Width (cm)', digits='Stock Dimension')
    height = fields.Float(string='Height (cm)', digits='Stock Dimension')
    package_type = fields.Selection([
        ('box', 'Box'),
        ('envelope', 'Envelope'),
        ('pallet', 'Pallet'),
        ('tube', 'Tube'),
        ('custom', 'Custom'),
    ], string='Package Type', default='box')

    # ==================== FINANCIAL ====================
    return_cost = fields.Monetary(
        string='Return Cost',
        currency_field='currency_id',
        tracking=True,
        help='Cost of return shipping'
    )
    refund_amount = fields.Monetary(
        string='Refund Amount',
        currency_field='currency_id',
        help='Amount to refund to customer'
    )
    restocking_fee = fields.Monetary(
        string='Restocking Fee',
        currency_field='currency_id',
        help='Restocking fee applied'
    )
    restocking_fee_percent = fields.Float(
        string='Restocking Fee %',
        default=0.0,
        help='Restocking fee percentage'
    )

    shipping_charge = fields.Monetary(
        string='Shipping Charge',
        currency_field='currency_id',
        help='Shipping charge for return'
    )
    handling_fee = fields.Monetary(
        string='Handling Fee',
        currency_field='currency_id',
        help='Handling fee for return'
    )
    total_charge = fields.Monetary(
        string='Total Charge',
        currency_field='currency_id',
        compute='_compute_total_charge',
        store=True,
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
    )

    # ==================== ADDRESS ====================
    return_address_name = fields.Char(string='Return Address Name')
    return_address = fields.Text(string='Return Address')
    return_city = fields.Char(string='Return City')
    return_state_id = fields.Many2one('res.country.state', string='Return State')
    return_country_id = fields.Many2one('res.country', string='Return Country')
    return_zip = fields.Char(string='Return ZIP')
    return_phone = fields.Char(string='Return Phone')
    return_email = fields.Char(string='Return Email')

    # ==================== RMA ====================
    rma_number = fields.Char(
        string='RMA Number',
        tracking=True,
        copy=False,
        help='Return Merchandise Authorization Number'
    )
    rma_expiry_date = fields.Datetime(
        string='RMA Expiry Date',
        help='Date when RMA expires'
    )

    # ==================== DATES ====================
    request_date = fields.Datetime(
        string='Request Date',
        default=fields.Datetime.now,
        tracking=True,
    )
    approval_date = fields.Datetime(
        string='Approval Date',
        tracking=True,
    )
    shipped_date = fields.Datetime(
        string='Shipped Date',
        tracking=True,
    )
    received_date = fields.Datetime(
        string='Received Date',
        tracking=True,
    )
    inspected_date = fields.Datetime(
        string='Inspected Date',
    )
    completed_date = fields.Datetime(
        string='Completed Date',
        tracking=True,
    )
    rejected_date = fields.Datetime(
        string='Rejected Date',
    )

    # ==================== TRACKING ====================
    tracking_event_ids = fields.One2many(
        'shipping.tracking.event',
        'return_id',
        string='Tracking Events',
    )

    # ==================== COMPANY ====================
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
    )

    # ==================== COMPUTED FIELDS ====================
    days_open = fields.Integer(
        string='Days Open',
        compute='_compute_days_open',
        store=True,
        help='Number of days the return has been open'
    )

    is_late = fields.Boolean(
        string='Is Late',
        compute='_compute_is_late',
        store=True,
        help='Return is past expected timeframe'
    )

    # ==================== CONSTRAINTS ====================
    _sql_constraints = [
        ('unique_rma', 'unique(rma_number)', 'RMA number must be unique!'),
        ('check_weight_positive', 'CHECK(weight >= 0)', 'Weight cannot be negative.'),
    ]

    # ==================== COMPUTATION METHODS ====================

    @api.depends('item_ids', 'item_ids.quantity', 'item_ids.price')
    def _compute_item_totals(self):
        for return_order in self:
            return_order.total_items = len(return_order.item_ids)
            return_order.total_quantity = sum(return_order.item_ids.mapped('quantity'))
            return_order.total_value = sum(
                return_order.item_ids.mapped('price') * return_order.item_ids.mapped('quantity'))

    @api.depends('return_cost', 'shipping_charge', 'handling_fee', 'restocking_fee')
    def _compute_total_charge(self):
        for return_order in self:
            return_order.total_charge = (
                    return_order.return_cost +
                    return_order.shipping_charge +
                    return_order.handling_fee +
                    return_order.restocking_fee
            )

    @api.depends('request_date', 'state')
    def _compute_days_open(self):
        for return_order in self:
            if return_order.state in ['completed', 'cancelled', 'rejected']:
                return_order.days_open = 0
            elif return_order.request_date:
                delta = fields.Datetime.now() - return_order.request_date
                return_order.days_open = delta.days
            else:
                return_order.days_open = 0

    @api.depends('request_date', 'rma_expiry_date', 'state')
    def _compute_is_late(self):
        for return_order in self:
            if return_order.state in ['completed', 'cancelled', 'rejected']:
                return_order.is_late = False
            elif return_order.rma_expiry_date:
                return_order.is_late = fields.Datetime.now() > return_order.rma_expiry_date
            else:
                # Default 30 days
                if return_order.request_date:
                    days = (fields.Datetime.now() - return_order.request_date).days
                    return_order.is_late = days > 30
                else:
                    return_order.is_late = False

    # ==================== ORM METHODS ====================

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('shipping.return') or _('New')

        # Auto-generate RMA number
        if not vals.get('rma_number'):
            vals['rma_number'] = self.env['ir.sequence'].next_by_code('shipping.rma') or f"RMA-{vals['name']}"

        # Set default expiry (30 days from now)
        if not vals.get('rma_expiry_date'):
            vals['rma_expiry_date'] = fields.Datetime.now() + timedelta(days=30)

        return super(ShippingReturnOrder, self).create(vals)

    # ==================== ACTION METHODS ====================

    def action_request_approval(self):
        """Request approval for return"""
        self.ensure_one()
        if self.state == 'draft':
            self.state = 'requested'
            self.request_date = fields.Datetime.now()
            self.message_post(body=_('Return approval requested.'))
            self._send_approval_request_notification()

    def action_approve(self):
        """Approve return"""
        self.ensure_one()
        if self.state == 'requested':
            self.state = 'approved'
            self.approval_date = fields.Datetime.now()
            self.message_post(body=_('Return approved.'))
            self._send_approval_notification()

    def action_reject(self):
        """Reject return"""
        self.ensure_one()
        if self.state in ['requested', 'approved']:
            self.state = 'rejected'
            self.rejected_date = fields.Datetime.now()
            self.message_post(body=_('Return rejected.'))
            self._send_rejection_notification()

    def action_generate_label(self):
        """Generate return shipping label"""
        self.ensure_one()

        if self.state != 'approved':
            raise UserError(_('Return must be approved before generating label.'))

        self.state = 'label_generated'
        self.label_generated_date = fields.Datetime.now()

        # TODO: Implement actual label generation
        # Create dummy label
        import tempfile
        from reportlab.pdfgen import canvas
        from io import BytesIO

        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=(400, 600))
        c.drawString(50, 550, "RETURN SHIPPING LABEL")
        c.drawString(50, 520, f"Return Reference: {self.name}")
        c.drawString(50, 490, f"RMA Number: {self.rma_number}")
        c.drawString(50, 460, f"Customer: {self.customer_id.name}")
        c.drawString(50, 430, f"Return Address: {self.return_address or self.company_id.street}")
        c.drawString(50, 370, "RETURN TO:")
        c.drawString(50, 350, self.return_address_name or self.company_id.name)
        c.drawString(50, 330, self.return_address or self.company_id.street)
        c.drawString(50, 310, f"{self.return_city or self.company_id.city}")
        c.drawString(50, 290, f"{self.return_state_id.name if self.return_state_id else ''} {self.return_zip or ''}")
        c.save()

        pdf_data = buffer.getvalue()
        buffer.close()

        self.label_pdf = base64.b64encode(pdf_data)
        self.label_filename = f"return_label_{self.name}_{self.rma_number}.pdf"

        self.message_post(
            body=_('Return label generated successfully.'),
            attachments=[(self.label_filename, self.label_pdf)]
        )

        return {
            'type': 'ir.actions.act_window',
            'name': _('Return'),
            'res_model': 'shipping.return',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_mark_shipped(self):
        """Mark return as shipped"""
        self.ensure_one()
        if self.state in ['label_generated', 'approved']:
            self.state = 'shipped'
            self.shipped_date = fields.Datetime.now()
            self.message_post(body=_('Return shipped.'))
            self._send_shipped_notification()

    def action_mark_received(self):
        """Mark return as received"""
        self.ensure_one()
        if self.state == 'shipped':
            self.state = 'received'
            self.received_date = fields.Datetime.now()
            self.message_post(body=_('Return received.'))
            self._send_received_notification()

    def action_inspect(self):
        """Inspect return"""
        self.ensure_one()
        if self.state == 'received':
            self.state = 'inspected'
            self.inspected_date = fields.Datetime.now()
            self.message_post(body=_('Return inspected.'))

    def action_complete(self):
        """Complete return"""
        self.ensure_one()
        if self.state == 'inspected':
            self.state = 'completed'
            self.completed_date = fields.Datetime.now()
            self.message_post(body=_('Return completed.'))
            self._send_completed_notification()

            # Process refund if applicable
            if self.refund_amount > 0:
                self._process_refund()

    def action_cancel(self):
        """Cancel return"""
        self.ensure_one()
        if self.state not in ['completed', 'cancelled']:
            self.state = 'cancelled'
            self.message_post(body=_('Return cancelled.'))

    def action_view_shipment(self):
        """View original shipment"""
        self.ensure_one()
        if self.original_shipment_id:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Original Shipment'),
                'res_model': 'shipping.shipment',
                'res_id': self.original_shipment_id.id,
                'view_mode': 'form',
                'target': 'current',
            }
        return {'type': 'ir.actions.act_window_close'}

    def action_view_tracking(self):
        """View tracking events"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Tracking Events'),
            'res_model': 'shipping.tracking.event',
            'view_mode': 'tree,form',
            'domain': [('return_id', '=', self.id)],
        }

    def action_view_items(self):
        """View return items"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Return Items'),
            'res_model': 'shipping.return.item',
            'view_mode': 'tree,form',
            'domain': [('return_id', '=', self.id)],
        }

    # ==================== NOTIFICATION METHODS ====================

    def _send_approval_request_notification(self):
        """Send approval request notification"""
        self.ensure_one()
        # TODO: Implement actual notification

    def _send_approval_notification(self):
        """Send approval notification"""
        self.ensure_one()
        # TODO: Implement actual notification

    def _send_rejection_notification(self):
        """Send rejection notification"""
        self.ensure_one()
        # TODO: Implement actual notification

    def _send_shipped_notification(self):
        """Send shipped notification"""
        self.ensure_one()
        # TODO: Implement actual notification

    def _send_received_notification(self):
        """Send received notification"""
        self.ensure_one()
        # TODO: Implement actual notification

    def _send_completed_notification(self):
        """Send completed notification"""
        self.ensure_one()
        # TODO: Implement actual notification

    # ==================== FINANCIAL METHODS ====================

    def _process_refund(self):
        """Process refund for return"""
        self.ensure_one()
        # TODO: Implement refund processing
        _logger.info(f"Processing refund of {self.refund_amount} for return {self.name}")

    # ==================== HELPER METHODS ====================

    def get_status_display(self):
        """Get formatted status for display"""
        self.ensure_one()
        status_map = {
            'draft': 'Draft',
            'requested': 'Requested',
            'approved': 'Approved',
            'label_generated': 'Label Generated',
            'shipped': 'Shipped',
            'received': 'Received',
            'inspected': 'Inspected',
            'completed': 'Completed ✓',
            'rejected': 'Rejected ✗',
            'cancelled': 'Cancelled ✗',
        }
        return status_map.get(self.state, self.state)

    def get_status_color(self):
        """Get color for status"""
        self.ensure_one()
        color_map = {
            'draft': 'text-muted',
            'requested': 'text-warning',
            'approved': 'text-primary',
            'label_generated': 'text-primary',
            'shipped': 'text-info',
            'received': 'text-info',
            'inspected': 'text-info',
            'completed': 'text-success',
            'rejected': 'text-danger',
            'cancelled': 'text-danger',
        }
        return color_map.get(self.state, 'text-muted')


class ShippingReturnItem(models.Model):
    """Return Items"""
    _name = 'shipping.return.item'
    _description = 'Return Item'
    _order = 'return_id, sequence'
    _rec_name = 'product_id'

    return_id = fields.Many2one(
        'shipping.return',
        string='Return',
        required=True,
        ondelete='cascade',
    )

    sequence = fields.Integer(string='Sequence', default=10)

    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True,
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

    quantity = fields.Integer(
        string='Quantity',
        required=True,
        default=1,
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
        ('other', 'Other'),
    ], string='Reason', default='other')

    condition = fields.Selection([
        ('new', 'New/Unused'),
        ('opened', 'Opened/Used'),
        ('damaged', 'Damaged'),
        ('defective', 'Defective'),
    ], string='Condition', default='new')

    notes = fields.Text(string='Notes')

    # For exchange
    exchange_product_id = fields.Many2one(
        'product.product',
        string='Exchange Product',
        help='Product to exchange for'
    )

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
    )

    @api.depends('quantity', 'price')
    def _compute_subtotal(self):
        for item in self:
            item.subtotal = item.quantity * item.price

    @api.constrains('quantity')
    def _check_quantity(self):
        for item in self:
            if item.quantity <= 0:
                raise ValidationError(_('Quantity must be greater than 0.'))

    def name_get(self):
        result = []
        for item in self:
            name = f"{item.product_name} x{item.quantity}"
            if item.price:
                name = f"{name} @ {item.price:.2f}"
            result.append((item.id, name))
        return result
    