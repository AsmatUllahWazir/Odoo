from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class HotelPaymentWizard(models.TransientModel):
    _name = 'hotel.payment.wizard'
    _description = 'Payment Wizard'

    partner_id = fields.Many2one(
        'res.partner',
        string='Guest',
        required=True,
        help='Guest making the payment'
    )
    folio_id = fields.Many2one(
        'hotel.folio',
        string='Folio',
        help='Associated folio'
    )
    reservation_id = fields.Many2one(
        'hotel.reservation',
        string='Reservation',
        help='Associated reservation'
    )
    amount = fields.Float(
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
        ('refund', 'Refund')
    ], string='Payment Type', default='full',
        help='Type of payment')
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
    transaction_id = fields.Char(
        string='Transaction ID',
        help='Transaction ID from payment gateway'
    )
    reference = fields.Char(
        string='Reference Number',
        help='Additional reference number'
    )
    notes = fields.Text(
        string='Notes',
        help='Additional notes'
    )
    balance_due = fields.Float(
        string='Balance Due',
        compute='_compute_balance_due',
        readonly=True,
        help='Remaining balance'
    )

    @api.depends('folio_id', 'reservation_id')
    def _compute_balance_due(self):
        for record in self:
            if record.folio_id:
                record.balance_due = record.folio_id.balance_due
            elif record.reservation_id:
                record.balance_due = record.reservation_id.balance_due
            else:
                record.balance_due = 0

    @api.constrains('amount')
    def _check_amount(self):
        for record in self:
            if record.amount <= 0:
                raise ValidationError('Amount must be greater than zero.')

    @api.constrains('card_last4')
    def _check_card_last4(self):
        for record in self:
            if record.card_last4 and len(record.card_last4) != 4:
                raise ValidationError('Last 4 digits must be exactly 4 characters.')

    def action_process_payment(self):
        self.ensure_one()

        payment_vals = {
            'partner_id': self.partner_id.id,
            'folio_id': self.folio_id.id if self.folio_id else False,
            'reservation_id': self.reservation_id.id if self.reservation_id else False,
            'amount': self.amount,
            'payment_method': self.payment_method,
            'payment_type': self.payment_type,
            'payment_date': fields.Date.today(),
            'payment_status': 'completed',
            'card_type': self.card_type,
            'card_last4': self.card_last4,
            'transaction_id': self.transaction_id,
            'reference': self.reference,
            'notes': self.notes,
        }

        payment = self.env['hotel.payment'].create(payment_vals)

        # Update folio or reservation
        if self.folio_id:
            self.folio_id.paid_amount += self.amount
            self.folio_id.message_post(
                body=_('Payment of %s received via %s') % (
                    self.amount, dict(self._fields['payment_method'].selection).get(self.payment_method)
                )
            )

        if self.reservation_id:
            self.reservation_id.paid_amount += self.amount

        # Send receipt
        payment.action_send_receipt()

        return {
            'type': 'ir.actions.act_window',
            'name': _('Payment'),
            'res_model': 'hotel.payment',
            'view_mode': 'form',
            'res_id': payment.id,
            'target': 'current',
        }
    