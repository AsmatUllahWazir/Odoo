# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.http import request
import logging
import time

_logger = logging.getLogger(__name__)

# URL patterns to skip
SKIP_URL_PATTERNS = [
    '/longpolling/',
    '/web/webclient/version_info',
    '/web/dataset/call_kw/bus.bus',
    '/web/action/load',
    '/web/image/',
    '/web/static/',
    '/web/assets/',
    '/__debug__/',
    '/favicon.ico',
    '/mail/notify',
    '/discuss/channel/',
    '/web/service-worker.js',
    '/web/webclient/translations',
]


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def _dispatch(cls, endpoint):
        """Override dispatch to add timing and tracking."""
        start_time = time.time()
        response = super()._dispatch(endpoint)

        # Only track if we have a valid request and user
        if request and hasattr(request, 'session') and request.session.uid:
            try:
                path = request.httprequest.path or ''

                # Skip patterns
                if not any(pattern in path for pattern in SKIP_URL_PATTERNS):
                    if path.startswith('/web') or path.startswith('/odoo'):
                        env = request.env

                        # Update session if exists
                        active_session = env['activity.tracker.session'].sudo().search([
                            ('user_id', '=', request.session.uid),
                            ('status', 'in', ['active', 'idle']),
                        ], limit=1, order='login_datetime desc')

                        if active_session:
                            active_session.sudo().write({
                                'last_activity': fields.Datetime.now(),
                                'status': 'active',
                                'page_views': active_session.page_views + 1,
                            })
            except Exception as e:
                _logger.debug("HTTP tracking error: %s", e)

        return response
