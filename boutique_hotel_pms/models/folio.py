from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from odoo.tools import float_compare
import logging

_logger = logging.getLogger(__name__)


class HotelFolio(models.Model):
    _name = 'hotel.folio'
    _description = 'Hotel Folio'
    _order = 'id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'display_name'

    # Basic Information
    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True,
        help='Complete display name'
    )
    name = fields.Char(
        string='Folio Number',
        required=True,
        default='New',
        copy=False,
        help='Unique folio identifier (auto-generated)'
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id.id
    )

    # Linked Records
    reservation_id = fields.Many2one(
        'hotel.reservation',
        string='Reservation',
        required=True,
        ondelete='restrict',
        help='Associated reservation'
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Guest',
        required=True,
        help='Guest responsible for this folio'
    )
    room_ids = fields.Many2many(
        'hotel.room',
        string='Rooms',
        help='Rooms associated with this folio'
    )

    # Dates
    check_in = fields.Datetime(
        string='Check-in Date',
        required=True,
        help='Check-in date'
    )
    check_out = fields.Datetime(
        string='Check-out Date',
        required=True,
        help='Check-out date'
    )
    number_of_nights = fields.Integer(
        string='Number of Nights',
        compute='_compute_nights',
        store=True,
        help='Number of nights'
    )
    date_opened = fields.Datetime(
        string='Date Opened',
        default=fields.Datetime.now,
        help='Date the folio was opened'
    )
    date_settled = fields.Datetime(
        string='Date Settled',
        help='Date the folio was settled'
    )

    # State Management
    state = fields.Selection([
        ('draft', 'Draft'),
        ('open', 'Open'),
        ('settled', 'Settled'),
        ('cancelled', 'Cancelled'),
        ('overdue', 'Overdue')
    ], string='Status', required=True, default='draft', tracking=True,
        help='Current state of the folio')
    state_color = fields.Char(
        string='State Color',
        compute='_compute_state_color',
        help='Color for state display'
    )
    settlement_notes = fields.Text(
        string='Settlement Notes',
        help='Notes about settlement'
    )

    # Financials
    room_charges = fields.Monetary(
        string='Room Charges',
        compute='_compute_room_charges',
        store=True,
        help='Total room charges'
    )
    extra_charges = fields.Monetary(
        string='Extra Charges',
        compute='_compute_extra_charges',
        store=True,
        help='Total extra charges'
    )
    taxes = fields.Monetary(
        string='Taxes',
        compute='_compute_taxes',
        store=True,
        help='Total taxes'
    )
    total_amount = fields.Monetary(
        string='Total Amount',
        compute='_compute_total_amount',
        store=True,
        help='Total folio amount'
    )
    paid_amount = fields.Monetary(
        string='Paid Amount',
        default=0.0,
        tracking=True,
        help='Amount paid'
    )
    balance_due = fields.Monetary(
        string='Balance Due',
        compute='_compute_balance_due',
        store=True,
        help='Remaining balance'
    )
    discount_amount = fields.Monetary(
        string='Discount Amount',
        default=0.0,
        help='Discount applied to the folio'
    )
    discount_percentage = fields.Float(
        string='Discount Percentage',
        default=0.0,
        help='Discount percentage applied'
    )
    discount_reason = fields.Char(
        string='Discount Reason',
        help='Reason for discount'
    )
    tax_percentage = fields.Float(
        string='Tax Percentage',
        default=10.0,
        help='Tax percentage to apply'
    )
    service_charge = fields.Monetary(
        string='Service Charge',
        default=0.0,
        help='Service charge amount'
    )
    service_charge_percentage = fields.Float(
        string='Service Charge %',
        default=0.0,
        help='Service charge percentage'
    )

    # Payment Information
    payment_status = fields.Selection([
        ('unpaid', 'Unpaid'),
        ('partial', 'Partially Paid'),
        ('paid', 'Paid'),
        ('refunded', 'Refunded')
    ], string='Payment Status', default='unpaid', tracking=True,
        help='Current payment status')
    payment_method = fields.Selection([
        ('cash', 'Cash'),
        ('card', 'Credit/Debit Card'),
        ('bank_transfer', 'Bank Transfer'),
        ('online', 'Online Payment'),
        ('travel_agent', 'Travel Agent'),
        ('corporate', 'Corporate'),
        ('other', 'Other')
    ], string='Payment Method',
        help='Method of payment')
    payment_reference = fields.Char(
        string='Payment Reference',
        help='Reference number for payment'
    )
    payment_term = fields.Selection([
        ('immediate', 'Immediate'),
        ('upon_checkout', 'Upon Checkout'),
        ('15_days', '15 Days'),
        ('30_days', '30 Days')
    ], string='Payment Term', default='upon_checkout',
        help='Payment terms')

    # Service Lines
    service_line_ids = fields.One2many(
        'hotel.service.line',
        'folio_id',
        string='Service Lines',
        help='Extra services added to this folio'
    )
    service_line_count = fields.Integer(
        string='Service Count',
        compute='_compute_service_count',
        store=True,
        help='Number of service lines'
    )

    # Additional Fields
    notes = fields.Text(
        string='Notes',
        help='Additional notes about this folio'
    )
    internal_notes = fields.Text(
        string='Internal Notes',
        help='Internal notes visible only to staff'
    )
    created_by = fields.Many2one(
        'res.users',
        string='Created By',
        default=lambda self: self.env.user
    )
    created_date = fields.Datetime(
        string='Created Date',
        default=fields.Datetime.now
    )
    last_modified_by = fields.Many2one(
        'res.users',
        string='Last Modified By',
        tracking=True
    )
    last_modified_date = fields.Datetime(
        string='Last Modified Date',
        tracking=True
    )

    @api.depends('name', 'partner_id')
    def _compute_display_name(self):
        for record in self:
            if record.name and record.partner_id:
                record.display_name = f"{record.name} - {record.partner_id.name}"
            else:
                record.display_name = record.name or ''

    @api.depends('check_in', 'check_out')
    def _compute_nights(self):
        for record in self:
            if record.check_in and record.check_out:
                duration = record.check_out - record.check_in
                record.number_of_nights = duration.days if duration.days > 0 else 1
            else:
                record.number_of_nights = 1

    @api.depends('state')
    def _compute_state_color(self):
        state_colors = {
            'draft': 'secondary',
            'open': 'warning',
            'settled': 'success',
            'cancelled': 'danger',
            'overdue': 'danger'
        }
        for record in self:
            record.state_color = state_colors.get(record.state, 'secondary')

    @api.depends('reservation_id', 'reservation_id.total_amount')
    def _compute_room_charges(self):
        for record in self:
            if record.reservation_id:
                record.room_charges = record.reservation_id.total_amount
            else:
                record.room_charges = 0.0

    @api.depends('service_line_ids', 'service_line_ids.total_price')
    def _compute_extra_charges(self):
        for record in self:
            record.extra_charges = sum(record.service_line_ids.mapped('total_price'))

    @api.depends('total_amount', 'tax_percentage')
    def _compute_taxes(self):
        for record in self:
            record.taxes = record.total_amount * (record.tax_percentage / 100)

    @api.depends('room_charges', 'extra_charges', 'discount_amount', 'service_charge')
    def _compute_total_amount(self):
        for record in self:
            subtotal = record.room_charges + record.extra_charges
            total = subtotal - record.discount_amount + record.service_charge
            record.total_amount = total

    @api.depends('total_amount', 'paid_amount')
    def _compute_balance_due(self):
        for record in self:
            record.balance_due = record.total_amount - record.paid_amount

    @api.depends('service_line_ids')
    def _compute_service_count(self):
        for record in self:
            record.service_line_count = len(record.service_line_ids)

    @api.constrains('check_in', 'check_out')
    def _check_dates(self):
        for record in self:
            if record.check_in and record.check_out:
                if record.check_out <= record.check_in:
                    raise ValidationError('Check-out date must be after check-in date.')

    @api.constrains('paid_amount', 'total_amount')
    def _check_paid_amount(self):
        for record in self:
            if record.paid_amount < 0:
                raise ValidationError('Paid amount cannot be negative.')
            if record.paid_amount > record.total_amount and record.state != 'settled':
                raise ValidationError('Paid amount cannot exceed total amount.')

    @api.constrains('discount_amount')
    def _check_discount(self):
        for record in self:
            if record.discount_amount < 0:
                raise ValidationError('Discount amount cannot be negative.')
            if record.discount_amount > (record.room_charges + record.extra_charges):
                raise ValidationError('Discount amount cannot exceed total charges.')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('hotel.folio') or 'New'
        return super().create(vals_list)

    def action_open(self):
        for record in self:
            if record.state != 'draft':
                raise UserError('Only draft folios can be opened.')
            record.state = 'open'
            record.message_post(body=_('Folio opened.'))

    def action_settle(self):
        for record in self:
            if record.state != 'open':
                raise UserError('Only open folios can be settled.')

            # Check if balance is zero
            if record.balance_due > 0:
                raise UserError(
                    f'Cannot settle folio with balance due of {record.balance_due}. '
                    'Please register payment first.'
                )

            record.state = 'settled'
            record.date_settled = fields.Datetime.now()
            record.message_post(body=_('Folio settled.'))

    def action_cancel(self):
        for record in self:
            if record.state in ['settled']:
                raise UserError('Cannot cancel a settled folio.')
            record.state = 'cancelled'
            record.message_post(body=_('Folio cancelled.'))

    def action_register_payment(self):
        return {
            'name': _('Register Payment'),
            'type': 'ir.actions.act_window',
            'res_model': 'hotel.payment',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_folio_id': self.id,
                'default_partner_id': self.partner_id.id,
                'default_reservation_id': self.reservation_id.id,
                'default_amount': self.balance_due,
            }
        }

    def action_add_service(self):
        return {
            'name': _('Add Service'),
            'type': 'ir.actions.act_window',
            'res_model': 'hotel.service.line',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_folio_id': self.id,
                'default_partner_id': self.partner_id.id,
            }
        }

    def action_view_reservation(self):
        self.ensure_one()
        if self.reservation_id:
            return {
                'name': _('Reservation'),
                'type': 'ir.actions.act_window',
                'res_model': 'hotel.reservation',
                'view_mode': 'form',
                'res_id': self.reservation_id.id,
                'target': 'current',
            }

    def action_view_payments(self):
        self.ensure_one()
        return {
            'name': _('Payments'),
            'type': 'ir.actions.act_window',
            'res_model': 'hotel.payment',
            'view_mode': 'tree,form',
            'domain': [('folio_id', '=', self.id)],
            'target': 'current',
        }

    def action_print_folio(self):
        self.ensure_one()
        return self.env.ref('boutique_hotel_pms.action_report_hotel_folio').report_action(self)

    def _compute_folio_summary(self):
        """Compute summary data for the folio"""
        self.ensure_one()
        return {
            'room_charges': self.room_charges,
            'extra_charges': self.extra_charges,
            'taxes': self.taxes,
            'total_amount': self.total_amount,
            'paid_amount': self.paid_amount,
            'balance_due': self.balance_due,
        }

    @api.model
    def get_daily_summary(self, date=None):
        """Get daily folio summary"""
        if not date:
            date = fields.Date.today()

        folios = self.search([
            ('state', '=', 'settled'),
            ('date_settled', '>=', date),
            ('date_settled', '<', date + timedelta(days=1))
        ])

        return {
            'count': len(folios),
            'total_revenue': sum(folios.mapped('total_amount')),
            'total_paid': sum(folios.mapped('paid_amount')),
            'folios': folios,
        }

    def _send_folio_email(self):
        """Send folio to guest via email"""
        self.ensure_one()
        template = self.env.ref('boutique_hotel_pms.email_template_folio', False)
        if template:
            template.send_mail(self.id, force_send=True)
            self.message_post(body=_('Folio email sent to guest.'))
