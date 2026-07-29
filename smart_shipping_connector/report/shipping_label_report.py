from odoo import api, fields, models, _
import base64
from io import BytesIO
import logging

_logger = logging.getLogger(__name__)


class ShippingLabelReport(models.AbstractModel):
    """Shipping Label Report"""
    _name = 'report.smart_shipping_connector.shipping_label'
    _description = 'Shipping Label Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['shipping.shipment'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'shipping.shipment',
            'docs': docs,
            'data': data,
            'format_date': self._format_date,
            'format_currency': self._format_currency,
        }

    def _format_date(self, date):
        if not date:
            return 'N/A'
        return date.strftime('%B %d, %Y')

    def _format_currency(self, amount, currency):
        if not amount:
            return '0.00'
        return f"{amount:.2f} {currency.symbol if currency else ''}"


class CustomsDeclarationReport(models.AbstractModel):
    """Customs Declaration Report"""
    _name = 'report.smart_shipping_connector.customs_declaration'
    _description = 'Customs Declaration Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['shipping.customs.declaration'].browse(docids)
        return {
            'doc_ids': docids,
            'doc_model': 'shipping.customs.declaration',
            'docs': docs,
            'data': data,
            'format_date': self._format_date,
            'format_currency': self._format_currency,
        }

    def _format_date(self, date):
        if not date:
            return 'N/A'
        return date.strftime('%B %d, %Y')

    def _format_currency(self, amount, currency):
        if not amount:
            return '0.00'
        return f"{amount:.2f} {currency.symbol if currency else ''}"
