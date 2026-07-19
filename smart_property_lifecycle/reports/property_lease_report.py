# -*- coding: utf-8 -*-
"""
Property Lease Report - PDF generation for lease contracts
"""

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero
import base64
import logging
from datetime import datetime

_logger = logging.getLogger(__name__)


class PropertyLeaseReport(models.AbstractModel):
    """
    Abstract model for lease report generation
    """
    _name = 'report.smart_property_lifecycle.lease_contract'
    _description = 'Lease Contract Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        """Get report values for lease contract PDF"""
        docs = self.env['property.lease'].browse(docids)

        return {
            'doc_ids': docids,
            'doc_model': 'property.lease',
            'docs': docs,
            'data': data,
            'get_lease_details': self._get_lease_details,
            'get_payment_terms': self._get_payment_terms,
            'get_lease_terms': self._get_lease_terms,
        }

    def _get_lease_details(self, lease):
        """Get formatted lease details"""
        return {
            'lease_number': lease.name,
            'tenant_name': lease.tenant_id.name,
            'tenant_address': lease.tenant_id.street or '',
            'tenant_city': lease.tenant_id.city or '',
            'tenant_phone': lease.tenant_id.phone or '',
            'tenant_email': lease.tenant_id.email or '',
            'property_name': lease.property_id.name,
            'property_address': lease.property_id.full_address or '',
            'unit_number': lease.unit_id.unit_number if lease.unit_id else '',
            'start_date': lease.start_date,
            'end_date': lease.end_date,
            'term_months': lease.term_months,
            'rent_amount': lease.rent_amount,
            'deposit_amount': lease.deposit_amount,
            'rent_frequency': lease.rent_frequency,
            'currency_symbol': lease.currency_id.symbol or '$',
        }

    def _get_payment_terms(self, lease):
        """Get payment terms for lease"""
        terms = []
        if lease.rent_frequency == 'monthly':
            terms.append('Monthly rent of %s%s payable on the 1st of each month' % (
                lease.currency_id.symbol or '$', lease.rent_amount))
        elif lease.rent_frequency == 'quarterly':
            terms.append('Quarterly rent of %s%s payable on the 1st of each quarter' % (
                lease.currency_id.symbol or '$', lease.rent_amount * 3))

        if lease.late_fee_amount:
            terms.append('Late fee of %s%s applies after %s days grace period' % (
                lease.currency_id.symbol or '$', lease.late_fee_amount, lease.grace_period_days or 5))

        terms.append('Security deposit of %s%s required' % (
            lease.currency_id.symbol or '$', lease.deposit_amount))

        return terms

    def _get_lease_terms(self, lease):
        """Get lease terms and conditions"""
        return lease.terms_conditions or 'Standard lease terms and conditions apply.'


class PropertyPortfolioReport(models.AbstractModel):
    """
    Abstract model for portfolio report generation
    """
    _name = 'report.smart_property_lifecycle.portfolio_analytics'
    _description = 'Portfolio Analytics Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        """Get report values for portfolio analytics PDF"""
        docs = self.env['property.property'].browse(docids)

        return {
            'doc_ids': docids,
            'doc_model': 'property.property',
            'docs': docs,
            'data': data,
            'get_portfolio_summary': self._get_portfolio_summary,
            'get_property_stats': self._get_property_stats,
            'date_report': datetime.now().strftime('%B %d, %Y'),
        }

    def _get_portfolio_summary(self, properties):
        """Get portfolio summary statistics"""
        total_properties = len(properties)
        total_value = sum(p.base_price for p in properties)
        total_rent = sum(p.rental_price for p in properties)
        total_area = sum(p.area_total for p in properties)
        occupied = len(properties.filtered(lambda p: p.occupancy_rate > 0))

        return {
            'total_properties': total_properties,
            'total_value': total_value,
            'total_rent': total_rent,
            'total_area': total_area,
            'occupied_count': occupied,
            'vacant_count': total_properties - occupied,
            'occupancy_rate': (occupied / total_properties * 100) if total_properties > 0 else 0,
        }

    def _get_property_stats(self, property_record):
        """Get individual property statistics"""
        return {
            'name': property_record.name,
            'code': property_record.property_code,
            'type': property_record.type,
            'status': property_record.status,
            'city': property_record.city,
            'base_price': property_record.base_price,
            'dynamic_price': property_record.dynamic_price,
            'area': property_record.area_total,
            'bedrooms': property_record.bedrooms,
            'bathrooms': property_record.bathrooms,
            'occupancy_rate': property_record.occupancy_rate,
            'total_revenue': property_record.total_revenue,
            'next_maintenance': property_record.next_maintenance_date,
            'lease_count': len(property_record.lease_ids),
            'active_lease': property_record.active_lease_id.name if property_record.active_lease_id else False,
        }
    