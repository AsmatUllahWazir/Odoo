from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class HotelReservationReport(models.AbstractModel):
    _name = 'report.boutique_hotel_pms.report_hotel_reservation'
    _description = 'Reservation Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['hotel.reservation'].browse(docids)

        return {
            'doc_ids': docids,
            'doc_model': 'hotel.reservation',
            'docs': docs,
            'data': data,
            'get_company': self._get_company,
            'format_date': self._format_date,
            'format_amount': self._format_amount,
        }

    def _get_company(self):
        return self.env.company

    def _format_date(self, date):
        if date:
            return datetime.strftime(date, '%B %d, %Y')
        return ''

    def _format_amount(self, amount):
        return self.env.company.currency_id.format(amount)


class HotelFolioReport(models.AbstractModel):
    _name = 'report.boutique_hotel_pms.report_hotel_folio'
    _description = 'Folio Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['hotel.folio'].browse(docids)

        return {
            'doc_ids': docids,
            'doc_model': 'hotel.folio',
            'docs': docs,
            'data': data,
            'get_company': self._get_company,
            'format_date': self._format_date,
            'format_amount': self._format_amount,
            'get_service_lines': self._get_service_lines,
        }

    def _get_company(self):
        return self.env.company

    def _format_date(self, date):
        if date:
            return datetime.strftime(date, '%B %d, %Y')
        return ''

    def _format_amount(self, amount):
        return self.env.company.currency_id.format(amount)

    def _get_service_lines(self, folio):
        return folio.service_line_ids


class HotelOccupancyReport(models.AbstractModel):
    _name = 'report.boutique_hotel_pms.report_hotel_occupancy'
    _description = 'Occupancy Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        return {
            'doc_ids': docids,
            'doc_model': 'hotel.reservation',
            'data': data,
            'get_company': self._get_company,
            'format_date': self._format_date,
            'format_amount': self._format_amount,
            'get_occupancy_data': self._get_occupancy_data,
        }

    def _get_company(self):
        return self.env.company

    def _format_date(self, date):
        if date:
            return datetime.strftime(date, '%B %d, %Y')
        return ''

    def _format_amount(self, amount):
        return self.env.company.currency_id.format(amount)

    def _get_occupancy_data(self, date_from, date_to, room_type_id=None):
        domain = [
            ('state', 'in', ['checked_in', 'checked_out']),
            ('check_in', '>=', date_from),
            ('check_out', '<=', date_to)
        ]
        if room_type_id:
            domain.append(('room_ids.room_type_id', '=', room_type_id))

        reservations = self.env['hotel.reservation'].search(domain)

        occupancy_data = []
        current_date = date_from
        while current_date <= date_to:
            day_reservations = reservations.filtered(
                lambda r: r.check_in <= current_date and r.check_out > current_date
            )
            occupied = len(day_reservations.mapped('room_ids'))
            total_rooms = self.env['hotel.room'].search_count([('active', '=', True)])

            occupancy_data.append({
                'date': current_date,
                'occupied': occupied,
                'total': total_rooms,
                'occupancy_rate': (occupied / total_rooms * 100) if total_rooms > 0 else 0,
                'reservations': day_reservations,
            })
            current_date += timedelta(days=1)

        return occupancy_data
