# -*- coding: utf-8 -*-
###############################################################################
# Controller: ActivityTrackerMain
# Purpose: HTTP endpoints for JavaScript client-side tracking calls
###############################################################################

import json
import logging
from datetime import datetime

from odoo import http, fields
from odoo.http import request, Response

_logger = logging.getLogger(__name__)


class ActivityTrackerMain(http.Controller):
    """
    REST endpoints called by the JavaScript tracking client.
    These endpoints receive events from the browser and store them
    in the appropriate log models.
    """

    # =========================================================================
    # Heartbeat — keep session alive and update status
    # =========================================================================
    @http.route(
        '/activity_tracker/heartbeat',
        type='json',
        auth='user',
        methods=['POST'],
        csrf=False,
    )
    def heartbeat(self, **kwargs):
        """
        Called every 60 seconds by the JS client to:
        1. Update session last_activity timestamp
        2. Mark session as active (not idle)
        3. Return current session info
        """
        try:
            uid = request.session.uid
            if not uid:
                return {'status': 'no_session'}

            active_session = request.env['activity.tracker.session'].sudo().search([
                ('user_id', '=', uid),
                ('status', 'in', ['active', 'idle']),
            ], limit=1, order='login_datetime desc')

            if active_session:
                active_session.write({
                    'last_activity': fields.Datetime.now(),
                    'status': 'active',
                })
                return {
                    'status': 'ok',
                    'session_id': active_session.id,
                    'duration': active_session.session_duration,
                }
            return {'status': 'no_active_session'}
        except Exception as e:
            _logger.debug("Heartbeat error: %s", e)
            return {'status': 'error', 'message': str(e)}

    # =========================================================================
    # Track client-side events (navigation, button clicks, etc.)
    # =========================================================================
    @http.route(
        '/activity_tracker/track_event',
        type='json',
        auth='user',
        methods=['POST'],
        csrf=False,
    )
    def track_event(self, event_type=None, data=None, **kwargs):
        """
        Receive events from the JavaScript client tracker.
        Handles: menu_access, form_open, button_click, view_change, etc.
        """
        if not event_type or not data:
            return {'status': 'missing_data'}
        try:
            uid = request.session.uid
            if not uid:
                return {'status': 'no_session'}

            env = request.env
            ip_address = request.httprequest.environ.get(
                'HTTP_X_FORWARDED_FOR',
                request.httprequest.environ.get('REMOTE_ADDR', '')
            ).split(',')[0].strip()

            active_session = env['activity.tracker.session'].sudo().search([
                ('user_id', '=', uid),
                ('status', 'in', ['active', 'idle']),
            ], limit=1, order='login_datetime desc')

            session_id = active_session.id if active_session else False

            if active_session:
                active_session.sudo().write({
                    'last_activity': fields.Datetime.now(),
                    'status': 'active',
                })

            # Map event types to log models
            if event_type == 'button_click':
                self._log_button_click(env, uid, session_id, data, ip_address)
            elif event_type in (
                'menu_access', 'form_open', 'list_view',
                'kanban_view', 'calendar_view', 'pivot_view', 'graph_view',
            ):
                self._log_navigation(env, uid, session_id, event_type, data, ip_address)
            elif event_type == 'logout':
                self._log_logout(env, uid, session_id, ip_address)
            elif event_type == 'developer_mode':
                self._log_developer_mode(env, uid, data, ip_address)

            return {'status': 'ok'}
        except Exception as e:
            _logger.debug("Event tracking error: %s", e)
            return {'status': 'error', 'message': str(e)}

    def _log_button_click(self, env, uid, session_id, data, ip_address):
        """Record a button click event."""
        env['activity.tracker.button.click'].sudo().create({
            'user_id': uid,
            'company_id': env.company.id,
            'session_id': session_id,
            'button_name': (data.get('button_name') or '')[:255],
            'button_method': (data.get('method') or '')[:255],
            'button_string': (data.get('string') or '')[:255],
            'model_name': (data.get('model') or '')[:255],
            'model_description': (data.get('model_description') or '')[:255],
            'record_id': data.get('res_id') or 0,
            'record_name': (data.get('record_name') or '')[:255],
            'module_name': (data.get('module') or '')[:255],
            'ip_address': ip_address,
            'result': data.get('result', 'success'),
            'result_message': (data.get('message') or '')[:1000],
        })
        env['activity.tracker.log'].sudo()._log_activity(
            action_type='button_click',
            summary=f"Button clicked: {data.get('string') or data.get('button_name', 'Unknown')}",
            model_name=data.get('model', ''),
            record_id=data.get('res_id') or 0,
            record_name=data.get('record_name', ''),
            module_name=data.get('module', ''),
            ip_address=ip_address,
        )

    def _log_navigation(self, env, uid, session_id, event_type, data, ip_address):
        """Record a navigation event (menu access, view open, etc.)."""
        env['activity.tracker.log'].sudo()._log_activity(
            action_type=event_type,
            summary=f"{event_type.replace('_', ' ').title()}: {data.get('name', '')}",
            model_name=data.get('model', ''),
            model_description=data.get('model_description', ''),
            module_name=data.get('module', ''),
            menu_name=data.get('menu_name', ''),
            view_type=data.get('view_type', ''),
            url_path=data.get('url', ''),
            ip_address=ip_address,
        )

    def _log_logout(self, env, uid, session_id, ip_address):
        """Record logout event and close session."""
        if session_id:
            session = env['activity.tracker.session'].sudo().browse(session_id)
            session.write({
                'status': 'logged_out',
                'logout_datetime': fields.Datetime.now(),
            })
        env['activity.tracker.log'].sudo()._log_activity(
            action_type='logout',
            summary=f"User logged out",
            module_name='Authentication',
            result='success',
            ip_address=ip_address,
        )

    def _log_developer_mode(self, env, uid, data, ip_address):
        """Record developer mode activation/deactivation."""
        is_enabled = data.get('enabled', False)
        event_type = 'developer_mode_on' if is_enabled else 'developer_mode_off'
        env['activity.tracker.security.log'].sudo().create({
            'event_type': event_type,
            'user_id': uid,
            'company_id': env.company.id,
            'ip_address': ip_address,
            'description': f"Developer mode {'enabled' if is_enabled else 'disabled'}",
            'severity': 'warning' if is_enabled else 'info',
        })

    # =========================================================================
    # Dashboard Data API
    # =========================================================================
    @http.route(
        '/activity_tracker/dashboard_data',
        type='json',
        auth='user',
        methods=['POST'],
    )
    def dashboard_data(self, **kwargs):
        """Return data for the real-time monitoring dashboard."""
        if not request.env.user.has_group('employee_activity_tracker.group_tracker_manager'):
            return {'error': 'Access denied'}

        env = request.env
        session_data = env['activity.tracker.session'].sudo().get_active_sessions_data()
        activity_data = env['activity.tracker.log'].sudo().get_today_stats()

        # Top 10 most active users today
        from odoo import fields as f
        today = f.Date.today()
        active_sessions = env['activity.tracker.session'].sudo().search([
            ('status', 'in', ['active', 'idle']),
        ], limit=20)

        online_users = []
        for session in active_sessions:
            online_users.append({
                'user_name': session.user_id.name,
                'status': session.status,
                'ip': session.ip_address,
                'duration': session.session_duration,
                'last_activity': session.last_activity.isoformat() if session.last_activity else '',
                'activity_count': session.activity_count,
                'browser': session.browser,
            })

        return {
            'sessions': session_data,
            'activities': activity_data,
            'online_users': online_users,
        }