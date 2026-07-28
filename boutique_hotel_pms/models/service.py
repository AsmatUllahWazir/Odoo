from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import logging

_logger = logging.getLogger(__name__)


class HotelService(models.Model):
    _name = 'hotel.service'
    _description = 'Hotel Service'
    _order = 'name'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'display_name'

    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True,
        help='Complete display name'
    )
    name = fields.Char(
        string='Service Name',
        required=True,
        translate=True,
        tracking=True,
        help='Name of the service (e.g., Breakfast, Laundry, Spa)'
    )
    code = fields.Char(
        string='Code',
        required=True,
        help='Short code for the service (e.g., BRKF, LAUN, SPA)'
    )
    category = fields.Selection([
        ('food_beverage', 'Food & Beverage'),
        ('wellness', 'Wellness & Spa'),
        ('transport', 'Transportation'),
        ('recreation', 'Recreation'),
        ('business', 'Business Services'),
        ('laundry', 'Laundry'),
        ('other', 'Other')
    ], string='Category', required=True, default='other',
        help='Category of service')
    description = fields.Text(
        string='Description',
        translate=True,
        help='Detailed description of the service'
    )
    long_description = fields.Html(
        string='Long Description',
        translate=True,
        help='Detailed description for website'
    )

    # Pricing
    price = fields.Monetary(
        string='Price',
        currency_field='currency_id',
        required=True,
        default=0.0,
        help='Price of this service'
    )
    price_type = fields.Selection([
        ('fixed', 'Fixed Price'),
        ('per_person', 'Per Person'),
        ('per_hour', 'Per Hour'),
        ('per_day', 'Per Day')
    ], string='Price Type', default='fixed',
        help='How the service is priced')
    tax_ids = fields.Many2many(
        'account.tax',
        string='Taxes',
        help='Taxes applicable to this service'
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id.id
    )

    # Availability
    available = fields.Boolean(
        string='Available',
        default=True,
        help='Whether this service is currently available'
    )
    available_from = fields.Date(
        string='Available From',
        help='Date from which this service is available'
    )
    available_to = fields.Date(
        string='Available To',
        help='Date until which this service is available'
    )
    time_slots = fields.Text(
        string='Time Slots',
        help='Available time slots (e.g., "8:00-10:00, 14:00-16:00")'
    )
    requires_booking = fields.Boolean(
        string='Requires Booking',
        default=False,
        help='Whether this service requires advance booking'
    )
    advance_booking_hours = fields.Integer(
        string='Advance Booking (hours)',
        default=24,
        help='Minimum hours advance booking required'
    )

    # Additional Fields
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company
    )
    active = fields.Boolean(
        string='Active',
        default=True,
        help='If unchecked, this service will be hidden'
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help='Order of display'
    )
    image = fields.Binary(
        string='Image',
        attachment=True,
        help='Image for the service'
    )
    notes = fields.Text(
        string='Notes',
        help='Additional notes about this service'
    )

    @api.depends('code', 'name')
    def _compute_display_name(self):
        for record in self:
            record.display_name = f"{record.code} - {record.name}"

    @api.constrains('price')
    def _check_price(self):
        for record in self:
            if record.price < 0:
                raise ValidationError('Price cannot be negative.')

    @api.constrains('code')
    def _check_code_unique(self):
        for record in self:
            existing = self.search([('code', '=', record.code), ('id', '!=', record.id)])
            if existing:
                raise ValidationError(f'Service code "{record.code}" must be unique!')

    @api.constrains('available_from', 'available_to')
    def _check_availability_dates(self):
        for record in self:
            if record.available_from and record.available_to:
                if record.available_to < record.available_from:
                    raise ValidationError('Available To date must be after Available From date.')

    def name_get(self):
        result = []
        for record in self:
            name = f"{record.code} - {record.name}"
            if record.price:
                name += f" ({record.price} {record.currency_id.symbol})"
            result.append((record.id, name))
        return result

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        domain = []
        if name:
            domain = ['|', ('name', operator, name), ('code', operator, name)]
        domain += args
        return self.search(domain, limit=limit).name_get()


class HotelServiceLine(models.Model):
    _name = 'hotel.service.line'
    _description = 'Hotel Service Line'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'display_name'

    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True,
        help='Complete display name'
    )
    folio_id = fields.Many2one(
        'hotel.folio',
        string='Folio',
        required=True,
        ondelete='cascade',
        help='Associated folio'
    )
    reservation_id = fields.Many2one(
        'hotel.reservation',
        string='Reservation',
        related='folio_id.reservation_id',
        store=True,
        help='Associated reservation'
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Guest',
        required=True,
        help='Guest who received this service'
    )
    service_id = fields.Many2one(
        'hotel.service',
        string='Service',
        required=True,
        help='Service provided'
    )
    service_code = fields.Char(
        string='Service Code',
        related='service_id.code',
        store=True,
        help='Service code'
    )
    service_category = fields.Selection(
        string='Service Category',
        related='service_id.category',
        store=True,
        help='Service category'
    )

    # Pricing
    quantity = fields.Float(
        string='Quantity',
        default=1.0,
        required=True,
        help='Quantity of the service'
    )
    unit_price = fields.Monetary(
        string='Unit Price',
        related='service_id.price',
        store=True,
        help='Price per unit'
    )
    total_price = fields.Monetary(
        string='Total Price',
        compute='_compute_total_price',
        store=True,
        help='Total price for this service line'
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        related='service_id.currency_id',
        store=True,
        help='Currency'
    )
    discount_amount = fields.Monetary(
        string='Discount Amount',
        default=0.0,
        help='Discount amount applied'
    )
    discount_percentage = fields.Float(
        string='Discount Percentage',
        default=0.0,
        help='Discount percentage applied'
    )
    net_price = fields.Monetary(
        string='Net Price',
        compute='_compute_net_price',
        store=True,
        help='Price after discount'
    )

    # Service Details
    date = fields.Date(
        string='Service Date',
        default=fields.Date.today,
        help='Date when the service was provided'
    )
    time = fields.Float(
        string='Service Time',
        help='Time when the service was provided'
    )
    duration = fields.Float(
        string='Duration (hours)',
        help='Duration of the service in hours'
    )
    notes = fields.Text(
        string='Notes',
        help='Additional notes about this service'
    )
    status = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('provided', 'Provided'),
        ('billed', 'Billed'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', tracking=True,
        help='Status of this service line')

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        related='folio_id.company_id',
        store=True,
        help='Company'
    )

    @api.depends('service_id', 'folio_id')
    def _compute_display_name(self):
        for record in self:
            if record.service_id and record.folio_id:
                record.display_name = f"{record.service_id.name} - {record.folio_id.name}"
            else:
                record.display_name = record.service_id.name or ''

    @api.depends('quantity', 'unit_price', 'discount_amount')
    def _compute_total_price(self):
        for record in self:
            total = record.quantity * record.unit_price
            record.total_price = total

    @api.depends('total_price', 'discount_amount')
    def _compute_net_price(self):
        for record in self:
            record.net_price = record.total_price - record.discount_amount

    @api.constrains('quantity')
    def _check_quantity(self):
        for record in self:
            if record.quantity <= 0:
                raise ValidationError('Quantity must be greater than zero.')

    @api.constrains('discount_amount')
    def _check_discount(self):
        for record in self:
            if record.discount_amount < 0:
                raise ValidationError('Discount amount cannot be negative.')
            if record.discount_amount > record.total_price:
                raise ValidationError('Discount amount cannot exceed total price.')

    def action_confirm(self):
        for record in self:
            record.status = 'confirmed'
            record.message_post(body=_('Service line confirmed.'))

    def action_provide(self):
        for record in self:
            record.status = 'provided'
            record.message_post(body=_('Service provided.'))

    def action_bill(self):
        for record in self:
            if record.status != 'provided':
                raise UserError('Only provided services can be billed.')
            record.status = 'billed'
            # Update folio total
            if record.folio_id:
                record.folio_id._compute_total_amount()
            record.message_post(body=_('Service billed.'))

    def action_cancel(self):
        for record in self:
            if record.status in ['provided', 'billed']:
                raise UserError('Cannot cancel a provided or billed service.')
            record.status = 'cancelled'
            record.message_post(body=_('Service line cancelled.'))

    @api.model
    def get_services_summary(self, date_from=None, date_to=None):
        """Get summary of services for a date range"""
        if not date_from:
            date_from = fields.Date.today() - timedelta(days=30)
        if not date_to:
            date_to = fields.Date.today()

        services = self.search([
            ('date', '>=', date_from),
            ('date', '<=', date_to),
            ('status', 'in', ['provided', 'billed'])
        ])

        summary = {}
        for service in services:
            if service.service_id.name not in summary:
                summary[service.service_id.name] = {
                    'quantity': 0,
                    'revenue': 0,
                }
            summary[service.service_id.name]['quantity'] += service.quantity
            summary[service.service_id.name]['revenue'] += service.total_price

        return summary
