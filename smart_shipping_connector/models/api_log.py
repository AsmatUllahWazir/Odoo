from odoo import api, fields, models, _
import logging
import json
import time

_logger = logging.getLogger(__name__)


class ShippingApiLog(models.Model):
    """API Call Log for Debugging"""
    _name = 'shipping.api.log'
    _description = 'Shipping API Log'
    _order = 'create_date desc'
    _rec_name = 'endpoint'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # Basic Information
    name = fields.Char(
        string='Log Reference',
        default=lambda self: _('New'),
        required=True,
    )
    create_uid = fields.Many2one(
        'res.users',
        string='Created By',
        default=lambda self: self.env.user,
    )

    # Request Details
    endpoint = fields.Char(string='API Endpoint', required=True, tracking=True)
    method = fields.Selection([
        ('GET', 'GET'),
        ('POST', 'POST'),
        ('PUT', 'PUT'),
        ('DELETE', 'DELETE'),
        ('PATCH', 'PATCH'),
    ], string='HTTP Method', required=True, default='POST')

    request_headers = fields.Text(string='Request Headers')
    request_body = fields.Text(string='Request Body')
    request_timestamp = fields.Datetime(string='Request Time', default=fields.Datetime.now)

    # Response Details
    response_code = fields.Integer(string='Response Code')
    response_body = fields.Text(string='Response Body')
    response_headers = fields.Text(string='Response Headers')
    response_timestamp = fields.Datetime(string='Response Time')
    response_time_ms = fields.Float(string='Response Time (ms)')

    # Status
    status = fields.Selection([
        ('success', 'Success'),
        ('error', 'Error'),
        ('timeout', 'Timeout'),
        ('pending', 'Pending'),
    ], string='Status', default='pending', tracking=True)

    error_message = fields.Text(string='Error Message')
    error_traceback = fields.Text(string='Error Traceback')

    # Related Records
    carrier_provider_id = fields.Many2one(
        'shipping.carrier.provider',
        string='Carrier Provider',
    )
    carrier_account_id = fields.Many2one(
        'shipping.carrier.account',
        string='Carrier Account',
    )
    shipment_id = fields.Many2one(
        'shipping.shipment',
        string='Related Shipment',
    )
    return_id = fields.Many2one(
        'shipping.return',
        string='Related Return',
    )

    # Additional
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
    )
    ip_address = fields.Char(string='IP Address')
    user_agent = fields.Char(string='User Agent')

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('shipping.api.log') or _('New')
        return super(ShippingApiLog, self).create(vals)

    def action_retry(self):
        """Retry the API call"""
        self.ensure_one()
        # TODO: Implement retry logic
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Retry Initiated'),
                'message': _('API call retry has been initiated.'),
                'type': 'info',
                'sticky': False,
            }
        }

    def action_view_shipment(self):
        """View related shipment"""
        self.ensure_one()
        if self.shipment_id:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Shipment'),
                'res_model': 'shipping.shipment',
                'res_id': self.shipment_id.id,
                'view_mode': 'form',
                'target': 'current',
            }
        return {'type': 'ir.actions.act_window_close'}

    @api.model
    def clean_old_logs(self):
        """Clean old API logs based on retention policy"""
        config = self.env['shipping.config']._get_default_config()
        if config and config.api_log_retention_days:
            cutoff_date = fields.Datetime.now() - timedelta(days=config.api_log_retention_days)
            old_logs = self.search([
                ('create_date', '<', cutoff_date),
                ('status', '=', 'success')
            ])
            old_logs.unlink()
            _logger.info(f"Cleaned {len(old_logs)} old API logs")
            