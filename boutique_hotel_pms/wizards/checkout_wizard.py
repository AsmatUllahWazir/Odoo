from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import logging

_logger = logging.getLogger(__name__)


class HotelCheckoutWizard(models.TransientModel):
    _name = 'hotel.checkout.wizard'
    _description = 'Check-out Wizard'

    reservation_id = fields.Many2one(
        'hotel.reservation',
        string='Reservation',
        required=True,
        help='Reservation to check out'
    )
    check_out_actual = fields.Datetime(
        string='Actual Check-out Time',
        required=True,
        default=fields.Datetime.now,
        help='Actual check-out time'
    )
    extra_charges = fields.Float(
        string='Extra Charges',
        help='Additional charges during stay'
    )
    extra_charges_description = fields.Text(
        string='Extra Charges Description',
        help='Description of extra charges'
    )
    payment_method = fields.Selection([
        ('cash', 'Cash'),
        ('card', 'Credit/Debit Card'),
        ('bank_transfer', 'Bank Transfer'),
        ('online', 'Online Payment'),
        ('corporate', 'Corporate'),
        ('other', 'Other')
    ], string='Payment Method',
        help='Payment method for settlement')
    notes = fields.Text(
        string='Notes',
        help='Additional notes about check-out'
    )
    total_amount = fields.Float(
        string='Total Amount',
        compute='_compute_total_amount',
        readonly=True,
        help='Total amount to be paid'
    )
    balance_due = fields.Float(
        string='Balance Due',
        compute='_compute_balance_due',
        readonly=True,
        help='Remaining balance'
    )

    @api.depends('reservation_id')
    def _compute_total_amount(self):
        for record in self:
            if record.reservation_id:
                record.total_amount = record.reservation_id.total_amount + record.extra_charges
            else:
                record.total_amount = 0

    @api.depends('reservation_id')
    def _compute_balance_due(self):
        for record in self:
            if record.reservation_id:
                record.balance_due = record.reservation_id.balance_due + record.extra_charges
            else:
                record.balance_due = 0

    @api.constrains('extra_charges')
    def _check_extra_charges(self):
        for record in self:
            if record.extra_charges < 0:
                raise ValidationError('Extra charges cannot be negative.')

    def action_check_out(self):
        self.ensure_one()

        # Add extra charges if any
        if self.extra_charges > 0 and self.reservation_id.folio_id:
            service_line_vals = {
                'folio_id': self.reservation_id.folio_id.id,
                'partner_id': self.reservation_id.partner_id.id,
                'service_id': self._get_extra_service_id(),
                'quantity': 1,
                'unit_price': self.extra_charges,
                'notes': self.extra_charges_description or 'Extra charges at checkout',
                'status': 'provided',
            }
            self.env['hotel.service.line'].create(service_line_vals)

        # Process check-out
        self.reservation_id.check_out_actual = self.check_out_actual
        self.reservation_id.action_check_out()

        # Register payment if needed
        if self.balance_due > 0 and self.payment_method:
            self._register_payment()

        return {
            'type': 'ir.actions.act_window',
            'name': _('Reservation'),
            'res_model': 'hotel.reservation',
            'view_mode': 'form',
            'res_id': self.reservation_id.id,
            'target': 'current',
        }

    def _get_extra_service_id(self):
        """Get or create extra service"""
        service = self.env['hotel.service'].search([
            ('code', '=', 'EXTRA'),
            ('active', '=', True)
        ], limit=1)

        if not service:
            service = self.env['hotel.service'].create({
                'name': 'Extra Charges',
                'code': 'EXTRA',
                'price': 0,
                'category': 'other',
                'description': 'Extra charges at checkout',
            })

        return service.id

    def _register_payment(self):
        """Register payment for remaining balance"""
        payment_vals = {
            'partner_id': self.reservation_id.partner_id.id,
            'reservation_id': self.reservation_id.id,
            'folio_id': self.reservation_id.folio_id.id,
            'amount': self.balance_due,
            'payment_method': self.payment_method,
            'payment_type': 'full',
            'payment_date': fields.Date.today(),
            'payment_status': 'completed',
            'notes': 'Check-out payment',
        }
        self.env['hotel.payment'].create(payment_vals)
        