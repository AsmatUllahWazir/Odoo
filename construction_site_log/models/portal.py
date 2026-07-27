# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, AccessError
from odoo.addons.portal.controllers.portal import pager as portal_pager
import logging

_logger = logging.getLogger(__name__)


class ConstructionPortalAccess(models.Model):
    """
    Portal access management for construction site logs.
    """
    _name = 'construction.portal.access'
    _description = 'Portal Access Management'

    user_id = fields.Many2one(
        'res.users',
        string='User',
        required=True
    )

    partner_id = fields.Many2one(
        'res.partner',
        string='Partner',
        related='user_id.partner_id',
        store=True
    )

    project_ids = fields.Many2many(
        'project.project',
        'portal_access_project_rel',
        string='Allowed Projects',
        help='Projects this user can access via portal'
    )

    access_level = fields.Selection([
        ('view', 'View Only'),
        ('submit', 'Submit Logs'),
        ('approve', 'Approve Logs'),
        ('full', 'Full Access')
    ], string='Access Level',
        default='view')

    active = fields.Boolean(
        string='Active',
        default=True
    )

    notes = fields.Text(
        string='Notes'
    )

    @api.constrains('user_id')
    def _check_user(self):
        """Ensure user is portal user."""
        for record in self:
            if not record.user_id:
                raise ValidationError(_('User is required.'))
            if not record.user_id.partner_id:
                raise ValidationError(_('User must have a partner associated.'))


class ConstructionPortalLog(models.Model):
    """
    Portal view for construction logs.
    """
    _name = 'construction.portal.log'
    _description = 'Portal Log View'
    _inherit = ['mail.thread']

    daily_log_id = fields.Many2one(
        'construction.site.daily.log',
        string='Daily Log',
        required=True
    )

    portal_user_id = fields.Many2one(
        'res.users',
        string='Portal User',
        default=lambda self: self.env.user
    )

    access_token = fields.Char(
        string='Access Token',
        readonly=True,
        copy=False
    )

    view_count = fields.Integer(
        string='View Count',
        default=0
    )

    last_view_date = fields.Datetime(
        string='Last View Date'
    )

    is_shared = fields.Boolean(
        string='Is Shared',
        default=False
    )

    share_token = fields.Char(
        string='Share Token',
        readonly=True,
        copy=False
    )

    @api.model
    def generate_access_token(self):
        """Generate a unique access token."""
        import secrets
        return secrets.token_urlsafe(32)

    @api.model
    def create(self, vals):
        """Override create to generate access token."""
        if not vals.get('access_token'):
            vals['access_token'] = self.generate_access_token()
        return super().create(vals)

    def action_share(self):
        """Generate share link for the log."""
        self.ensure_one()
        if not self.share_token:
            self.write({'share_token': self.generate_access_token()})
        self.write({'is_shared': True})

        # Generate share URL
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        share_url = f"{base_url}/portal/daily_log/{self.id}?token={self.share_token}"

        return share_url

    def action_record_view(self):
        """Record a view of the log."""
        self.ensure_one()
        self.write({
            'view_count': self.view_count + 1,
            'last_view_date': fields.Datetime.now()
        })


class ConstructionPortalNotification(models.Model):
    """
    Portal notifications for construction logs.
    """
    _name = 'construction.portal.notification'
    _description = 'Portal Notification'
    _order = 'create_date desc'

    user_id = fields.Many2one(
        'res.users',
        string='User',
        required=True
    )

    message = fields.Text(
        string='Message',
        required=True
    )

    notification_type = fields.Selection([
        ('log_submitted', 'Log Submitted'),
        ('log_approved', 'Log Approved'),
        ('observation_created', 'Observation Created'),
        ('incident_reported', 'Incident Reported'),
        ('toolbox_talk', 'Toolbox Talk'),
        ('reminder', 'Reminder')
    ], string='Notification Type',
        required=True)

    read = fields.Boolean(
        string='Read',
        default=False
    )

    read_date = fields.Datetime(
        string='Read Date'
    )

    link = fields.Char(
        string='Link'
    )

    def action_mark_read(self):
        """Mark notification as read."""
        self.write({
            'read': True,
            'read_date': fields.Datetime.now()
        })

    def action_mark_unread(self):
        """Mark notification as unread."""
        self.write({
            'read': False,
            'read_date': False
        })


class ConstructionPortalSetting(models.Model):
    """
    Portal settings for construction module.
    """
    _name = 'construction.portal.setting'
    _description = 'Portal Settings'
    _rec_name = 'company_id'

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )

    allow_public_access = fields.Boolean(
        string='Allow Public Access',
        default=False
    )

    require_login = fields.Boolean(
        string='Require Login',
        default=True
    )

    auto_share_logs = fields.Boolean(
        string='Auto-Share Logs',
        default=True,
        help='Automatically share logs with project stakeholders'
    )

    notification_enabled = fields.Boolean(
        string='Enable Notifications',
        default=True
    )

    email_notifications = fields.Boolean(
        string='Email Notifications',
        default=True
    )

    sms_notifications = fields.Boolean(
        string='SMS Notifications',
        default=False
    )

    theme = fields.Selection([
        ('light', 'Light'),
        ('dark', 'Dark')
    ], string='Theme',
        default='light')

    logo = fields.Binary(
        string='Logo',
        attachment=True
    )

    custom_css = fields.Text(
        string='Custom CSS'
    )

    custom_js = fields.Text(
        string='Custom JavaScript'
    )
