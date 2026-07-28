from odoo import models, fields, api, _
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class HotelReportWizard(models.TransientModel):
    _name = 'hotel.report.wizard'
    _description = 'Report Wizard'

    report_type = fields.Selection([
        ('occupancy', 'Occupancy Report'),
        ('revenue', 'Revenue Report'),
        ('reservations', 'Reservations Report'),
        ('guest', 'Guest Report'),
        ('housekeeping', 'Housekeeping Report'),
        ('financial', 'Financial Report')
    ], string='Report Type', required=True,
        help='Type of report to generate')

    date_from = fields.Date(
        string='Date From',
        required=True,
        default=lambda self: fields.Date.today() - timedelta(days=30),
        help='Start date for report'
    )
    date_to = fields.Date(
        string='Date To',
        required=True,
        default=fields.Date.today,
        help='End date for report'
    )

    room_type_id = fields.Many2one(
        'hotel.room.type',
        string='Room Type',
        help='Filter by room type'
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Guest',
        help='Filter by guest'
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('checked_in', 'Checked In'),
        ('checked_out', 'Checked Out'),
        ('cancelled', 'Cancelled')
    ], string='Reservation Status',
        help='Filter by reservation status')

    format = fields.Selection([
        ('pdf', 'PDF'),
        ('xlsx', 'Excel'),
        ('csv', 'CSV')
    ], string='Format', required=True, default='pdf',
        help='Output format')

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for record in self:
            if record.date_from and record.date_to:
                if record.date_to < record.date_from:
                    raise ValidationError('End date must be after start date.')

    def action_generate_report(self):
        self.ensure_one()

        report_name = f'hotel_report_{self.report_type}'
        data = {
            'wizard_id': self.id,
            'report_type': self.report_type,
            'date_from': self.date_from,
            'date_to': self.date_to,
            'room_type_id': self.room_type_id.id if self.room_type_id else False,
            'partner_id': self.partner_id.id if self.partner_id else False,
            'state': self.state,
            'format': self.format,
        }

        return {
            'type': 'ir.actions.act_window',
            'name': _('Report'),
            'res_model': 'hotel.report.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': data,
        }
    