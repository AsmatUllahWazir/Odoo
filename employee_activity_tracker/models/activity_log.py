# -*- coding: utf-8 -*-
###############################################################################
# Model: activity.tracker.log
# Purpose: Central log for ALL user activities across the entire Odoo system
###############################################################################

from odoo import models, fields, api
from odoo.exceptions import AccessError
import logging

_logger = logging.getLogger(__name__)


class ActivityTrackerLog(models.Model):
    """
    Central activity log. Every significant user action is recorded here.
    This covers: CRUD operations, button clicks, workflow actions, menu access,
    report printing, imports/exports, API calls, and more.
    Uses batch-insert and indexing for performance.
    """
    _name = 'activity.tracker.log'
    _description = 'User Activity Log'
    _order = 'action_datetime desc'
    _rec_name = 'action_summary'
    _log_access = False  # Disable ORM logging on this model itself

    # -------------------------------------------------------------------------
    # Identity Fields
    # -------------------------------------------------------------------------
    user_id = fields.Many2one(
        'res.users', string='User', required=True,
        ondelete='restrict', index=True
    )
    company_id = fields.Many2one(
        'res.company', string='Company', index=True,
        default=lambda self: self.env.company
    )
    session_id = fields.Many2one(
        'activity.tracker.session', string='Session',
        ondelete='set null', index=True
    )

    # -------------------------------------------------------------------------
    # Action Classification
    # -------------------------------------------------------------------------
    action_type = fields.Selection([
        # CRUD
        ('create', 'Create Record'),
        ('write', 'Edit/Update Record'),
        ('unlink', 'Delete Record'),
        # Navigation
        ('menu_access', 'Menu Access'),
        ('form_open', 'Form Opened'),
        ('list_view', 'List View Access'),
        ('kanban_view', 'Kanban View Access'),
        ('calendar_view', 'Calendar View Access'),
        ('pivot_view', 'Pivot View Access'),
        ('graph_view', 'Graph View Access'),
        # Workflow
        ('button_click', 'Button Click'),
        ('workflow_action', 'Workflow Action'),
        ('approval', 'Approval'),
        ('status_change', 'Status Change'),
        # Documents
        ('report_print', 'Report Printed'),
        ('export', 'Data Export'),
        ('import', 'Data Import'),
        # System
        ('api_call', 'API Call'),
        ('scheduled_action', 'Scheduled Action'),
        ('portal_activity', 'Portal Activity'),
        ('developer_mode', 'Developer Mode Action'),
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('failed_login', 'Failed Login'),
        # Security
        ('permission_denied', 'Permission Denied'),
        ('password_change', 'Password Changed'),
        ('group_change', 'Group/Permission Change'),
        # Other
        ('other', 'Other'),
    ], string='Action Type', required=True, index=True)

    action_datetime = fields.Datetime(
        string='Date & Time', required=True,
        default=fields.Datetime.now, index=True
    )
    action_summary = fields.Char(
        string='Summary', required=True
    )
    action_detail = fields.Text(
        string='Detail'
    )

    # -------------------------------------------------------------------------
    # Target Resource
    # -------------------------------------------------------------------------
    model_name = fields.Char(
        string='Model', index=True,
        help='Technical name of the Odoo model (e.g., sale.order)'
    )
    model_description = fields.Char(
        string='Module/Object',
        help='Human-readable model description'
    )
    record_id = fields.Integer(
        string='Record ID', index=True
    )
    record_name = fields.Char(
        string='Record Name'
    )
    res_id = fields.Reference(
        lambda self: [(m.model, m.name) for m in self.env['ir.model'].search([], limit=100)],
        string='Record Reference'
    )

    # -------------------------------------------------------------------------
    # Module / Menu Context
    # -------------------------------------------------------------------------
    module_name = fields.Char(
        string='Odoo Module', index=True,
        help='Odoo module/application (e.g., Sale, Purchase, Inventory)'
    )
    menu_name = fields.Char(
        string='Menu Item'
    )
    view_type = fields.Char(
        string='View Type'
    )
    url_path = fields.Char(
        string='URL Path'
    )

    # -------------------------------------------------------------------------
    # Network Context
    # -------------------------------------------------------------------------
    ip_address = fields.Char(string='IP Address')
    is_api_call = fields.Boolean(string='Via API', default=False)

    # -------------------------------------------------------------------------
    # Result
    # -------------------------------------------------------------------------
    result = fields.Selection([
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('partial', 'Partial'),
        ('denied', 'Access Denied'),
    ], string='Result', default='success')

    error_message = fields.Text(string='Error Message')
    duration_ms = fields.Integer(
        string='Duration (ms)',
        help='Time taken to complete this action in milliseconds'
    )

    # -------------------------------------------------------------------------
    # Computed / Display
    # -------------------------------------------------------------------------
    action_type_icon = fields.Char(
        string='Icon', compute='_compute_action_icon'
    )
    color_index = fields.Integer(
        string='Color', compute='_compute_color'
    )

    @api.depends('action_type')
    def _compute_action_icon(self):
        icons = {
            'create': 'fa-plus-circle',
            'write': 'fa-edit',
            'unlink': 'fa-trash',
            'menu_access': 'fa-bars',
            'form_open': 'fa-file-alt',
            'list_view': 'fa-list',
            'kanban_view': 'fa-th-large',
            'button_click': 'fa-mouse-pointer',
            'workflow_action': 'fa-project-diagram',
            'approval': 'fa-check-circle',
            'status_change': 'fa-exchange-alt',
            'report_print': 'fa-print',
            'export': 'fa-file-export',
            'import': 'fa-file-import',
            'api_call': 'fa-code',
            'login': 'fa-sign-in-alt',
            'logout': 'fa-sign-out-alt',
            'failed_login': 'fa-exclamation-triangle',
            'permission_denied': 'fa-ban',
            'other': 'fa-circle',
        }
        for rec in self:
            rec.action_type_icon = icons.get(rec.action_type, 'fa-circle')

    @api.depends('action_type', 'result')
    def _compute_color(self):
        for rec in self:
            if rec.result == 'failed' or rec.result == 'denied':
                rec.color_index = 1  # Red
            elif rec.action_type in ['login', 'create', 'approval']:
                rec.color_index = 10  # Green
            elif rec.action_type in ['unlink']:
                rec.color_index = 9   # Orange/Red
            elif rec.action_type in ['failed_login', 'permission_denied']:
                rec.color_index = 1   # Red
            else:
                rec.color_index = 0   # Default

    # -------------------------------------------------------------------------
    # Helper: Create log entry (used by the tracking engine)
    # -------------------------------------------------------------------------
    @api.model
    def _log_activity(self, action_type, summary, **kwargs):
        """
        Central method to create activity log entries.
        Called by the tracking engine across all models and controllers.
        Uses sudo() to ensure logging works even for restricted users.
        """
        try:
            vals = {
                'user_id': self.env.uid,
                'company_id': self.env.company.id,
                'action_type': action_type,
                'action_summary': summary[:255] if summary else '',
                'ip_address': self._get_request_ip(),
            }
            vals.update(kwargs)
            # Find active session for this user
            active_session = self.env['activity.tracker.session'].sudo().search([
                ('user_id', '=', self.env.uid),
                ('status', 'in', ['active', 'idle']),
            ], limit=1, order='login_datetime desc')
            if active_session:
                vals['session_id'] = active_session.id
                active_session.sudo().write({'last_activity': fields.Datetime.now()})
                # Increment appropriate counter
                counter_field = {
                    'create': 'records_created',
                    'write': 'records_modified',
                    'unlink': 'records_deleted',
                    'form_open': 'form_opens',
                }.get(action_type, 'activity_count')
                active_session.sudo()[counter_field] += 1
            self.sudo().create(vals)
        except Exception as e:
            # Never let logging break the main operation
            _logger.debug("Activity logging failed silently: %s", str(e))

    @api.model
    def _get_request_ip(self):
        """Safely extract IP from current request."""
        try:
            from odoo.http import request
            if request:
                return request.httprequest.environ.get(
                    'HTTP_X_FORWARDED_FOR',
                    request.httprequest.environ.get('REMOTE_ADDR', '')
                ).split(',')[0].strip()
        except Exception:
            pass
        return ''

    # -------------------------------------------------------------------------
    # Statistics for Dashboard
    # -------------------------------------------------------------------------
    @api.model
    def get_today_stats(self):
        """Return today's activity statistics for the dashboard."""
        today = fields.Date.today()
        domain = [('action_datetime', '>=', str(today))]
        total = self.search_count(domain)
        creates = self.search_count(domain + [('action_type', '=', 'create')])
        writes = self.search_count(domain + [('action_type', '=', 'write')])
        deletes = self.search_count(domain + [('action_type', '=', 'unlink')])
        failed_logins = self.search_count(
            domain + [('action_type', '=', 'failed_login')]
        )
        return {
            'total_actions': total,
            'creates': creates,
            'writes': writes,
            'deletes': deletes,
            'failed_logins': failed_logins,
        }

    def unlink(self):
        if not self.env.user.has_group('employee_activity_tracker.group_tracker_admin'):
            raise AccessError("You are not allowed to delete activity logs.")
        return super().unlink()

    @api.model
    def cron_cleanup_logs(self):
        """Cron job: Clean up old logs based on retention policy."""
        import datetime
        retention_days = int(self.env['ir.config_parameter'].sudo().get_param(
            'activity_tracker.log_retention_days', '365'
        ))
        cutoff = datetime.datetime.now() - datetime.timedelta(days=retention_days)

        # Clean up activity logs
        old_logs = self.sudo().search([
            ('action_datetime', '<', cutoff)
        ])
        old_logs_count = len(old_logs)
        old_logs.sudo().unlink()

        # Clean up access logs
        old_access = self.env['activity.tracker.access.log'].sudo().search([
            ('access_datetime', '<', cutoff)
        ])
        old_access_count = len(old_access)
        old_access.sudo().unlink()

        # Clean up button click logs
        old_clicks = self.env['activity.tracker.button.click'].sudo().search([
            ('click_datetime', '<', cutoff)
        ])
        old_clicks_count = len(old_clicks)
        old_clicks.sudo().unlink()

        # Clean up security logs
        old_security = self.env['activity.tracker.security.log'].sudo().search([
            ('event_datetime', '<', cutoff)
        ])
        old_security_count = len(old_security)
        old_security.sudo().unlink()

        # Clean up field change logs
        old_fields = self.env['activity.tracker.field.change'].sudo().search([
            ('change_datetime', '<', cutoff)
        ])
        old_fields_count = len(old_fields)
        old_fields.sudo().unlink()

        _logger = logging.getLogger(__name__)
        _logger.info(
            'Activity Tracker Cleanup: Removed %d activity logs, %d access logs, %d button clicks, %d security logs, %d field changes',
            old_logs_count, old_access_count, old_clicks_count, old_security_count, old_fields_count
        )

        return True