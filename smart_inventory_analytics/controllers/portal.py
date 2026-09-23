# -*- coding: utf-8 -*-
from odoo import http, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager


class SmartInventoryPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'aging_count' in counters and request.env.user.has_group(
                'smart_inventory_analytics.group_smart_inventory_user'):
            values['aging_count'] = request.env['product.product'].sudo().search_count([
                ('type', 'in', ['product', 'consu']),
                ('qty_available', '>', 0),
                ('is_dead_stock', '=', True),
            ])
        return values

    @http.route(['/my/inventory/aging', '/my/inventory/aging/page/<int:page>'],
                type='http', auth='user', website=True)
    def portal_inventory_aging(self, page=1, sortby=None, filterby=None, **kw):
        if not request.env.user.has_group('smart_inventory_analytics.group_smart_inventory_user'):
            return request.redirect('/my')

        Product = request.env['product.product'].sudo()
        domain = [
            ('type', 'in', ['product', 'consu']),
            ('qty_available', '>', 0),
        ]

        searchbar_filters = {
            'all': {'label': _('All'), 'domain': []},
            'dead': {'label': _('Dead Stock'), 'domain': [('is_dead_stock', '=', True)]},
            'high_reorder': {'label': _('High Priority Reorder'),
                            'domain': [('reorder_priority', 'in', ['high', 'critical'])]},
        }
        if not filterby:
            filterby = 'all'
        domain += searchbar_filters[filterby]['domain']

        searchbar_sortings = {
            'score': {'label': _('Dead Stock Score'), 'order': 'dead_stock_score desc'},
            'days': {'label': _('Days Since Move'), 'order': 'days_since_last_move desc'},
            'value': {'label': _('Stock Value'), 'order': 'stock_value_aging desc'},
            'name': {'label': _('Name'), 'order': 'name'},
        }
        if not sortby:
            sortby = 'score'
        order = searchbar_sortings[sortby]['order']

        total = Product.search_count(domain)
        pager = portal_pager(
            url='/my/inventory/aging',
            total=total,
            page=page,
            step=20,
            url_args={'sortby': sortby, 'filterby': filterby},
        )
        products = Product.search(domain, order=order, limit=20, offset=pager['offset'])

        values = {
            'products': products,
            'page_name': 'inventory_aging',
            'pager': pager,
            'default_url': '/my/inventory/aging',
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
            'searchbar_filters': searchbar_filters,
            'filterby': filterby,
        }
        return request.render('smart_inventory_analytics.portal_inventory_aging', values)
