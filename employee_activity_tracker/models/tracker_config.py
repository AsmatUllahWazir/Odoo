# -*- coding: utf-8 -*-
###############################################################################
# Model: activity.tracker.config
# Purpose: System-wide configuration for the tracking system
###############################################################################

from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class ActivityTrackerConfig(models.TransientModel):
    """Configuration settings for the Activity Tracker module."""
    _inherit = 'res.config.settings'

    # Session Settings
    tracker_session_timeout_hours = fields.Integer(
        string='Session Timeout (Hours)',
        config_parameter='activity_tracker.session_timeout_hours',
        default=8,
        help='Sessions inactive for this many hours will be marked expired.'
    )
    tracker_idle_threshold_minutes = fields.Integer(
        string='Idle Threshold (Minutes)',
        config_parameter='activity_tracker.idle_threshold_minutes',
        default=15,
        help='Sessions inactive for this many minutes will be marked idle.'
    )

    # Tracking Options
    tracker_enable_field_tracking = fields.Boolean(
        string='Enable Field Change Tracking',
        config_parameter='activity_tracker.enable_field_tracking',
        default=True,
    )
    tracker_enable_button_tracking = fields.Boolean(
        string='Enable Button Click Tracking',
        config_parameter='activity_tracker.enable_button_tracking',
        default=True,
    )
    tracker_enable_access_tracking = fields.Boolean(
        string='Enable URL/Menu Access Tracking',
        config_parameter='activity_tracker.enable_access_tracking',
        default=True,
    )

    # Excluded Models
    tracker_excluded_models = fields.Char(
        string='Excluded Models (comma-separated)',
        config_parameter='activity_tracker.excluded_models',
        default='mail.message,bus.bus,ir.logging',
        help='Technical model names to exclude from tracking.'
    )

    # Notification Settings
    tracker_alert_email = fields.Char(
        string='Alert Email (CEO/Admin)',
        config_parameter='activity_tracker.alert_email',
    )
    tracker_failed_login_threshold = fields.Integer(
        string='Failed Login Alert Threshold',
        config_parameter='activity_tracker.failed_login_threshold',
        default=5,
        help='Send alert after this many failed logins from same IP.'
    )
    tracker_send_daily_report = fields.Boolean(
        string='Send Daily Activity Report',
        config_parameter='activity_tracker.send_daily_report',
        default=True,
    )
    tracker_send_weekly_report = fields.Boolean(
        string='Send Weekly Productivity Report',
        config_parameter='activity_tracker.send_weekly_report',
        default=True,
    )

    # Retention Policy
    tracker_log_retention_days = fields.Integer(
        string='Log Retention (Days)',
        config_parameter='activity_tracker.log_retention_days',
        default=365,
        help='Logs older than this many days will be archived/deleted by cron.'
    )
    tracker_session_retention_days = fields.Integer(
        string='Session Retention (Days)',
        config_parameter='activity_tracker.session_retention_days',
        default=365,
    )


class ActivityTrackerSettings(models.Model):
    """
    Named configuration singleton for the tracker.
    Stores which models/modules to include or exclude.
    """
    _name = 'activity.tracker.config.model'
    _description = 'Tracker Model Configuration'
    _rec_name = 'model_name'

    model_name = fields.Char(string='Model Name', required=True, index=True)
    model_description = fields.Char(string='Description')
    is_excluded = fields.Boolean(string='Excluded from Tracking', default=False)
    track_fields = fields.Boolean(string='Track Field Changes', default=True)
    track_buttons = fields.Boolean(string='Track Button Clicks', default=True)
    track_crud = fields.Boolean(string='Track CRUD Operations', default=True)
    notes = fields.Text(string='Notes')

    _sql_constraints = [
        ('unique_model', 'UNIQUE(model_name)', 'Model name must be unique in tracker config.')
    ]