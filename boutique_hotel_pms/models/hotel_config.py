from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class HotelConfigSettings(models.TransientModel):
    _name = 'hotel.config.settings'
    _description = 'Hotel Configuration Settings'
    _inherit = ['res.config.settings']

    # General Settings
    company_name = fields.Char(
        string='Hotel Name',
        related='company_id.name',
        readonly=False,
        help='Name of the hotel'
    )
    company_website = fields.Char(
        string='Hotel Website',
        related='company_id.website',
        readonly=False,
        help='Hotel website URL'
    )
    company_email = fields.Char(
        string='Hotel Email',
        related='company_id.email',
        readonly=False,
        help='Hotel email address'
    )
    company_phone = fields.Char(
        string='Hotel Phone',
        related='company_id.phone',
        readonly=False,
        help='Hotel phone number'
    )
    company_address = fields.Char(
        string='Hotel Address',
        related='company_id.street',
        readonly=False,
        help='Hotel address'
    )

    # Check-in/Check-out Settings
    default_checkin_time = fields.Char(
        string='Default Check-in Time',
        default='15:00',
        help='Default check-in time (e.g., 15:00 for 3 PM)'
    )
    default_checkout_time = fields.Char(
        string='Default Check-out Time',
        default='11:00',
        help='Default check-out time (e.g., 11:00 for 11 AM)'
    )
    early_checkin_allowed = fields.Boolean(
        string='Allow Early Check-in',
        default=False,
        help='Whether early check-in is allowed'
    )
    late_checkout_allowed = fields.Boolean(
        string='Allow Late Check-out',
        default=False,
        help='Whether late check-out is allowed'
    )
    early_checkin_charge = fields.Monetary(
        string='Early Check-in Charge',
        currency_field='currency_id',
        help='Charge for early check-in'
    )
    late_checkout_charge = fields.Monetary(
        string='Late Check-out Charge',
        currency_field='currency_id',
        help='Charge for late check-out'
    )

    # Tax and Financial Settings
    tax_percentage = fields.Float(
        string='Default Tax Rate (%)',
        default=10.0,
        help='Default tax rate applied to bookings'
    )
    service_charge_percentage = fields.Float(
        string='Service Charge (%)',
        default=0.0,
        help='Service charge percentage'
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id.id
    )

    # Booking Settings
    min_advance_booking_days = fields.Integer(
        string='Minimum Advance Booking (days)',
        default=1,
        help='Minimum days in advance for bookings'
    )
    max_advance_booking_days = fields.Integer(
        string='Maximum Advance Booking (days)',
        default=365,
        help='Maximum days in advance for bookings'
    )
    cancellation_policy = fields.Text(
        string='Cancellation Policy',
        default='Free cancellation up to 24 hours before check-in.',
        help='Hotel cancellation policy'
    )
    deposit_required = fields.Boolean(
        string='Deposit Required',
        default=False,
        help='Whether a deposit is required for bookings'
    )
    deposit_percentage = fields.Float(
        string='Deposit Percentage (%)',
        default=0.0,
        help='Deposit as percentage of total amount'
    )
    deposit_amount = fields.Monetary(
        string='Deposit Amount',
        currency_field='currency_id',
        help='Fixed deposit amount if applicable'
    )

    # Notification Settings
    send_confirmation_email = fields.Boolean(
        string='Send Confirmation Email',
        default=True,
        help='Whether to send confirmation emails'
    )
    send_reminder_emails = fields.Boolean(
        string='Send Reminder Emails',
        default=True,
        help='Whether to send reminder emails'
    )
    reminder_days = fields.Integer(
        string='Reminder Days Before Check-in',
        default=3,
        help='Days before check-in to send reminder'
    )
    send_folio_email = fields.Boolean(
        string='Send Folio Email',
        default=True,
        help='Whether to send folio emails after check-out'
    )
    send_payment_receipt = fields.Boolean(
        string='Send Payment Receipt',
        default=True,
        help='Whether to send payment receipts'
    )

    # Housekeeping Settings
    default_cleaning_time = fields.Float(
        string='Default Cleaning Time (hours)',
        default=1.0,
        help='Default time allocated for room cleaning'
    )
    inspection_required = fields.Boolean(
        string='Inspection Required',
        default=True,
        help='Whether room inspection is required after cleaning'
    )

    # Website Settings
    website_booking_enabled = fields.Boolean(
        string='Enable Website Booking',
        default=False,
        help='Whether to enable online booking via website'
    )
    website_booking_theme = fields.Selection([
        ('default', 'Default'),
        ('modern', 'Modern'),
        ('minimal', 'Minimal'),
        ('luxury', 'Luxury')
    ], string='Website Theme',
        default='default',
        help='Theme for the booking website')

    @api.depends('company_id')
    def _compute_currency_id(self):
        for record in self:
            record.currency_id = record.company_id.currency_id

    def get_values(self):
        res = super().get_values()
        config = self.env['ir.config_parameter'].sudo()

        res.update({
            'default_checkin_time': config.get_param('hotel.default_checkin_time', '15:00'),
            'default_checkout_time': config.get_param('hotel.default_checkout_time', '11:00'),
            'early_checkin_allowed': config.get_param('hotel.early_checkin_allowed', 'False') == 'True',
            'late_checkout_allowed': config.get_param('hotel.late_checkout_allowed', 'False') == 'True',
            'early_checkin_charge': float(config.get_param('hotel.early_checkin_charge', '0.0')),
            'late_checkout_charge': float(config.get_param('hotel.late_checkout_charge', '0.0')),
            'tax_percentage': float(config.get_param('hotel.tax_percentage', '10.0')),
            'service_charge_percentage': float(config.get_param('hotel.service_charge_percentage', '0.0')),
            'min_advance_booking_days': int(config.get_param('hotel.min_advance_booking_days', '1')),
            'max_advance_booking_days': int(config.get_param('hotel.max_advance_booking_days', '365')),
            'cancellation_policy': config.get_param('hotel.cancellation_policy',
                                                    'Free cancellation up to 24 hours before check-in.'),
            'deposit_required': config.get_param('hotel.deposit_required', 'False') == 'True',
            'deposit_percentage': float(config.get_param('hotel.deposit_percentage', '0.0')),
            'deposit_amount': float(config.get_param('hotel.deposit_amount', '0.0')),
            'send_confirmation_email': config.get_param('hotel.send_confirmation_email', 'True') == 'True',
            'send_reminder_emails': config.get_param('hotel.send_reminder_emails', 'True') == 'True',
            'reminder_days': int(config.get_param('hotel.reminder_days', '3')),
            'send_folio_email': config.get_param('hotel.send_folio_email', 'True') == 'True',
            'send_payment_receipt': config.get_param('hotel.send_payment_receipt', 'True') == 'True',
            'default_cleaning_time': float(config.get_param('hotel.default_cleaning_time', '1.0')),
            'inspection_required': config.get_param('hotel.inspection_required', 'True') == 'True',
            'website_booking_enabled': config.get_param('hotel.website_booking_enabled', 'False') == 'True',
            'website_booking_theme': config.get_param('hotel.website_booking_theme', 'default'),
        })
        return res

    def set_values(self):
        super().set_values()
        config = self.env['ir.config_parameter'].sudo()

        config.set_param('hotel.default_checkin_time', self.default_checkin_time or '15:00')
        config.set_param('hotel.default_checkout_time', self.default_checkout_time or '11:00')
        config.set_param('hotel.early_checkin_allowed', str(self.early_checkin_allowed))
        config.set_param('hotel.late_checkout_allowed', str(self.late_checkout_allowed))
        config.set_param('hotel.early_checkin_charge', str(self.early_checkin_charge or 0.0))
        config.set_param('hotel.late_checkout_charge', str(self.late_checkout_charge or 0.0))
        config.set_param('hotel.tax_percentage', str(self.tax_percentage or 10.0))
        config.set_param('hotel.service_charge_percentage', str(self.service_charge_percentage or 0.0))
        config.set_param('hotel.min_advance_booking_days', str(self.min_advance_booking_days or 1))
        config.set_param('hotel.max_advance_booking_days', str(self.max_advance_booking_days or 365))
        config.set_param('hotel.cancellation_policy', self.cancellation_policy or '')
        config.set_param('hotel.deposit_required', str(self.deposit_required))
        config.set_param('hotel.deposit_percentage', str(self.deposit_percentage or 0.0))
        config.set_param('hotel.deposit_amount', str(self.deposit_amount or 0.0))
        config.set_param('hotel.send_confirmation_email', str(self.send_confirmation_email))
        config.set_param('hotel.send_reminder_emails', str(self.send_reminder_emails))
        config.set_param('hotel.reminder_days', str(self.reminder_days or 3))
        config.set_param('hotel.send_folio_email', str(self.send_folio_email))
        config.set_param('hotel.send_payment_receipt', str(self.send_payment_receipt))
        config.set_param('hotel.default_cleaning_time', str(self.default_cleaning_time or 1.0))
        config.set_param('hotel.inspection_required', str(self.inspection_required))
        config.set_param('hotel.website_booking_enabled', str(self.website_booking_enabled))
        config.set_param('hotel.website_booking_theme', self.website_booking_theme or 'default')
