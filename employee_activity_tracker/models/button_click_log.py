# -*- coding: utf-8 -*-
###############################################################################
# Model: activity.tracker.button.click
# Purpose: Track every significant button click / method call in Odoo
###############################################################################

from odoo import models, fields, api
from odoo.exceptions import AccessError
import logging

_logger = logging.getLogger(__name__)


class ActivityTrackerButtonClick(models.Model):
    """
    Tracks button clicks and server actions called from the frontend.
    Captures: confirm order, validate invoice, approve leave, etc.
    """
    _name = 'activity.tracker.button.click'
    _description = 'Button Click Log'
    _order = 'click_datetime desc'
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
    click_datetime = fields.Datetime(
        string='Clicked At', required=True,
        default=fields.Datetime.now, index=True
    )

    # Button details
    button_name = fields.Char(string='Button Name', required=True)
    button_method = fields.Char(string='Method Name')
    button_string = fields.Char(string='Button Label')

    # Target document
    model_name = fields.Char(string='Model', index=True)
    model_description = fields.Char(string='Object')
    record_id = fields.Integer(string='Record ID')
    record_name = fields.Char(string='Document')

    # Context
    module_name = fields.Char(string='Module')
    ip_address = fields.Char(string='IP Address')

    # Result
    result = fields.Selection([
        ('success', 'Success'),
        ('failed', 'Failed / Error'),
        ('denied', 'Access Denied'),
    ], string='Result', default='success')
    result_message = fields.Text(string='Result / Error')
    duration_ms = fields.Integer(string='Duration (ms)')

    def unlink(self):
        if not self.env.user.has_group('employee_activity_tracker.group_tracker_admin'):
            raise AccessError("You are not allowed to delete button click logs.")
        return super().unlink()
