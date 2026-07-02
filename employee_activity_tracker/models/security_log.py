# -*- coding: utf-8 -*-
###############################################################################
# Model: activity.tracker.security.log
# Purpose: Track security-sensitive events
###############################################################################

from odoo import models, fields, api
from odoo.exceptions import AccessError
import logging

_logger = logging.getLogger(__name__)


class ActivityTrackerSecurityLog(models.Model):
    """
    Tracks security-sensitive events:
    - Failed login attempts
    - Password changes
    - Group/permission changes
    - Access denied events
    - Developer mode activation
    """
    _name = 'activity.tracker.security.log'
    _description = 'Security Event Log'
    _order = 'event_datetime desc'
    _log_access = False

    event_type = fields.Selection([
        ('failed_login', 'Failed Login Attempt'),
        ('login', 'Successful Login'),
        ('logout', 'Logout'),
        ('password_change', 'Password Changed'),
        ('group_change', 'Permission Group Changed'),
        ('access_denied', 'Access Denied'),
        ('developer_mode_on', 'Developer Mode Enabled'),
        ('developer_mode_off', 'Developer Mode Disabled'),
        ('api_key_created', 'API Key Created'),
        ('api_key_deleted', 'API Key Deleted'),
        ('2fa_enabled', '2FA Enabled'),
        ('2fa_disabled', '2FA Disabled'),
        ('suspicious', 'Suspicious Activity'),
    ], string='Event Type', required=True, index=True)

    event_datetime = fields.Datetime(
        string='Date & Time', required=True,
        default=fields.Datetime.now, index=True
    )
    user_id = fields.Many2one(
        'res.users', string='User', ondelete='restrict', index=True
    )
    target_user_id = fields.Many2one(
        'res.users', string='Target User', ondelete='set null'
    )
    company_id = fields.Many2one(
        'res.company', string='Company', index=True
    )
    ip_address = fields.Char(string='IP Address', index=True)
    user_agent = fields.Text(string='User Agent')
    description = fields.Text(string='Description')
    severity = fields.Selection([
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('critical', 'Critical'),
    ], string='Severity', default='info', index=True)
    is_notified = fields.Boolean(string='Notified Admin', default=False)

    def unlink(self):
        if not self.env.user.has_group('employee_activity_tracker.group_tracker_admin'):
            raise AccessError("You are not allowed to delete security logs.")
        return super().unlink()

    @api.model
    def cron_check_suspicious_activity(self):
        """Cron job: Check for suspicious activity (failed logins)."""
        import datetime
        threshold = int(self.env['ir.config_parameter'].sudo().get_param(
            'activity_tracker.failed_login_threshold', '5'
        ))
        one_hour_ago = datetime.datetime.now() - datetime.timedelta(hours=1)

        # Group failed logins by IP
        failed_logins = self.sudo().read_group(
            [('event_type', '=', 'failed_login'), ('event_datetime', '>=', one_hour_ago)],
            ['ip_address', 'id:count'],
            ['ip_address']
        )

        for group in failed_logins:
            if group.get('ip_address_count', 0) >= threshold:
                ip = group['ip_address']
                count = group['ip_address_count']
                # Create suspicious activity log
                self.sudo().create({
                    'event_type': 'suspicious',
                    'ip_address': ip,
                    'description': f'{count} failed login attempts from {ip} in the last hour.',
                    'severity': 'critical',
                })
        return True
