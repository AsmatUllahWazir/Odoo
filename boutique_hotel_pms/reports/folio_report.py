from odoo import models, api, _
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)


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
    