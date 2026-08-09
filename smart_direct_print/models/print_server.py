# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from odoo import http
import requests
import json
import logging
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)


class SmartPrintServer(models.Model):
    """
    Print Server Configuration Model

    Represents the connection between Odoo and an external/local printing bridge.
    The print bridge is a lightweight service that communicates with physical printers.
    """
    _name = 'smart.print.server'
    _description = 'Smart Print Server Configuration'
    _order = 'name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # Basic Information
    name = fields.Char(
        string='Server Name',
        required=True,
        tracking=True,
        help='A descriptive name for this print server'
    )
    active = fields.Boolean(
        string='Active',
        default=True,
        tracking=True,
        help='Enable or disable this print server'
    )

    # Connection Details
    server_url = fields.Char(
        string='Server URL',
        required=True,
        tracking=True,
        help='URL of the print bridge service (e.g., http://localhost:5000)'
    )
    api_key = fields.Char(
        string='API Key',
        required=True,
        tracking=True,
        help='API key for authenticating with the print bridge'
    )

    # Status Tracking
    state = fields.Selection([
        ('draft', 'Draft'),
        ('connecting', 'Connecting'),
        ('online', 'Online'),
        ('offline', 'Offline'),
        ('error', 'Error')
    ], string='Status', default='draft', tracking=True)

    last_connection_check = fields.Datetime(
        string='Last Connection Check',
        readonly=True,
        help='Timestamp of the last successful connection test'
    )
    error_message = fields.Text(
        string='Error Message',
        readonly=True,
        help='Last error message from the server'
    )

    # Company
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True,
        help='Company this server belongs to'
    )

    _sql_constraints = [
        ('unique_name_company', 'unique(name, company_id)',
         'Server name must be unique per company!'),
        ('unique_url_company', 'unique(server_url, company_id)',
         'Server URL must be unique per company!')
    ]

    @api.constrains('server_url')
    def _check_server_url(self):
        """Validate server URL format."""
        for server in self:
            if server.server_url:
                if not server.server_url.startswith(('http://', 'https://')):
                    raise ValidationError(
                        _('Server URL must start with http:// or https://')
                    )
                # Remove trailing slash if present
                if server.server_url.endswith('/'):
                    server.server_url = server.server_url[:-1]

    @api.model
    def _get_default_server(self):
        """Get the default print server for the current company."""
        return self.search([
            ('company_id', '=', self.env.company.id),
            ('active', '=', True)
        ], limit=1)

    def test_connection(self):
        """
        Test the connection to the print server.

        Returns:
            dict: Action notification result
        """
        self.ensure_one()
        self.state = 'connecting'

        try:
            headers = self._get_auth_headers()
            response = requests.get(
                f"{self.server_url}/api/health",
                headers=headers,
                timeout=10
            )

            if response.status_code == 200:
                self.write({
                    'state': 'online',
                    'last_connection_check': fields.Datetime.now(),
                    'error_message': False
                })

                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('Connection Successful'),
                        'message': _(
                            'Successfully connected to print server: %s'
                        ) % self.name,
                        'type': 'success',
                        'sticky': False,
                    }
                }
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                self.write({
                    'state': 'error',
                    'error_message': error_msg,
                    'last_connection_check': fields.Datetime.now()
                })
                raise UserError(_('Connection failed: %s') % error_msg)

        except requests.exceptions.ConnectionError:
            self.write({
                'state': 'offline',
                'error_message': _('Could not connect to server - network error'),
                'last_connection_check': fields.Datetime.now()
            })
            raise UserError(_('Could not connect to print server. Please check the URL and network connectivity.'))

        except requests.exceptions.Timeout:
            self.write({
                'state': 'offline',
                'error_message': _('Connection timed out'),
                'last_connection_check': fields.Datetime.now()
            })
            raise UserError(_('Connection to print server timed out.'))

        except requests.exceptions.RequestException as e:
            self.write({
                'state': 'error',
                'error_message': str(e),
                'last_connection_check': fields.Datetime.now()
            })
            raise UserError(_('Connection failed: %s') % str(e))

    def _get_auth_headers(self):
        """
        Get authentication headers for API calls.

        Returns:
            dict: Headers with authentication
        """
        return {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }

    def _get_printer_list(self):
        """
        Retrieve printer list from the print server.

        Returns:
            list: List of printer dictionaries from the server
        """
        self.ensure_one()
        headers = self._get_auth_headers()

        try:
            response = requests.get(
                f"{self.server_url}/api/printers",
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            _logger.error(f"Failed to get printer list from {self.name}: {e}")
            self.write({
                'state': 'error',
                'error_message': _('Failed to retrieve printers: %s') % str(e)
            })
            return []

    def sync_printers(self):
        """
        Synchronize printers from the print server.

        Creates or updates printer records based on the server's printer list.

        Returns:
            dict: Action notification with sync results
        """
        self.ensure_one()

        if self.state != 'online':
            self.test_connection()
            if self.state != 'online':
                raise UserError(_(
                    'Cannot sync printers: Print server is not online'
                ))

        printers_data = self._get_printer_list()
        if not printers_data:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Synchronization Complete'),
                    'message': _('No printers found on the server'),
                    'type': 'info',
                    'sticky': False,
                }
            }

        Printer = self.env['smart.printer']
        created = 0
        updated = 0

        for printer_info in printers_data:
            external_id = printer_info.get('id')
            if not external_id:
                continue

            existing = Printer.search([
                ('external_printer_id', '=', str(external_id)),
                ('server_id', '=', self.id)
            ])

            vals = {
                'name': printer_info.get('name', 'Unknown Printer'),
                'external_printer_id': str(external_id),
                'server_id': self.id,
                'printer_type': printer_info.get('type', 'generic'),
                'supported_formats': printer_info.get('supported_formats', ['pdf']),
                'status': printer_info.get('status', 'unknown'),
                'company_id': self.company_id.id,
                'last_sync': fields.Datetime.now(),
            }

            if existing:
                existing.write(vals)
                updated += 1
            else:
                vals['active'] = True
                Printer.create(vals)
                created += 1

        self.write({
            'last_connection_check': fields.Datetime.now(),
            'error_message': False
        })

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Synchronization Complete'),
                'message': _(
                    'Created %(created)s and updated %(updated)s printers'
                ) % {'created': created, 'updated': updated},
                'type': 'success',
                'sticky': False,
            }
        }

    def send_print_job(self, printer_external_id, document_data, job_options=None):
        """
        Send a print job to the server.

        Args:
            printer_external_id (str): External printer ID
            document_data (dict): Document data with 'data' and 'filename' keys
            job_options (dict): Optional job options (copies, format, etc.)

        Returns:
            str: External job ID from the server

        Raises:
            UserError: If the print job fails
        """
        self.ensure_one()

        if self.state != 'online':
            self.test_connection()
            if self.state != 'online':
                raise UserError(_(
                    'Print server %s is not online') % self.name)

        headers = self._get_auth_headers()
        job_options = job_options or {}

        # Prepare the payload
        payload = {
            'printer_id': printer_external_id,
            'document': document_data,
            'options': {
                'copies': job_options.get('copies', 1),
                'format': job_options.get('format', 'pdf'),
                'duplex': job_options.get('duplex', False),
                'color': job_options.get('color', True),
                'paper_size': job_options.get('paper_size', 'A4'),
                'orientation': job_options.get('orientation', 'portrait'),
            }
        }

        try:
            _logger.info(f"Sending print job to {self.name} for printer {printer_external_id}")

            response = requests.post(
                f"{self.server_url}/api/print",
                json=payload,
                headers=headers,
                timeout=60
            )
            response.raise_for_status()
            result = response.json()

            job_id = result.get('job_id')
            if not job_id:
                raise UserError(_('Server did not return a job ID'))

            return job_id

        except requests.exceptions.RequestException as e:
            _logger.error(f"Print job failed on {self.name}: {e}")
            self.write({
                'state': 'error',
                'error_message': str(e)
            })
            raise UserError(_(
                'Failed to send print job to %(server)s: %(error)s'
            ) % {'server': self.name, 'error': str(e)})

    def get_job_status(self, job_id):
        """
        Get job status from the server.

        Args:
            job_id (str): External job ID

        Returns:
            dict: Job status information
        """
        self.ensure_one()
        headers = self._get_auth_headers()

        try:
            response = requests.get(
                f"{self.server_url}/api/status/{job_id}",
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            _logger.error(f"Failed to get job status for {job_id}: {e}")
            return {
                'status': 'error',
                'message': str(e)
            }

    def cancel_job(self, job_id):
        """
        Cancel a job on the server.

        Args:
            job_id (str): External job ID

        Returns:
            dict: Cancellation result
        """
        self.ensure_one()
        headers = self._get_auth_headers()

        try:
            response = requests.post(
                f"{self.server_url}/api/cancel/{job_id}",
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            _logger.error(f"Failed to cancel job {job_id}: {e}")
            raise UserError(_('Failed to cancel print job: %s') % str(e))

    def action_view_printers(self):
        """Action to view printers for this server."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Printers for %s') % self.name,
            'res_model': 'smart.printer',
            'view_mode': 'tree,form',
            'domain': [('server_id', '=', self.id)],
            'context': {'default_server_id': self.id},
        }

    def action_view_jobs(self):
        """Action to view jobs for this server."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Print Jobs for %s') % self.name,
            'res_model': 'smart.print.job',
            'view_mode': 'tree,form',
            'domain': [('server_id', '=', self.id)],
        }
