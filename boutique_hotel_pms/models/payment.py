from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import logging

_logger = logging.getLogger(__name__)


class HotelPayment(models.Model):
    _name = 'hotel.payment'
    _description = 'Hotel Payment'
    _order = 'payment_date desc, id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'display_name'

    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True,
        help='Complete display name'
    )
    name = fields.Char(
        string='Payment Reference',
        required=True,
        default='New',
        copy=False,
        help='Unique payment reference'
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
    partner_id = fields.Many2one(
        'res.partner',
        string='Guest',
        required=True,
        help='Guest making the payment'
    )
    reservation_id = fields.Many2one(
        'hotel.reservation',
        string='Reservation',
        help='Associated reservation'
    )
    folio_id = fields.Many2one(
        'hotel.folio',
        string='Folio',
        help='Associated folio'
    )
    invoice_id = fields.Many2one(
        'account.move',
        string='Invoice',
        help='Associated invoice'
    )

    # Payment Details
    payment_date = fields.Date(
        string='Payment Date',
        required=True,
        default=fields.Date.today,
        help='Date of payment'
    )
    amount = fields.Monetary(
        string='Amount',
        required=True,
        help='Payment amount'
    )
    payment_method = fields.Selection([
        ('cash', 'Cash'),
        ('credit_card', 'Credit Card'),
        ('debit_card', 'Debit Card'),
        ('bank_transfer', 'Bank Transfer'),
        ('online', 'Online Payment'),
        ('travel_agent', 'Travel Agent'),
        ('corporate', 'Corporate Account'),
        ('loyalty_points', 'Loyalty Points'),
        ('voucher', 'Voucher/Gift Card'),
        ('other', 'Other')
    ], string='Payment Method', required=True,
        help='Method of payment')
    payment_type = fields.Selection([
        ('deposit', 'Deposit'),
        ('partial', 'Partial Payment'),
        ('full', 'Full Payment'),
        ('refund', 'Refund'),
        ('adjustment', 'Adjustment')
    ], string='Payment Type', default='full',
        help='Type of payment')
    payment_status = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending'),
        ('authorized', 'Authorized'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', tracking=True,
        help='Current status of the payment')

    # Card Details (if applicable)
    card_type = fields.Selection([
        ('visa', 'Visa'),
        ('mastercard', 'Mastercard'),
        ('amex', 'American Express'),
        ('discover', 'Discover'),
        ('diners', 'Diners Club'),
        ('other', 'Other')
    ], string='Card Type',
        help='Type of card used')
    card_last4 = fields.Char(
        string='Card Last 4',
        size=4,
        help='Last 4 digits of card number'
    )
    card_holder = fields.Char(
        string='Card Holder Name',
        help='Name on card'
    )
    transaction_id = fields.Char(
        string='Transaction ID',
        help='Transaction ID from payment gateway'
    )
    authorization_code = fields.Char(
        string='Authorization Code',
        help='Authorization code from bank'
    )

    # Additional Information
    reference = fields.Char(
        string='Reference Number',
        help='Additional reference number'
    )
    notes = fields.Text(
        string='Notes',
        help='Additional notes about the payment'
    )
    receipt_sent = fields.Boolean(
        string='Receipt Sent',
        default=False,
        help='Whether receipt was sent to guest'
    )
    receipt_sent_date = fields.Datetime(
        string='Receipt Sent Date',
        help='Date and time receipt was sent'
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

    @api.constrains('amount')
    def _check_amount(self):
        for record in self:
            if record.amount <= 0:
                raise ValidationError('Payment amount must be greater than zero.')

    @api.constrains('card_last4')
    def _check_card_last4(self):
        for record in self:
            if record.card_last4 and len(record.card_last4) != 4:
                raise ValidationError('Last 4 digits must be exactly 4 characters.')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('hotel.payment') or 'New'
        return super().create(vals_list)

    def action_complete(self):
        for record in self:
            if record.payment_status != 'draft':
                raise UserError('Only draft payments can be completed.')
            record.payment_status = 'completed'
            record.message_post(body=_('Payment completed.'))

    def action_pending(self):
        for record in self:
            if record.payment_status != 'draft':
                raise UserError('Only draft payments can be marked as pending.')
            record.payment_status = 'pending'
            record.message_post(body=_('Payment marked as pending.'))

    def action_authorize(self):
        for record in self:
            if record.payment_status != 'pending':
                raise UserError('Only pending payments can be authorized.')
            record.payment_status = 'authorized'
            record.message_post(body=_('Payment authorized.'))

    def action_fail(self):
        for record in self:
            if record.payment_status not in ['pending', 'authorized']:
                raise UserError('Only pending or authorized payments can be failed.')
            record.payment_status = 'failed'
            record.message_post(body=_('Payment failed.'))

    def action_refund(self):
        for record in self:
            if record.payment_status not in ['completed', 'authorized']:
                raise UserError('Only completed or authorized payments can be refunded.')
            record.payment_status = 'refunded'
            record.message_post(body=_('Payment refunded.'))

    def action_cancel(self):
        for record in self:
            if record.payment_status in ['completed', 'refunded']:
                raise UserError('Cannot cancel a completed or refunded payment.')
            record.payment_status = 'cancelled'
            record.message_post(body=_('Payment cancelled.'))

    def action_send_receipt(self):
        self.ensure_one()
        template = self.env.ref('boutique_hotel_pms.email_template_payment_receipt', False)
        if template:
            template.send_mail(self.id, force_send=True)
            self.receipt_sent = True
            self.receipt_sent_date = fields.Datetime.now()
            self.message_post(body=_('Receipt sent to guest.'))
        return True

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

    def action_view_folio(self):
        self.ensure_one()
        if self.folio_id:
            return {
                'name': _('Folio'),
                'type': 'ir.actions.act_window',
                'res_model': 'hotel.folio',
                'view_mode': 'form',
                'res_id': self.folio_id.id,
                'target': 'current',
            }

    @api.model
    def get_daily_collection(self, date=None):
        """Get daily collection summary"""
        if not date:
            date = fields.Date.today()

        payments = self.search([
            ('payment_status', '=', 'completed'),
            ('payment_date', '=', date)
        ])

        return {
            'total_payments': len(payments),
            'total_amount': sum(payments.mapped('amount')),
            'by_method': {
                method: sum(payments.filtered(lambda p: p.payment_method == method).mapped('amount'))
                for method in dict(self._fields['payment_method'].selection).keys()
            },
            'payments': payments,
        }
    