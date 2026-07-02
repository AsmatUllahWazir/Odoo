# -*- coding: utf-8 -*-
###############################################################################
# Model: activity.tracker.access.log
# Purpose: Track menu access, model access, and URL visits
###############################################################################

from odoo import models, fields, api
from odoo.exceptions import AccessError
import logging

_logger = logging.getLogger(__name__)


class ActivityTrackerAccessLog(models.Model):
    """
    Tracks navigation/access events:
    - Menu clicks
    - URL visits
    - Model access
    - Report generation
    - Export/import operations
    """
    _name = 'activity.tracker.access.log'
    _description = 'Access Log'
    _order = 'access_datetime desc'
    _log_access = False

    user_id = fields.Many2one(
        'res.users', string='User', required=True,
        ondelete='restrict', index=True
    )
    company_id = fields.Many2one(
        'res.company', string='Company', index=True
    )
    session_id = fields.Many2one(
        'activity.tracker.session', string='Session', ondelete='set null'
    )
    access_datetime = fields.Datetime(
        string='Accessed At', required=True,
        default=fields.Datetime.now, index=True
    )

    # Access target
    access_type = fields.Selection([
        ('menu', 'Menu Access'),
        ('url', 'URL Visit'),
        ('model', 'Model Access'),
        ('report', 'Report Access'),
        ('export', 'Export'),
        ('import', 'Import'),
        ('api', 'API Access'),
        ('portal', 'Portal Access'),
        ('website', 'Website Access'),
    ], string='Access Type', required=True, index=True)

    menu_id = fields.Many2one('ir.ui.menu', string='Menu Item')
    menu_name = fields.Char(string='Menu Name')
    url_path = fields.Char(string='URL', index=True)
    model_name = fields.Char(string='Model', index=True)
    module_name = fields.Char(string='Module', index=True)
    ip_address = fields.Char(string='IP Address')
    http_method = fields.Char(string='HTTP Method')
    response_code = fields.Integer(string='Response Code')
    duration_ms = fields.Integer(string='Duration (ms)')

    def unlink(self):
        if not self.env.user.has_group('employee_activity_tracker.group_tracker_admin'):
            raise AccessError("You are not allowed to delete access logs.")
        return super().unlink()
    