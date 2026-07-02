# -*- coding: utf-8 -*-
###############################################################################
# Controller: ActivityTrackerDashboard
# Purpose: Dashboard-specific API endpoints
###############################################################################

import logging
from odoo import http, fields
from odoo.http import request

_logger = logging.getLogger(__name__)


class ActivityTrackerDashboard(http.Controller):
    """API endpoints for the live monitoring dashboard."""

    @http.route(
        '/activity_tracker/live_stats',
        type='json',
        auth='user',
        methods=['POST'],
    )
    def live_stats(self, **kwargs):
        """Return real-time stats for dashboard widgets."""
        if not request.env.user.has_group('employee_activity_tracker.group_tracker_manager'):
            return {'error': 'Access denied'}

        env = request.env
        today = str(fields.Date.today())

        # Active sessions by status
        active_count = env['activity.tracker.session'].sudo().search_count([
            ('status', '=', 'active')
        ])
        idle_count = env['activity.tracker.session'].sudo().search_count([
            ('status', '=', 'idle')
        ])
        offline_count = env['activity.tracker.session'].sudo().search_count([
            ('status', 'in', ['logged_out', 'expired', 'forced_logout'])
        ])

        # Today's activity breakdown
        today_domain = [('action_datetime', '>=', today)]
        actions_today = env['activity.tracker.log'].sudo().search_count(today_domain)
        creates_today = env['activity.tracker.log'].sudo().search_count(
            today_domain + [('action_type', '=', 'create')]
        )
        writes_today = env['activity.tracker.log'].sudo().search_count(
            today_domain + [('action_type', '=', 'write')]
        )
        deletes_today = env['activity.tracker.log'].sudo().search_count(
            today_domain + [('action_type', '=', 'unlink')]
        )
        failed_logins = env['activity.tracker.security.log'].sudo().search_count([
            ('event_type', '=', 'failed_login'),
            ('event_datetime', '>=', today),
        ])

        # Activity by module (top 8)
        module_data = {}
        recent_logs = env['activity.tracker.log'].sudo().search(
            today_domain, limit=500
        )
        for log in recent_logs:
            module = log.module_name or 'Other'
            module_data[module] = module_data.get(module, 0) + 1

        module_sorted = sorted(module_data.items(), key=lambda x: x[1], reverse=True)[:8]

        # Recent critical security events
        security_events = env['activity.tracker.security.log'].sudo().search([
            ('severity', 'in', ['warning', 'critical']),
            ('event_datetime', '>=', today),
        ], limit=5, order='event_datetime desc')

        security_list = []
        for evt in security_events:
            security_list.append({
                'type': evt.event_type,
                'user': evt.user_id.name if evt.user_id else 'Unknown',
                'ip': evt.ip_address,
                'time': evt.event_datetime.isoformat() if evt.event_datetime else '',
                'severity': evt.severity,
                'description': evt.description or '',
            })

        # Top 5 most active users today
        user_activity = {}
        for log in recent_logs:
            uid = log.user_id.id
            name = log.user_id.name
            if uid not in user_activity:
                user_activity[uid] = {'name': name, 'count': 0}
            user_activity[uid]['count'] += 1

        top_users = sorted(
            user_activity.values(), key=lambda x: x['count'], reverse=True
        )[:5]

        return {
            'sessions': {
                'active': active_count,
                'idle': idle_count,
                'offline': offline_count,
                'total': active_count + idle_count + offline_count,
            },
            'activities': {
                'total': actions_today,
                'creates': creates_today,
                'writes': writes_today,
                'deletes': deletes_today,
                'failed_logins': failed_logins,
            },
            'modules': [{'name': k, 'count': v} for k, v in module_sorted],
            'security_alerts': security_list,
            'top_users': top_users,
        }