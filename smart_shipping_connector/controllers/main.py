from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.exceptions import AccessError, MissingError
from datetime import datetime, timedelta
import json
import base64


class ShippingPortal(CustomerPortal):
    """Portal controller for shipping"""

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)

        if 'shipment_count' in counters:
            Shipment = request.env['shipping.shipment']
            values['shipment_count'] = Shipment.search_count([
                ('recipient_email', '=', request.env.user.partner_id.email)
            ])

        if 'return_count' in counters:
            Return = request.env['shipping.return']
            values['return_count'] = Return.search_count([
                ('customer_id', '=', request.env.user.partner_id.id)
            ])

        return values

    # ==================== SHIPMENT PORTAL ====================

    @http.route(['/my/shipments'], type='http', auth='user', website=True)
    def portal_my_shipments(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):
        """Display customer's shipments"""
        values = self._prepare_portal_layout_values()

        Shipment = request.env['shipping.shipment']
        domain = [
            ('recipient_email', '=', request.env.user.partner_id.email)
        ]

        # Date filters
        if date_begin:
            domain.append(('create_date', '>=', date_begin))
        if date_end:
            domain.append(('create_date', '<=', date_end))

        # Sort
        if sortby == 'date':
            order = 'create_date desc'
        elif sortby == 'status':
            order = 'state'
        elif sortby == 'name':
            order = 'name'
        else:
            order = 'create_date desc'

        shipments = Shipment.search(domain, order=order)

        values.update({
            'shipments': shipments,
            'page_name': 'shipments',
            'default_url': '/my/shipments',
        })

        return request.render('smart_shipping_connector.portal_my_shipments', values)

    @http.route(['/shipping/shipment/<int:shipment_id>'], type='http', auth='user', website=True)
    def portal_shipment_detail(self, shipment_id, **kw):
        """Display shipment detail"""
        Shipment = request.env['shipping.shipment']
        try:
            shipment = Shipment.browse(shipment_id)
            if not shipment.exists():
                return request.redirect('/my/shipments')

            # Check access
            if shipment.recipient_email != request.env.user.partner_id.email:
                return request.redirect('/my/shipments')

            # Get tracking events
            tracking_events = shipment.tracking_event_ids.sorted('event_date', reverse=True)

            # Get packages
            packages = shipment.package_ids

            return request.render('smart_shipping_connector.portal_shipment_detail', {
                'shipment': shipment,
                'tracking_events': tracking_events,
                'packages': packages,
                'format_date': self._format_date,
                'format_currency': self._format_currency,
            })
        except (AccessError, MissingError):
            return request.redirect('/my/shipments')

    # ==================== TRACKING PORTAL ====================

    @http.route(['/shipping/track/<string:tracking_number>'], type='http', auth='public', website=True)
    def public_track_shipment(self, tracking_number, **kw):
        """Public tracking page"""
        Shipment = request.env['shipping.shipment']
        shipment = Shipment.search([
            ('tracking_number', '=', tracking_number)
        ], limit=1)

        if not shipment:
            return request.render('smart_shipping_connector.tracking_not_found', {
                'tracking_number': tracking_number,
            })

        tracking_events = shipment.tracking_event_ids.sorted('event_date', reverse=True)

        return request.render('smart_shipping_connector.public_tracking', {
            'shipment': shipment,
            'tracking_events': tracking_events,
            'format_date': self._format_date,
        })

    @http.route(['/shipping/track'], type='http', auth='public', website=True)
    def public_tracking_form(self, **kw):
        """Public tracking form"""
        return request.render('smart_shipping_connector.tracking_form')

    # ==================== RETURN PORTAL ====================

    @http.route(['/my/returns'], type='http', auth='user', website=True)
    def portal_my_returns(self, **kw):
        """Display customer's returns"""
        Return = request.env['shipping.return']
        returns = Return.search([
            ('customer_id', '=', request.env.user.partner_id.id)
        ], order='create_date desc')

        return request.render('smart_shipping_connector.portal_my_returns', {
            'returns': returns,
            'page_name': 'returns',
        })

    @http.route(['/shipping/return/<int:return_id>'], type='http', auth='user', website=True)
    def portal_return_detail(self, return_id, **kw):
        """Display return detail"""
        Return = request.env['shipping.return']
        try:
            return_order = Return.browse(return_id)
            if not return_order.exists():
                return request.redirect('/my/returns')

            # Check access
            if return_order.customer_id.id != request.env.user.partner_id.id:
                return request.redirect('/my/returns')

            return request.render('smart_shipping_connector.portal_return_detail', {
                'return': return_order,
                'format_date': self._format_date,
                'format_currency': self._format_currency,
            })
        except (AccessError, MissingError):
            return request.redirect('/my/returns')

    # ==================== RETURN REQUEST ====================

    @http.route(['/shipping/return/request'], type='http', auth='user', website=True)
    def return_request_form(self, **kw):
        """Return request form"""
        return request.render('smart_shipping_connector.return_request_form')

    @http.route(['/shipping/return/request/submit'], type='http', auth='user', website=True, methods=['POST'])
    def return_request_submit(self, **post):
        """Submit return request"""
        # TODO: Implement return request submission
        return request.redirect('/my/returns')

    # ==================== SHIPMENT RATE SHOPPING ====================

    @http.route(['/shipping/shipment/<int:shipment_id>/rates'], type='json', auth='user')
    def get_shipment_rates(self, shipment_id, **kw):
        """Get rates for a shipment via AJAX"""
        Shipment = request.env['shipping.shipment']
        try:
            shipment = Shipment.browse(shipment_id)
            if not shipment.exists():
                return {'error': 'Shipment not found'}

            # Check access
            if shipment.recipient_email != request.env.user.partner_id.email:
                return {'error': 'Access denied'}

            # Get rates
            rates = shipment.rate_ids.sorted('total_cost')
            rate_data = []
            for rate in rates:
                rate_data.append({
                    'id': rate.id,
                    'service_name': rate.service_name,
                    'carrier': rate.carrier_provider_id.name,
                    'total_cost': rate.total_cost,
                    'currency': rate.currency_id.symbol,
                    'delivery_days': rate.delivery_days,
                    'delivery_date': rate.delivery_date.strftime('%Y-%m-%d') if rate.delivery_date else None,
                })

            return {
                'rates': rate_data,
                'shipment_name': shipment.name,
            }
        except Exception as e:
            return {'error': str(e)}

    # ==================== SHIPMENT TRACKING UPDATE ====================

    @http.route(['/shipping/tracking/update/<string:tracking_number>'], type='json', auth='user')
    def update_tracking_ajax(self, tracking_number, **kw):
        """Update tracking via AJAX"""
        Shipment = request.env['shipping.shipment']
        try:
            shipment = Shipment.search([
                ('tracking_number', '=', tracking_number)
            ], limit=1)

            if not shipment:
                return {'error': 'Shipment not found'}

            # Update tracking
            shipment.action_update_tracking()

            # Get latest events
            events = shipment.tracking_event_ids.sorted('event_date', reverse=True)[:10]
            event_data = []
            for event in events:
                event_data.append({
                    'date': event.event_date.strftime('%Y-%m-%d %H:%M'),
                    'status': event.status_description,
                    'location': event.location,
                    'is_delivered': event.is_delivered,
                    'is_exception': event.is_exception,
                })

            return {
                'success': True,
                'state': shipment.state,
                'events': event_data,
            }
        except Exception as e:
            return {'error': str(e)}

    # ==================== HELPER METHODS ====================

    def _format_date(self, date):
        """Format date for display"""
        if not date:
            return 'N/A'
        return date.strftime('%B %d, %Y at %I:%M %p')

    def _format_currency(self, amount, currency):
        """Format currency for display"""
        if not amount:
            return '0.00'
        return f"{amount:.2f} {currency.symbol if currency else ''}"
