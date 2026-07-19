# -*- coding: utf-8 -*-
"""
Main Controllers - Website and Portal routes
"""

from odoo import http, fields
from odoo.http import request
from odoo.addons.website.controllers.main import Website
from odoo.addons.portal.controllers.portal import CustomerPortal
import json
import logging

_logger = logging.getLogger(__name__)


class PropertyWebsite(Website):
    """Website controllers for property listings"""

    @http.route('/property', type='http', auth='public', website=True)
    def property_list(self, **kwargs):
        """Display property listings on the website"""
        properties = request.env['property.property'].search([
            ('website_published', '=', True),
            ('status', 'in', ['listed', 'under_offer']),
        ])

        # Apply filters if provided
        if kwargs.get('type'):
            properties = properties.filtered(lambda p: p.type == kwargs.get('type'))
        if kwargs.get('city'):
            properties = properties.filtered(lambda p: p.city and p.city.lower() == kwargs.get('city').lower())
        if kwargs.get('min_price'):
            properties = properties.filtered(lambda p: p.base_price >= float(kwargs.get('min_price')))
        if kwargs.get('max_price'):
            properties = properties.filtered(lambda p: p.base_price <= float(kwargs.get('max_price')))
        if kwargs.get('bedrooms'):
            properties = properties.filtered(lambda p: p.bedrooms >= int(kwargs.get('bedrooms')))

        values = {
            'properties': properties,
            'property_types': request.env['property.property']._fields['type'].selection,
            'cities': request.env['property.property'].search_read([], ['city'], groupby=['city']),
            'filters': kwargs,
        }
        return request.render('smart_property_lifecycle.website_property_list', values)

    @http.route('/property/<string:property_code>', type='http', auth='public', website=True)
    def property_detail(self, property_code, **kwargs):
        """Display property detail page"""
        property_obj = request.env['property.property']
        property_record = property_obj.search([('property_code', '=', property_code)], limit=1)

        if not property_record:
            return request.render('website.404')

        # Get related properties for suggestions
        similar_properties = property_obj.search([
            ('id', '!=', property_record.id),
            ('type', '=', property_record.type),
            ('city', '=', property_record.city),
            ('website_published', '=', True),
            ('status', 'in', ['listed', 'under_offer']),
        ], limit=4)

        # Get available viewings
        available_slots = request.env['property.viewing'].search([
            ('property_id', '=', property_record.id),
            ('status', 'in', ['scheduled', 'confirmed']),
            ('scheduled_time', '>=', fields.Datetime.now()),
        ], limit=5)

        values = {
            'property': property_record,
            'similar_properties': similar_properties,
            'available_slots': available_slots,
        }
        return request.render('smart_property_lifecycle.website_property_detail', values)

    @http.route('/property/search', type='json', auth='public', methods=['POST'])
    def property_search(self, **kwargs):
        """AJAX endpoint for property search"""
        domain = [('website_published', '=', True), ('status', 'in', ['listed', 'under_offer'])]

        if kwargs.get('search'):
            search_term = kwargs.get('search')
            domain.extend([
                '|', '|',
                ('name', 'ilike', search_term),
                ('city', 'ilike', search_term),
                ('property_code', 'ilike', search_term),
            ])

        if kwargs.get('type'):
            domain.append(('type', '=', kwargs.get('type')))

        if kwargs.get('min_price'):
            domain.append(('base_price', '>=', float(kwargs.get('min_price'))))

        if kwargs.get('max_price'):
            domain.append(('base_price', '<=', float(kwargs.get('max_price'))))

        properties = request.env['property.property'].search(domain)

        return {
            'count': len(properties),
            'properties': [{
                'id': p.id,
                'name': p.name,
                'property_code': p.property_code,
                'city': p.city,
                'base_price': p.base_price,
                'bedrooms': p.bedrooms,
                'bathrooms': p.bathrooms,
                'area_total': p.area_total,
                'image_url': p.image_256 and f'/web/image/property.property/{p.id}/image_256',
                'url': f'/property/{p.property_code}',
            } for p in properties]
        }


class PropertyPortal(CustomerPortal):
    """Portal controllers for tenants and owners"""

    def _prepare_home_portal_values(self, counters):
        """Add property counters to portal home"""
        values = super()._prepare_home_portal_values(counters)

        if request.env.user.partner_id:
            partner = request.env.user.partner_id

            # Count leases for tenant
            lease_count = request.env['property.lease'].search_count([
                ('tenant_id', '=', partner.id),
                ('status', 'in', ['signed', 'active']),
            ])
            values['lease_count'] = lease_count

            # Count maintenance requests
            maintenance_count = request.env['property.maintenance.request'].search_count([
                '|',
                ('requestor_id', '=', partner.id),
                ('lease_id.tenant_id', '=', partner.id),
            ])
            values['maintenance_count'] = maintenance_count

            # Count properties owned
            property_count = request.env['property.property'].search_count([
                ('owner_id', '=', partner.id),
            ])
            values['property_count'] = property_count

        return values

    @http.route(['/my/leases', '/my/leases/page/<int:page>'], type='http', auth='user', website=True)
    def portal_leases(self, page=1, search=None, **kwargs):
        """Display tenant's leases in portal"""
        values = self._prepare_portal_layout_values()

        domain = [('tenant_id', '=', request.env.user.partner_id.id)]

        if search:
            domain.append(('name', 'ilike', search))

        # Search leases
        lease_obj = request.env['property.lease']
        leases = lease_obj.search(domain, order='start_date desc')

        # Pagination
        pager = request.website.pager(
            url='/my/leases',
            total=len(leases),
            page=page,
            step=20,
            url_args={'search': search}
        )

        # Get the sliced records
        offset = pager['offset']
        # Use the step value from the pager or default to 20
        step = pager.get('limit', 20)
        sliced_leases = leases[offset:offset + step]

        values.update({
            'leases': sliced_leases,
            'pager': pager,
            'search': search,
        })

        return request.render('smart_property_lifecycle.portal_leases', values)

    @http.route('/my/leases/<int:lease_id>', type='http', auth='user', website=True)
    def portal_lease_detail(self, lease_id, **kwargs):
        """Display lease detail page in portal"""
        lease = request.env['property.lease'].browse(lease_id)

        if not lease.exists() or lease.tenant_id != request.env.user.partner_id:
            return request.render('website.404')

        values = {
            'lease': lease,
            'invoices': lease.invoice_ids,
            'maintenance_requests': lease.maintenance_ids,
        }
        return request.render('smart_property_lifecycle.portal_lease_detail', values)

    @http.route('/my/maintenance', type='http', auth='user', website=True)
    def portal_maintenance(self, **kwargs):
        """Display maintenance requests in portal"""
        partner = request.env.user.partner_id
        maintenance_requests = request.env['property.maintenance.request'].search([
            '|',
            ('requestor_id', '=', partner.id),
            ('lease_id.tenant_id', '=', partner.id),
        ], order='create_date desc')

        values = {
            'maintenance_requests': maintenance_requests,
        }
        return request.render('smart_property_lifecycle.portal_maintenance', values)

    @http.route('/my/maintenance/create', type='http', auth='user', website=True, methods=['GET', 'POST'])
    def portal_maintenance_create(self, **kwargs):
        """Create maintenance request from portal"""
        if request.httprequest.method == 'POST':
            try:
                maintenance_vals = {
                    'title': kwargs.get('title'),
                    'description': kwargs.get('description'),
                    'category': kwargs.get('category'),
                    'priority': kwargs.get('priority', 'medium'),
                    'requestor_id': request.env.user.partner_id.id,
                    'property_id': int(kwargs.get('property_id')),
                    'unit_id': int(kwargs.get('unit_id')) if kwargs.get('unit_id') else False,
                    'lease_id': int(kwargs.get('lease_id')) if kwargs.get('lease_id') else False,
                }
                maintenance = request.env['property.maintenance.request'].create(maintenance_vals)

                # Post success message
                return request.redirect(f'/my/maintenance/{maintenance.id}')
            except Exception as e:
                _logger.error(f"Error creating maintenance request: {e}")
                return request.redirect('/my/maintenance?error=1')

        # GET - Show form
        partner = request.env.user.partner_id
        leases = request.env['property.lease'].search([
            ('tenant_id', '=', partner.id),
            ('status', 'in', ['signed', 'active']),
        ])

        values = {
            'leases': leases,
            'categories': request.env['property.maintenance.request']._fields['category'].selection,
            'priorities': request.env['property.maintenance.request']._fields['priority'].selection,
        }
        return request.render('smart_property_lifecycle.portal_maintenance_form', values)

    @http.route('/my/maintenance/<int:maintenance_id>', type='http', auth='user', website=True)
    def portal_maintenance_detail(self, maintenance_id, **kwargs):
        """Display maintenance request detail"""
        maintenance = request.env['property.maintenance.request'].browse(maintenance_id)

        if not maintenance.exists():
            return request.render('website.404')

        # Check access
        partner = request.env.user.partner_id
        if (maintenance.requestor_id != partner and
                maintenance.lease_id.tenant_id != partner):
            return request.render('website.404')

        values = {
            'maintenance': maintenance,
        }
        return request.render('smart_property_lifecycle.portal_maintenance_detail', values)

    @http.route('/my/properties', type='http', auth='user', website=True)
    def portal_properties(self, **kwargs):
        """Display owned properties in portal"""
        properties = request.env['property.property'].search([
            ('owner_id', '=', request.env.user.partner_id.id),
        ])

        values = {
            'properties': properties,
        }
        return request.render('smart_property_lifecycle.portal_properties', values)


class PropertyIoTController(http.Controller):
    """Controller for IoT device management"""

    @http.route('/api/iot/devices', type='json', auth='public', methods=['GET'])
    def get_iot_devices(self, property_id=None, **kwargs):
        """Get IoT devices for a property"""
        if not property_id:
            return {'error': 'Property ID required'}

        devices = request.env['property.iot.device'].search([
            ('property_id', '=', int(property_id)),
        ])

        return {
            'devices': [{
                'id': d.id,
                'name': d.device_name,
                'type': d.device_type,
                'status': d.status,
                'battery_level': d.battery_level,
                'last_seen': d.last_seen.isoformat() if d.last_seen else None,
                'has_alert': d.has_alert,
            } for d in devices]
        }

    @http.route('/api/iot/device/<int:device_id>', type='json', auth='public', methods=['GET'])
    def get_iot_device(self, device_id, **kwargs):
        """Get IoT device details"""
        device = request.env['property.iot.device'].browse(device_id)

        if not device.exists():
            return {'error': 'Device not found'}

        return {
            'id': device.id,
            'name': device.device_name,
            'type': device.device_type,
            'status': device.status,
            'battery_level': device.battery_level,
            'last_seen': device.last_seen.isoformat() if device.last_seen else None,
            'location': device.location_description,
            'manufacturer': device.manufacturer,
            'model': device.model,
            'firmware_version': device.firmware_version,
            'has_alert': device.has_alert,
            'last_data': device.last_data,
        }

    @http.route('/api/iot/device/<int:device_id>/control', type='json', auth='public', methods=['POST'])
    def control_iot_device(self, device_id, **kwargs):
        """Send control command to IoT device"""
        device = request.env['property.iot.device'].browse(device_id)

        if not device.exists():
            return {'error': 'Device not found'}

        action = kwargs.get('action')
        params = kwargs.get('params', {})

        device.message_post(
            body=f"Command sent: {action} with params {params}",
            message_type='notification'
        )

        device.status = 'online'
        device.last_seen = fields.Datetime.now()

        return {
            'success': True,
            'message': f'Command {action} sent to {device.device_name}',
            'device_id': device_id,
        }
