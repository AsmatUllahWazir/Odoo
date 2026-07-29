from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from odoo.addons import decimal_precision as dp
import logging
import base64
from datetime import datetime, timedelta
import json

_logger = logging.getLogger(__name__)


class ShippingShipment(models.Model):
    """Main Shipment Document - Complete Implementation"""
    _name = 'shipping.shipment'
    _description = 'Shipping Shipment'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'
    _rec_name = 'name'

    # ==================== BASIC INFORMATION ====================
    name = fields.Char(
        string='Shipment Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
        tracking=True,
    )

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('processing', 'Processing'),
        ('label_generated', 'Label Generated'),
        ('shipped', 'Shipped'),
        ('in_transit', 'In Transit'),
        ('out_for_delivery', 'Out for Delivery'),
        ('delivered', 'Delivered'),
        ('exception', 'Exception'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True, required=True,
        help='Current status of the shipment')

    priority = fields.Selection([
        ('0', 'Normal'),
        ('1', 'Urgent'),
        ('2', 'Very Urgent'),
        ('3', 'Emergency'),
    ], string='Priority', default='0', tracking=True)

    # ==================== RELATED DOCUMENTS ====================
    sale_order_id = fields.Many2one(
        'sale.order',
        string='Sales Order',
        tracking=True,
        help='Related sales order'
    )
    stock_picking_id = fields.Many2one(
        'stock.picking',
        string='Delivery Order',
        tracking=True,
        help='Related stock picking'
    )
    invoice_id = fields.Many2one(
        'account.move',
        string='Invoice',
        tracking=True,
        help='Related invoice'
    )
    purchase_order_id = fields.Many2one(
        'purchase.order',
        string='Purchase Order',
        tracking=True,
    )

    # ==================== CARRIER INFORMATION ====================
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

    service_type = fields.Char(
        string='Service Type',
        tracking=True,
        help='Service code or type used'
    )
    service_description = fields.Char(
        string='Service Description',
        tracking=True,
        help='Description of the service used'
    )

    # ==================== TRACKING INFORMATION ====================
    tracking_number = fields.Char(
        string='Tracking Number',
        tracking=True,
        copy=False,
        help='Carrier tracking number'
    )
    tracking_url = fields.Char(
        string='Tracking URL',
        readonly=True,
        compute='_compute_tracking_url',
        store=True,
        help='URL to track shipment'
    )
    alternative_tracking_numbers = fields.Text(
        string='Alternative Tracking Numbers',
        help='Additional tracking numbers (one per line)'
    )

    route_ids = fields.One2many(
        'shipping.shipment.route',
        'shipment_id',
        string='Routes',
        help='Route stops for this shipment'
    )

    # ==================== SHIPPING INFORMATION ====================
    shipper_name = fields.Char(string='Shipper Name', tracking=True)
    shipper_company = fields.Char(string='Shipper Company')
    shipper_address = fields.Text(string='Shipper Address')
    shipper_address2 = fields.Char(string='Shipper Address 2')
    shipper_city = fields.Char(string='Shipper City')
    shipper_state_id = fields.Many2one('res.country.state', string='Shipper State')
    shipper_country_id = fields.Many2one('res.country', string='Shipper Country')
    shipper_zip = fields.Char(string='Shipper ZIP')
    shipper_phone = fields.Char(string='Shipper Phone')
    shipper_email = fields.Char(string='Shipper Email')

    recipient_name = fields.Char(string='Recipient Name', required=True, tracking=True)
    recipient_company = fields.Char(string='Recipient Company')
    recipient_address = fields.Text(string='Recipient Address', required=True)
    recipient_address2 = fields.Char(string='Recipient Address 2')
    recipient_city = fields.Char(string='Recipient City')
    recipient_state_id = fields.Many2one('res.country.state', string='Recipient State')
    recipient_country_id = fields.Many2one('res.country', string='Recipient Country')
    recipient_zip = fields.Char(string='Recipient ZIP')
    recipient_phone = fields.Char(string='Recipient Phone')
    recipient_email = fields.Char(string='Recipient Email')
    recipient_tax_id = fields.Char(string='Recipient Tax ID')

    # ==================== PACKAGE INFORMATION ====================
    total_weight = fields.Float(
        string='Total Weight (kg)',
        digits='Stock Weight',
        compute='_compute_package_info',
        store=True,
        help='Total weight of all packages'
    )
    total_volume = fields.Float(
        string='Total Volume (cm³)',
        compute='_compute_package_info',
        store=True,
        help='Total volume of all packages'
    )
    total_packages = fields.Integer(
        string='Number of Packages',
        default=1,
        compute='_compute_package_info',
        store=True,
        help='Total number of packages'
    )

    declared_value = fields.Monetary(
        string='Declared Value',
        currency_field='currency_id',
        tracking=True,
        help='Value declared for customs'
    )
    declared_currency_id = fields.Many2one(
        'res.currency',
        string='Declared Currency',
        default=lambda self: self.env.company.currency_id,
    )

    # ==================== FINANCIAL ====================
    shipping_cost = fields.Monetary(
        string='Shipping Cost',
        currency_field='currency_id',
        tracking=True,
        help='Total shipping cost'
    )
    base_cost = fields.Monetary(
        string='Base Cost',
        currency_field='currency_id',
        help='Base shipping cost before surcharges'
    )
    fuel_surcharge = fields.Monetary(
        string='Fuel Surcharge',
        currency_field='currency_id',
        help='Fuel surcharge applied'
    )
    residential_surcharge = fields.Monetary(
        string='Residential Surcharge',
        currency_field='currency_id',
    )
    saturday_surcharge = fields.Monetary(
        string='Saturday Surcharge',
        currency_field='currency_id',
    )
    insurance_cost = fields.Monetary(
        string='Insurance Cost',
        currency_field='currency_id',
    )
    cod_fee = fields.Monetary(
        string='COD Fee',
        currency_field='currency_id',
    )
    other_charges = fields.Monetary(
        string='Other Charges',
        currency_field='currency_id',
        help='Additional charges not otherwise categorized'
    )
    total_charges = fields.Monetary(
        string='Total Charges',
        currency_field='currency_id',
        compute='_compute_total_charges',
        store=True,
        help='Total of all shipping charges'
    )

    insurance_amount = fields.Monetary(
        string='Insurance Amount',
        currency_field='currency_id',
        help='Amount insured'
    )
    cod_amount = fields.Monetary(
        string='Cash on Delivery',
        currency_field='currency_id',
        help='COD amount to collect'
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
    )

    # ==================== DATES ====================
    pickup_date = fields.Datetime(
        string='Pickup Date',
        tracking=True,
        help='Scheduled pickup date/time'
    )
    pickup_ready_date = fields.Datetime(
        string='Ready for Pickup',
        help='Date/time shipment is ready for pickup'
    )
    delivery_date = fields.Datetime(
        string='Expected Delivery Date',
        tracking=True,
        help='Estimated delivery date'
    )
    committed_date = fields.Datetime(
        string='Committed Delivery Date',
        help='Committed delivery date from carrier'
    )
    shipped_date = fields.Datetime(
        string='Shipped Date',
        tracking=True,
        help='Date shipment was actually shipped'
    )
    in_transit_date = fields.Datetime(
        string='In Transit Date',
        help='Date shipment entered transit'
    )
    out_for_delivery_date = fields.Datetime(
        string='Out for Delivery Date',
        help='Date shipment was out for delivery'
    )
    delivered_date = fields.Datetime(
        string='Delivered Date',
        tracking=True,
        help='Date shipment was delivered'
    )
    exception_date = fields.Datetime(
        string='Exception Date',
        help='Date exception occurred'
    )

    # ==================== DELIVERY OPTIONS ====================
    signature_required = fields.Boolean(
        string='Signature Required',
        default=False,
        tracking=True,
        help='Require signature on delivery'
    )
    saturday_delivery = fields.Boolean(
        string='Saturday Delivery',
        default=False,
        tracking=True,
    )
    residential_delivery = fields.Boolean(
        string='Residential Delivery',
        default=True,
        tracking=True,
    )
    hold_at_location = fields.Boolean(
        string='Hold at Location',
        default=False,
        help='Hold for pickup at carrier location'
    )
    hold_location = fields.Char(
        string='Hold Location',
        help='Carrier location for pickup'
    )
    delivery_instructions = fields.Text(
        string='Delivery Instructions',
        help='Special instructions for delivery'
    )

    # ==================== INTERNATIONAL ====================
    is_international = fields.Boolean(
        string='International Shipment',
        compute='_compute_is_international',
        store=True,
        tracking=True,
    )
    customs_declaration_id = fields.Many2one(
        'shipping.customs.declaration',
        string='Customs Declaration',
        ondelete='restrict',
    )
    customs_info = fields.Text(
        string='Customs Information',
        help='Additional customs information'
    )
    export_type = fields.Selection([
        ('permanent', 'Permanent Export'),
        ('temporary', 'Temporary Export'),
        ('return', 'Return'),
        ('gift', 'Gift'),
        ('sample', 'Sample'),
        ('commercial', 'Commercial'),
    ], string='Export Type', default='commercial')
    incoterm = fields.Selection([
        ('EXW', 'EXW - Ex Works'),
        ('FCA', 'FCA - Free Carrier'),
        ('FAS', 'FAS - Free Alongside Ship'),
        ('FOB', 'FOB - Free On Board'),
        ('CFR', 'CFR - Cost and Freight'),
        ('CIF', 'CIF - Cost, Insurance and Freight'),
        ('CPT', 'CPT - Carriage Paid To'),
        ('CIP', 'CIP - Carriage and Insurance Paid To'),
        ('DPU', 'DPU - Delivered at Place Unloaded'),
        ('DAP', 'DAP - Delivered at Place'),
        ('DDP', 'DDP - Delivered Duty Paid'),
    ], string='Incoterm', default='CIF')

    # ==================== LABEL ====================
    label_pdf = fields.Binary(
        string='Shipping Label',
        attachment=True,
        help='PDF shipping label'
    )
    label_filename = fields.Char(string='Label Filename')
    label_format = fields.Selection([
        ('pdf', 'PDF'),
        ('zpl', 'ZPL'),
        ('png', 'PNG'),
    ], string='Label Format', default='pdf')
    label_generated_date = fields.Datetime(
        string='Label Generated Date',
        help='Date label was generated'
    )

    # ==================== RELATIONS ====================
    package_ids = fields.One2many(
        'shipping.shipment.package',
        'shipment_id',
        string='Packages',
        help='Packages in this shipment'
    )
    tracking_event_ids = fields.One2many(
        'shipping.tracking.event',
        'shipment_id',
        string='Tracking Events',
        help='Tracking history'
    )
    rate_ids = fields.One2many(
        'shipping.rate',
        'shipment_id',
        string='Rates',
        help='Available rates for this shipment'
    )
    selected_rate_id = fields.Many2one(
        'shipping.rate',
        string='Selected Rate',
        help='Rate selected for this shipment'
    )
    return_ids = fields.One2many(
        'shipping.return',
        'original_shipment_id',
        string='Returns',
        help='Return shipments associated with this shipment'
    )

    # ==================== METADATA ====================
    notes = fields.Text(string='Notes')
    internal_notes = fields.Text(string='Internal Notes')
    tags = fields.Many2many(
        'shipping.tag',
        string='Tags',
        help='Tags for categorization'
    )

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
    )

    created_by = fields.Many2one(
        'res.users',
        string='Created By',
        default=lambda self: self.env.user,
        readonly=True,
    )

    # ==================== COMPUTED FIELDS ====================
    last_tracking_status = fields.Char(
        string='Last Tracking Status',
        compute='_compute_last_tracking',
        store=True,
    )
    last_tracking_date = fields.Datetime(
        string='Last Tracking Update',
        compute='_compute_last_tracking',
        store=True,
    )
    days_in_transit = fields.Integer(
        string='Days in Transit',
        compute='_compute_days_in_transit',
        store=True,
        help='Number of days shipment has been in transit'
    )
    delivered_late = fields.Boolean(
        string='Delivered Late',
        compute='_compute_delivered_late',
        store=True,
        help='True if delivered after committed date'
    )

    # ==================== CONSTRAINTS ====================
    _sql_constraints = [
        ('unique_tracking', 'unique(tracking_number)', 'Tracking number must be unique!'),
        ('check_weight_positive', 'CHECK(total_weight >= 0)', 'Weight cannot be negative.'),
        ('check_value_positive', 'CHECK(declared_value >= 0)', 'Declared value cannot be negative.'),
    ]

    # ==================== COMPUTATION METHODS ====================

    @api.depends('recipient_country_id')
    def _compute_is_international(self):
        """Determine if shipment is international"""
        for shipment in self:
            if shipment.recipient_country_id and shipment.company_id.country_id:
                shipment.is_international = shipment.recipient_country_id.id != shipment.company_id.country_id.id
            else:
                shipment.is_international = False

    @api.depends('package_ids', 'package_ids.weight', 'package_ids.volume')
    def _compute_package_info(self):
        """Compute package statistics"""
        for shipment in self:
            if shipment.package_ids:
                shipment.total_weight = sum(shipment.package_ids.mapped('weight'))
                shipment.total_volume = sum(shipment.package_ids.mapped('volume'))
                shipment.total_packages = len(shipment.package_ids)
            else:
                shipment.total_weight = 0.0
                shipment.total_volume = 0.0
                shipment.total_packages = 0

    @api.depends('base_cost', 'fuel_surcharge', 'residential_surcharge',
                 'saturday_surcharge', 'insurance_cost', 'cod_fee', 'other_charges')
    def _compute_total_charges(self):
        """Compute total charges"""
        for shipment in self:
            shipment.total_charges = (
                    shipment.base_cost +
                    shipment.fuel_surcharge +
                    shipment.residential_surcharge +
                    shipment.saturday_surcharge +
                    shipment.insurance_cost +
                    shipment.cod_fee +
                    shipment.other_charges
            )

    @api.depends('tracking_event_ids', 'tracking_event_ids.event_date',
                 'tracking_event_ids.status_description')
    def _compute_last_tracking(self):
        """Compute last tracking status"""
        for shipment in self:
            if shipment.tracking_event_ids:
                last = shipment.tracking_event_ids.sorted('event_date', reverse=True)[:1]
                shipment.last_tracking_status = last.status_description
                shipment.last_tracking_date = last.event_date
            else:
                shipment.last_tracking_status = False
                shipment.last_tracking_date = False

    @api.depends('shipped_date', 'delivered_date')
    def _compute_days_in_transit(self):
        """Compute days in transit"""
        for shipment in self:
            if shipment.shipped_date and shipment.delivered_date:
                delta = shipment.delivered_date - shipment.shipped_date
                shipment.days_in_transit = delta.days
            else:
                shipment.days_in_transit = 0

    @api.depends('delivered_date', 'committed_date')
    def _compute_delivered_late(self):
        """Check if delivered late"""
        for shipment in self:
            if shipment.delivered_date and shipment.committed_date:
                shipment.delivered_late = shipment.delivered_date > shipment.committed_date
            else:
                shipment.delivered_late = False

    @api.depends('tracking_number', 'carrier_provider_id')
    def _compute_tracking_url(self):
        """Generate tracking URL"""
        for shipment in self:
            if shipment.tracking_number and shipment.carrier_provider_id:
                # Generic tracking URL pattern
                # TODO: Implement carrier-specific URL generation
                shipment.tracking_url = f"https://www.{shipment.carrier_provider_id.code.lower()}.com/track/{shipment.tracking_number}"
            else:
                shipment.tracking_url = False

    # ==================== ORM METHODS ====================

    @api.model
    def create(self, vals):
        """Create shipment with sequence"""
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('shipping.shipment') or _('New')

        # Auto-fill carrier account if not provided
        if not vals.get('carrier_account_id') and vals.get('carrier_provider_id'):
            provider = self.env['shipping.carrier.provider'].browse(vals['carrier_provider_id'])
            if provider:
                default_account = provider.account_ids.filtered('is_default')[:1]
                if default_account:
                    vals['carrier_account_id'] = default_account.id

        # Set shipper info from company if not provided
        if not vals.get('shipper_name') or not vals.get('shipper_address'):
            company = self.env.company
            if not vals.get('shipper_name'):
                vals['shipper_name'] = company.name
            if not vals.get('shipper_address'):
                vals['shipper_address'] = company.street or ''
                if company.street2:
                    vals['shipper_address'] += f"\n{company.street2}"
                if company.city:
                    vals['shipper_address'] += f"\n{company.city}"
                if company.country_id:
                    vals['shipper_address'] += f"\n{company.country_id.name}"

        shipment = super(ShippingShipment, self).create(vals)

        # Create default package if none
        if not vals.get('package_ids') and not vals.get('total_weight'):
            self.env['shipping.shipment.package'].create({
                'shipment_id': shipment.id,
                'name': _('Package 1'),
                'weight': 1.0,
                'package_type': 'box',
            })

        # Send creation notification
        shipment._send_creation_notification()

        return shipment

    def write(self, vals):
        """Update shipment with tracking"""
        result = super(ShippingShipment, self).write(vals)

        # If tracking number added, update tracking
        if vals.get('tracking_number'):
            for shipment in self:
                shipment._update_tracking_on_number_change()

        # If state changes to delivered, update delivered date
        if vals.get('state') == 'delivered':
            for shipment in self:
                if not shipment.delivered_date:
                    shipment.delivered_date = fields.Datetime.now()

        return result

    # ==================== ACTION METHODS ====================

    def action_confirm_shipment(self):
        """Confirm shipment"""
        self.ensure_one()
        if self.state == 'draft':
            self.state = 'confirmed'
            self.message_post(body=_('Shipment confirmed.'))
            self._send_confirmation_notification()

    def action_get_rates(self):
        """Get shipping rates"""
        self.ensure_one()
        # Create rate request wizard
        return {
            'type': 'ir.actions.act_window',
            'name': _('Rate Shopping'),
            'res_model': 'shipping.rate.request',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_shipment_id': self.id,
            },
        }

    def action_generate_label(self):
        """Generate shipping label"""
        self.ensure_one()

        if not self.tracking_number:
            raise UserError(_('Please get rates and select a carrier first.'))

        self.state = 'processing'

        try:
            # TODO: Implement actual label generation with carrier API
            # For demo, create a dummy PDF
            import tempfile
            from reportlab.pdfgen import canvas
            from io import BytesIO

            buffer = BytesIO()
            c = canvas.Canvas(buffer, pagesize=(400, 600))
            c.drawString(50, 550, f"SHIPPING LABEL")
            c.drawString(50, 520, f"Reference: {self.name}")
            c.drawString(50, 490, f"Carrier: {self.carrier_provider_id.name}")
            c.drawString(50, 460, f"Tracking: {self.tracking_number}")
            c.drawString(50, 430, f"Recipient: {self.recipient_name}")
            c.drawString(50, 400, f"Address: {self.recipient_address}")
            c.drawString(50, 370, f"Service: {self.service_type or 'Standard'}")
            c.drawString(50, 340, f"Weight: {self.total_weight} kg")
            c.drawString(50, 310, f"Packages: {self.total_packages}")
            c.drawString(50, 250, "BARCODE PLACEHOLDER")
            c.rect(50, 200, 300, 50)
            c.drawString(60, 225, "TRACKING NUMBER")
            c.drawString(60, 210, self.tracking_number)
            c.save()

            pdf_data = buffer.getvalue()
            buffer.close()

            self.label_pdf = base64.b64encode(pdf_data)
            self.label_filename = f"label_{self.name}_{self.tracking_number}.pdf"
            self.label_generated_date = fields.Datetime.now()
            self.state = 'label_generated'

            self.message_post(
                body=_('Shipping label generated successfully. Tracking: %s') % self.tracking_number,
                attachments=[(self.label_filename, self.label_pdf)]
            )

            self._send_label_notification()

            return {
                'type': 'ir.actions.act_window',
                'name': _('Shipment Label'),
                'res_model': 'shipping.shipment',
                'res_id': self.id,
                'view_mode': 'form',
                'target': 'current',
            }

        except Exception as e:
            self.state = 'exception'
            raise UserError(_('Failed to generate label: %s') % str(e))

    def action_mark_shipped(self):
        """Mark shipment as shipped"""
        self.ensure_one()
        if self.state in ['label_generated', 'processing']:
            self.state = 'shipped'
            self.shipped_date = fields.Datetime.now()
            self.message_post(body=_('Shipment marked as shipped.'))
            self._send_shipped_notification()

    def action_mark_in_transit(self):
        """Mark shipment as in transit"""
        self.ensure_one()
        if self.state == 'shipped':
            self.state = 'in_transit'
            self.in_transit_date = fields.Datetime.now()
            self.message_post(body=_('Shipment is in transit.'))

    def action_mark_delivered(self):
        """Mark shipment as delivered"""
        self.ensure_one()
        if self.state not in ['delivered', 'cancelled']:
            self.state = 'delivered'
            self.delivered_date = fields.Datetime.now()
            self.message_post(body=_('Shipment delivered.'))
            self._send_delivery_notification()

    def action_mark_exception(self):
        """Mark shipment with exception"""
        self.ensure_one()
        if self.state not in ['delivered', 'cancelled']:
            self.state = 'exception'
            self.exception_date = fields.Datetime.now()
            self.message_post(body=_('Shipment has an exception.'))
            self._send_exception_notification()

    def action_cancel(self):
        """Cancel shipment"""
        self.ensure_one()
        if self.state not in ['delivered', 'cancelled']:
            self.state = 'cancelled'
            self.message_post(body=_('Shipment cancelled.'))

    def action_update_tracking(self):
        """Manually update tracking"""
        self.ensure_one()
        if not self.tracking_number:
            raise UserError(_('No tracking number available.'))

        # TODO: Implement actual tracking update
        self._create_dummy_tracking_event()
        self.message_post(body=_('Tracking updated.'))

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Tracking Updated'),
                'message': _('Tracking information has been updated.'),
                'type': 'success',
                'sticky': False,
            }
        }

    def action_batch_labels(self):
        """Generate labels for multiple shipments"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Batch Label Generation'),
            'res_model': 'shipping.batch.label.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_shipment_ids': [(6, 0, self.ids)],
            },
        }

    def action_view_rates(self):
        """View rates for this shipment"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Shipping Rates'),
            'res_model': 'shipping.rate',
            'view_mode': 'tree,form',
            'domain': [('shipment_id', '=', self.id)],
        }

    def action_view_tracking(self):
        """View tracking events"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Tracking Events'),
            'res_model': 'shipping.tracking.event',
            'view_mode': 'tree,form',
            'domain': [('shipment_id', '=', self.id)],
        }

    def action_view_returns(self):
        """View returns for this shipment"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Returns'),
            'res_model': 'shipping.return',
            'view_mode': 'tree,form',
            'domain': [('original_shipment_id', '=', self.id)],
        }

    def action_create_return(self):
        """Create return for this shipment"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Create Return'),
            'res_model': 'shipping.return',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_original_shipment_id': self.id,
                'default_customer_id': self.recipient_id.id if hasattr(self, 'recipient_id') else False,
                'default_carrier_provider_id': self.carrier_provider_id.id,
                'default_carrier_account_id': self.carrier_account_id.id,
            },
        }

    # ==================== NOTIFICATION METHODS ====================

    def _send_creation_notification(self):
        """Send creation notification"""
        self.ensure_one()
        # TODO: Implement notification sending

    def _send_confirmation_notification(self):
        """Send confirmation notification"""
        self.ensure_one()
        # TODO: Implement notification sending

    def _send_label_notification(self):
        """Send label notification"""
        self.ensure_one()
        # TODO: Implement notification sending

    def _send_shipped_notification(self):
        """Send shipped notification"""
        self.ensure_one()
        # TODO: Implement notification sending

    def _send_delivery_notification(self):
        """Send delivery notification"""
        self.ensure_one()
        # TODO: Implement notification sending

    def _send_exception_notification(self):
        """Send exception notification"""
        self.ensure_one()
        # TODO: Implement notification sending

    # ==================== TRACKING METHODS ====================

    def _update_tracking_on_number_change(self):
        """Update tracking when tracking number changes"""
        self.ensure_one()
        if self.tracking_number:
            self._create_dummy_tracking_event()

    def _create_dummy_tracking_event(self):
        """Create a dummy tracking event for demo"""
        self.ensure_one()
        statuses = [
            ('Picked Up', True, False),
            ('In Transit', False, False),
            ('Processing', False, False),
            ('Arrived at Facility', False, False),
            ('Out for Delivery', False, False),
            ('Delivered', False, True),
        ]

        import random
        status, is_delivered, is_exception = random.choice(statuses)

        self.env['shipping.tracking.event'].create({
            'shipment_id': self.id,
            'tracking_number': self.tracking_number,
            'event_date': fields.Datetime.now(),
            'status_description': status,
            'location': f"{random.choice(['New York', 'Los Angeles', 'Chicago', 'Houston', 'Phoenix'])}",
            'is_delivered': is_delivered,
            'is_exception': is_exception,
        })

        if is_delivered:
            self.action_mark_delivered()
        elif is_exception:
            self.action_mark_exception()

    # ==================== CRON METHODS ====================

    @api.model
    def action_update_tracking(self):
        """Cron job to update tracking for all shipments"""
        shipments = self.search([
            ('state', 'in', ['shipped', 'in_transit', 'out_for_delivery']),
            ('tracking_number', '!=', False),
        ])

        for shipment in shipments:
            try:
                shipment.action_update_tracking()
            except Exception as e:
                _logger.error(f"Error updating tracking for {shipment.name}: {e}")

        _logger.info(f"Updated tracking for {len(shipments)} shipments")
        return True

    @api.model
    def action_cleanup_old_shipments(self):
        """Clean up old completed shipments"""
        cutoff_date = fields.Datetime.now() - timedelta(days=365)
        shipments = self.search([
            ('state', 'in', ['delivered', 'cancelled']),
            ('create_date', '<', cutoff_date),
        ])

        # Archive instead of delete
        shipments.write({'active': False})
        _logger.info(f"Archived {len(shipments)} old shipments")
        return True

    # ==================== HELPER METHODS ====================

    def get_tracking_status_display(self):
        """Get formatted tracking status for display"""
        self.ensure_one()
        status_map = {
            'draft': 'Draft',
            'confirmed': 'Confirmed',
            'processing': 'Processing',
            'label_generated': 'Label Generated',
            'shipped': 'Shipped',
            'in_transit': 'In Transit',
            'out_for_delivery': 'Out for Delivery',
            'delivered': 'Delivered ✓',
            'exception': 'Exception ⚠',
            'cancelled': 'Cancelled ✗',
        }
        return status_map.get(self.state, self.state)

    def get_tracking_status_color(self):
        """Get color for tracking status"""
        self.ensure_one()
        color_map = {
            'draft': 'text-muted',
            'confirmed': 'text-info',
            'processing': 'text-warning',
            'label_generated': 'text-warning',
            'shipped': 'text-primary',
            'in_transit': 'text-primary',
            'out_for_delivery': 'text-primary',
            'delivered': 'text-success',
            'exception': 'text-danger',
            'cancelled': 'text-danger',
        }
        return color_map.get(self.state, 'text-muted')
