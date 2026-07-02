# -*- coding: utf-8 -*-
###############################################################################
# Model: res.users (inherited)
# Purpose: Intercept login/logout to create session records
###############################################################################

from odoo import models, fields, api
from odoo.exceptions import AccessError
import logging
import datetime

_logger = logging.getLogger(__name__)


class ResUsersInherit(models.Model):
    """
    Extend res.users to hook into authentication events.
    Creates session logs on login and closes them on logout.
    Also adds a computed online status badge for the dashboard.
    """
    _inherit = 'res.users'

    # -------------------------------------------------------------------------
    # Computed Fields for Dashboard Display
    # -------------------------------------------------------------------------
    tracker_session_status = fields.Char(
        string='Session Status',
        compute='_compute_tracker_status',
        help='Current session status: active, idle, offline'
    )
    tracker_last_login = fields.Datetime(
        string='Last Login',
        compute='_compute_tracker_status',
    )
    tracker_current_ip = fields.Char(
        string='Current IP',
        compute='_compute_tracker_status',
    )
    tracker_active_session_id = fields.Many2one(
        'activity.tracker.session',
        string='Active Session',
        compute='_compute_tracker_status',
    )
    tracker_session_count = fields.Integer(
        string='Total Sessions',
        compute='_compute_session_count',
    )
    tracker_activity_count = fields.Integer(
        string='Activities Today',
        compute='_compute_activity_count',
    )

    @api.depends()
    def _compute_tracker_status(self):
        for user in self:
            session = self.env['activity.tracker.session'].sudo().search([
                ('user_id', '=', user.id),
                ('status', 'in', ['active', 'idle']),
            ], limit=1, order='login_datetime desc')
            if session:
                user.tracker_session_status = session.status
                user.tracker_last_login = session.login_datetime
                user.tracker_current_ip = session.ip_address
                user.tracker_active_session_id = session
            else:
                user.tracker_session_status = 'offline'
                last_session = self.env['activity.tracker.session'].sudo().search([
                    ('user_id', '=', user.id),
                ], limit=1, order='login_datetime desc')
                user.tracker_last_login = last_session.login_datetime if last_session else False
                user.tracker_current_ip = ''
                user.tracker_active_session_id = self.env['activity.tracker.session']

    @api.depends()
    def _compute_session_count(self):
        for user in self:
            user.tracker_session_count = self.env['activity.tracker.session'].sudo().search_count([
                ('user_id', '=', user.id)
            ])

    @api.depends()
    def _compute_activity_count(self):
        today = fields.Date.today()
        for user in self:
            user.tracker_activity_count = self.env['activity.tracker.log'].sudo().search_count([
                ('user_id', '=', user.id),
                ('action_datetime', '>=', str(today)),
            ])

    def action_view_user_sessions(self):
        """Open session history for a specific user."""
        self.ensure_one()
        return {
            'name': f'Sessions – {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'activity.tracker.session',
            'view_mode': 'list,form',
            'domain': [('user_id', '=', self.id)],
            'context': {'default_user_id': self.id},
        }

    def action_view_user_activities(self):
        """Open activity timeline for a specific user."""
        self.ensure_one()
        return {
            'name': f'Activity Timeline – {self.name}',
            'type': 'ir.actions.act_window',
            'res_model': 'activity.tracker.log',
            'view_mode': 'list,form',
            'domain': [('user_id', '=', self.id)],
            'context': {'default_user_id': self.id},
        }


class ResUsersLoginHook(models.Model):
    """
    Hook into the HTTP session to track login/logout events.
    Extends the authenticate method.
    """
    _inherit = 'res.users'

    @classmethod
    def _login(cls, db, login, password, user_agent_env):
        """Override login to record session start."""
        uid = super()._login(db, login, password, user_agent_env)

        if uid:
            try:
                from odoo import registry
                from odoo.http import request
                env = api.Environment(
                    registry(db).cursor(), uid, {}
                )
                # Gather request metadata
                ip_address = ''
                user_agent = ''
                if request:
                    ip_address = request.httprequest.environ.get(
                        'HTTP_X_FORWARDED_FOR',
                        request.httprequest.environ.get('REMOTE_ADDR', '')
                    ).split(',')[0].strip()
                    user_agent = request.httprequest.user_agent.string or ''

                # Close any stale active sessions for this user
                stale = env['activity.tracker.session'].sudo().search([
                    ('user_id', '=', uid),
                    ('status', 'in', ['active', 'idle']),
                ])
                if stale:
                    stale.write({
                        'status': 'logged_out',
                        'logout_datetime': fields.Datetime.now(),
                    })

                # Create new session record
                session = env['activity.tracker.session'].sudo().create({
                    'user_id': uid,
                    'company_id': env.user.company_id.id,
                    'login_datetime': fields.Datetime.now(),
                    'ip_address': ip_address,
                    'user_agent': user_agent,
                    'status': 'active',
                    'last_activity': fields.Datetime.now(),
                })

                # Log the login activity
                env['activity.tracker.log'].sudo()._log_activity(
                    action_type='login',
                    summary=f"User logged in: {env.user.name}",
                    module_name='Authentication',
                    result='success',
                    ip_address=ip_address,
                )

                # Log security event
                env['activity.tracker.security.log'].sudo().create({
                    'event_type': 'login',
                    'user_id': uid,
                    'company_id': env.user.company_id.id,
                    'ip_address': ip_address,
                    'user_agent': user_agent,
                    'description': f"Successful login for {env.user.name} from {ip_address}",
                    'severity': 'info',
                })

                env.cr.commit()
            except Exception as e:
                _logger.warning("Session tracking error on login: %s", str(e))
        else:
            # Failed login attempt
            try:
                from odoo import registry
                from odoo.http import request
                from odoo.sql_db import db_connect
                cr = db_connect(db).cursor()
                env = api.Environment(cr, 1, {})  # Use admin for logging
                ip_address = ''
                user_agent = ''
                if request:
                    ip_address = request.httprequest.environ.get('REMOTE_ADDR', '')
                    user_agent = request.httprequest.user_agent.string or ''

                env['activity.tracker.security.log'].sudo().create({
                    'event_type': 'failed_login',
                    'ip_address': ip_address,
                    'user_agent': user_agent,
                    'description': f"Failed login attempt for '{login}' from {ip_address}",
                    'severity': 'warning',
                })
                cr.commit()
                cr.close()
            except Exception as e:
                _logger.debug("Failed login tracking error: %s", e)

        return uid