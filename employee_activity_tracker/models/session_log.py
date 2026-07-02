# -*- coding: utf-8 -*-
###############################################################################
# Model: activity.tracker.session
# Purpose: Track every user session from login to logout with full details
###############################################################################

from odoo import models, fields, api, tools
from odoo.exceptions import AccessError
import logging
import datetime

_logger = logging.getLogger(__name__)


class ActivityTrackerSession(models.Model):
    """
    Stores complete session information for every user login.
    Tracks login time, logout time, IP address, browser, device,
    session duration, and current status.
    """
    _name = 'activity.tracker.session'
    _description = 'User Session Log'
    _order = 'login_datetime desc'
    _rec_name = 'display_name_computed'

    # -------------------------------------------------------------------------
    # Core Session Fields
    # -------------------------------------------------------------------------
    user_id = fields.Many2one(
        'res.users', string='User', required=True,
        ondelete='restrict', index=True
    )
    partner_id = fields.Many2one(
        related='user_id.partner_id', string='Partner', store=True
    )
    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.company
    )
    session_token = fields.Char(
        string='Session Token', index=True, copy=False
    )

    # -------------------------------------------------------------------------
    # Timing Fields
    # -------------------------------------------------------------------------
    login_datetime = fields.Datetime(
        string='Login Time', required=True,
        default=fields.Datetime.now, index=True
    )
    logout_datetime = fields.Datetime(
        string='Logout Time', index=True
    )
    last_activity = fields.Datetime(
        string='Last Activity', default=fields.Datetime.now, index=True
    )
    session_duration = fields.Float(
        string='Duration (hours)', compute='_compute_duration', store=True
    )
    idle_duration = fields.Float(
        string='Idle Time (hours)', compute='_compute_idle', store=False
    )

    # -------------------------------------------------------------------------
    # Network & Device Fields
    # -------------------------------------------------------------------------
    ip_address = fields.Char(string='IP Address', index=True)
    user_agent = fields.Text(string='User Agent')
    browser = fields.Char(string='Browser', compute='_compute_browser', store=True)
    operating_system = fields.Char(string='OS', compute='_compute_os', store=True)
    device_type = fields.Selection([
        ('desktop', 'Desktop'),
        ('mobile', 'Mobile'),
        ('tablet', 'Tablet'),
        ('api', 'API Client'),
        ('unknown', 'Unknown'),
    ], string='Device Type', compute='_compute_device_type', store=True)

    # -------------------------------------------------------------------------
    # Status Fields
    # -------------------------------------------------------------------------
    status = fields.Selection([
        ('active', 'Active'),
        ('idle', 'Idle'),
        ('logged_out', 'Logged Out'),
        ('expired', 'Expired'),
        ('forced_logout', 'Forced Logout'),
    ], string='Status', default='active', index=True)

    status_color = fields.Char(
        string='Status Color', compute='_compute_status_color'
    )
    status_icon = fields.Char(
        string='Status Icon', compute='_compute_status_icon'
    )

    # -------------------------------------------------------------------------
    # Activity Counts
    # -------------------------------------------------------------------------
    activity_count = fields.Integer(
        string='Activities', default=0
    )
    page_views = fields.Integer(
        string='Page Views', default=0
    )
    form_opens = fields.Integer(
        string='Forms Opened', default=0
    )
    records_created = fields.Integer(
        string='Records Created', default=0
    )
    records_modified = fields.Integer(
        string='Records Modified', default=0
    )
    records_deleted = fields.Integer(
        string='Records Deleted', default=0
    )

    # -------------------------------------------------------------------------
    # Location Data
    # -------------------------------------------------------------------------
    login_location = fields.Char(string='Login Location')
    display_name_computed = fields.Char(
        string='Session', compute='_compute_display_name_custom', store=True
    )

    # -------------------------------------------------------------------------
    # Computed Fields
    # -------------------------------------------------------------------------
    @api.depends('user_id', 'login_datetime')
    def _compute_display_name_custom(self):
        for rec in self:
            user = rec.user_id.name if rec.user_id else 'Unknown'
            dt = rec.login_datetime.strftime('%Y-%m-%d %H:%M') if rec.login_datetime else ''
            rec.display_name_computed = f"{user} — {dt}"

    @api.depends('login_datetime', 'logout_datetime', 'status')
    def _compute_duration(self):
        now = fields.Datetime.now()
        for rec in self:
            end = rec.logout_datetime or now
            if rec.login_datetime:
                delta = end - rec.login_datetime
                rec.session_duration = round(delta.total_seconds() / 3600, 2)
            else:
                rec.session_duration = 0.0

    @api.depends('last_activity', 'status')
    def _compute_idle(self):
        now = fields.Datetime.now()
        for rec in self:
            if rec.last_activity and rec.status == 'active':
                delta = now - rec.last_activity
                rec.idle_duration = round(delta.total_seconds() / 3600, 2)
            else:
                rec.idle_duration = 0.0

    @api.depends('user_agent')
    def _compute_browser(self):
        for rec in self:
            ua = rec.user_agent or ''
            if 'Edg/' in ua or 'Edge/' in ua:
                rec.browser = 'Microsoft Edge'
            elif 'Chrome/' in ua and 'Safari/' in ua:
                rec.browser = 'Google Chrome'
            elif 'Firefox/' in ua:
                rec.browser = 'Mozilla Firefox'
            elif 'Safari/' in ua and 'Chrome' not in ua:
                rec.browser = 'Safari'
            elif 'Opera/' in ua or 'OPR/' in ua:
                rec.browser = 'Opera'
            elif 'MSIE' in ua or 'Trident/' in ua:
                rec.browser = 'Internet Explorer'
            elif not ua:
                rec.browser = 'API/Script'
            else:
                rec.browser = 'Unknown'

    @api.depends('user_agent')
    def _compute_os(self):
        for rec in self:
            ua = rec.user_agent or ''
            if 'Windows NT 10.0' in ua:
                rec.operating_system = 'Windows 10/11'
            elif 'Windows NT 6.3' in ua:
                rec.operating_system = 'Windows 8.1'
            elif 'Windows' in ua:
                rec.operating_system = 'Windows'
            elif 'Mac OS X' in ua and 'iPhone' not in ua and 'iPad' not in ua:
                rec.operating_system = 'macOS'
            elif 'iPhone' in ua:
                rec.operating_system = 'iOS (iPhone)'
            elif 'iPad' in ua:
                rec.operating_system = 'iOS (iPad)'
            elif 'Android' in ua:
                rec.operating_system = 'Android'
            elif 'Linux' in ua:
                rec.operating_system = 'Linux'
            else:
                rec.operating_system = 'Unknown'

    @api.depends('user_agent')
    def _compute_device_type(self):
        for rec in self:
            ua = rec.user_agent or ''
            if 'iPhone' in ua or 'Android' in ua and 'Mobile' in ua:
                rec.device_type = 'mobile'
            elif 'iPad' in ua or 'Tablet' in ua:
                rec.device_type = 'tablet'
            elif not ua:
                rec.device_type = 'api'
            elif 'Windows' in ua or 'Mac OS X' in ua or 'Linux' in ua:
                rec.device_type = 'desktop'
            else:
                rec.device_type = 'unknown'

    @api.depends('status')
    def _compute_status_color(self):
        colors = {
            'active': '#22c55e',
            'idle': '#f59e0b',
            'logged_out': '#ef4444',
            'expired': '#6b7280',
            'forced_logout': '#dc2626',
        }
        for rec in self:
            rec.status_color = colors.get(rec.status, '#6b7280')

    @api.depends('status')
    def _compute_status_icon(self):
        icons = {
            'active': 'fa-circle text-success',
            'idle': 'fa-clock text-warning',
            'logged_out': 'fa-times-circle text-danger',
            'expired': 'fa-ban text-muted',
            'forced_logout': 'fa-exclamation-circle text-danger',
        }
        for rec in self:
            rec.status_icon = icons.get(rec.status, 'fa-question-circle')

    # -------------------------------------------------------------------------
    # Business Methods
    # -------------------------------------------------------------------------
    def action_force_logout(self):
        """Force terminate a session from the monitoring dashboard."""
        self.ensure_one()
        if not self.env.user.has_group('employee_activity_tracker.group_tracker_admin'):
            raise AccessError("Only administrators can force logout sessions.")
        self.write({
            'status': 'forced_logout',
            'logout_datetime': fields.Datetime.now(),
        })
        _logger.warning(
            "Session %s for user %s was force-terminated by %s",
            self.id, self.user_id.name, self.env.user.name
        )

    def action_mark_expired(self):
        """Mark sessions as expired based on inactivity threshold."""
        threshold_hours = int(
            self.env['ir.config_parameter'].sudo().get_param(
                'activity_tracker.session_timeout_hours', '8'
            )
        )
        threshold = fields.Datetime.now() - datetime.timedelta(hours=threshold_hours)
        expired_sessions = self.search([
            ('status', 'in', ['active', 'idle']),
            ('last_activity', '<', threshold),
        ])
        expired_sessions.write({
            'status': 'expired',
            'logout_datetime': fields.Datetime.now(),
        })
        _logger.info("Marked %d sessions as expired.", len(expired_sessions))

    def action_update_idle_status(self):
        """Mark sessions as idle based on inactivity threshold."""
        idle_threshold_minutes = int(
            self.env['ir.config_parameter'].sudo().get_param(
                'activity_tracker.idle_threshold_minutes', '15'
            )
        )
        idle_threshold = fields.Datetime.now() - datetime.timedelta(
            minutes=idle_threshold_minutes
        )
        idle_sessions = self.search([
            ('status', '=', 'active'),
            ('last_activity', '<', idle_threshold),
        ])
        idle_sessions.write({'status': 'idle'})

    @api.model
    def cron_cleanup_sessions(self):
        """Cron: Mark expired/idle sessions. Called every 15 minutes."""
        self.action_update_idle_status()
        self.action_mark_expired()

    @api.model
    def get_active_sessions_data(self):
        """Return data for the real-time dashboard."""
        active = self.search_count([('status', '=', 'active')])
        idle = self.search_count([('status', '=', 'idle')])
        offline = self.search_count([('status', 'in', ['logged_out', 'expired', 'forced_logout'])])
        total_users = self.env['res.users'].search_count([('active', '=', True)])
        today = fields.Date.today()
        sessions_today = self.search_count([
            ('login_datetime', '>=', str(today))
        ])
        return {
            'active': active,
            'idle': idle,
            'offline': offline,
            'total_users': total_users,
            'sessions_today': sessions_today,
        }

    # -------------------------------------------------------------------------
    # Security: Prevent normal users from deleting logs
    # -------------------------------------------------------------------------
    def unlink(self):
        if not self.env.user.has_group('employee_activity_tracker.group_tracker_admin'):
            raise AccessError("You are not allowed to delete session logs.")
        return super().unlink()

    @api.model
    def action_update_idle_status(self):
        """Mark sessions as idle based on inactivity threshold."""
        idle_threshold_minutes = int(
            self.env['ir.config_parameter'].sudo().get_param(
                'activity_tracker.idle_threshold_minutes', '15'
            )
        )
        idle_threshold = fields.Datetime.now() - datetime.timedelta(
            minutes=idle_threshold_minutes
        )
        idle_sessions = self.search([
            ('status', '=', 'active'),
            ('last_activity', '<', idle_threshold),
        ])
        idle_sessions.write({'status': 'idle'})
        return True

    @api.model
    def action_mark_expired(self):
        """Mark sessions as expired based on inactivity threshold."""
        threshold_hours = int(
            self.env['ir.config_parameter'].sudo().get_param(
                'activity_tracker.session_timeout_hours', '8'
            )
        )
        threshold = fields.Datetime.now() - datetime.timedelta(hours=threshold_hours)
        expired_sessions = self.search([
            ('status', 'in', ['active', 'idle']),
            ('last_activity', '<', threshold),
        ])
        expired_sessions.write({
            'status': 'expired',
            'logout_datetime': fields.Datetime.now(),
        })
        _logger.info("Marked %d sessions as expired.", len(expired_sessions))
        return True

    @api.model
    def cron_cleanup_sessions(self):
        """Cron: Mark expired/idle sessions. Called every 15 minutes."""
        self.action_update_idle_status()
        self.action_mark_expired()
        return True