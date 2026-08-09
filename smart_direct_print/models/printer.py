# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError


class SmartPrinter(models.Model):
    """
    Printer Configuration Model

    Represents a physical printer that can receive print jobs.
    """
    _name = 'smart.printer'
    _description = 'Smart Printer Configuration'
    _order = 'name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # Basic Information
    name = fields.Char(
        string='Printer Name',
        required=True,
        tracking=True,
        help='A descriptive name for this printer'
    )
    external_printer_id = fields.Char(
        string='External Printer ID',
        required=True,
        tracking=True,
        help='Printer ID as known by the print server'
    )
    server_id = fields.Many2one(
        'smart.print.server',
        string='Print Server',
        required=True,
        tracking=True,
        help='The print server this printer is connected to'
    )
    active = fields.Boolean(
        string='Active',
        default=True,
        tracking=True,
        help='Enable or disable this printer'
    )

    # Printer Capabilities
    printer_type = fields.Selection([
        ('generic', 'Generic'),
        ('zpl', 'ZPL Label Printer'),
        ('esc_pos', 'ESC/POS Receipt Printer'),
        ('pdf', 'PDF Printer'),
        ('label', 'Label Printer'),
        ('thermal', 'Thermal Printer'),
        ('laser', 'Laser Printer'),
        ('inkjet', 'Inkjet Printer'),
    ], string='Printer Type', required=True, default='generic', tracking=True)

    supported_formats = fields.Selection([
        ('pdf', 'PDF'),
        ('zpl', 'ZPL'),
        ('esc_pos', 'ESC/POS'),
        ('raw', 'RAW'),
        ('png', 'PNG'),
        ('jpg', 'JPG'),
        ('tiff', 'TIFF'),
    ], string='Supported Format', required=True, default='pdf', tracking=True)

    paper_size = fields.Selection([
        ('a4', 'A4'),
        ('a5', 'A5'),
        ('letter', 'Letter'),
        ('legal', 'Legal'),
        ('label_4x6', 'Label 4x6'),
        ('label_4x4', 'Label 4x4'),
        ('label_4x3', 'Label 4x3'),
        ('receipt_80', 'Receipt 80mm'),
        ('receipt_58', 'Receipt 58mm'),
        ('custom', 'Custom'),
    ], string='Paper Size', default='a4', tracking=True)

    default_copies = fields.Integer(
        string='Default Copies',
        default=1,
        required=True,
        min=1,
        max=999,
        tracking=True
    )

    # Location & Access
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True,
        help='Company this printer belongs to'
    )
    user_ids = fields.Many2many(
        'res.users',
        string='Allowed Users',
        help='Users who can use this printer. If empty, all users can use it.'
    )
    workstation_name = fields.Char(
        string='Workstation Name',
        help='Name of the workstation this printer is associated with'
    )
    default_bin = fields.Char(
        string='Default Bin/Location',
        help='Default output bin or paper tray location'
    )

    # Status
    last_sync = fields.Datetime(
        string='Last Synchronization',
        readonly=True,
        help='Timestamp of the last sync with the print server'
    )
    status = fields.Selection([
        ('unknown', 'Unknown'),
        ('online', 'Online'),
        ('offline', 'Offline'),
        ('error', 'Error'),
        ('busy', 'Busy'),
        ('paper_out', 'Paper Out'),
        ('toner_low', 'Toner Low'),
    ], string='Status', default='unknown', tracking=True)

    # Additional
    description = fields.Text(
        string='Description',
        help='Additional notes about this printer'
    )

    _sql_constraints = [
        ('unique_external_server', 'unique(external_printer_id, server_id)',
         'Printer must be unique per server!'),
        ('unique_name_company', 'unique(name, company_id)',
         'Printer name must be unique per company!')
    ]

    @api.constrains('supported_formats')
    def _check_format_compatibility(self):
        """Check that the format is compatible with the printer type."""
        for printer in self:
            incompatible = {
                'zpl': ['pdf', 'png', 'jpg', 'tiff'],
                'esc_pos': ['pdf', 'png', 'jpg', 'tiff', 'zpl'],
            }

            if printer.printer_type in incompatible:
                if printer.supported_formats in incompatible[printer.printer_type]:
                    raise ValidationError(_(
                        '%(type)s printers do not support %(format)s format'
                    ) % {
                                              'type': printer.printer_type.upper(),
                                              'format': printer.supported_formats.upper()
                                          })

    @api.depends('external_printer_id', 'server_id')
    def _compute_display_name(self):
        """Compute display name with server info."""
        for printer in self:
            if printer.server_id:
                printer.display_name = _(
                    '%(name)s (%(server)s)'
                ) % {
                                           'name': printer.name,
                                           'server': printer.server_id.name
                                       }
            else:
                printer.display_name = printer.name

    def can_print_format(self, format_type):
        """
        Check if printer supports the given format.

        Args:
            format_type (str): Format to check (pdf, zpl, etc.)

        Returns:
            bool: True if the printer supports the format
        """
        self.ensure_one()
        return self.supported_formats == format_type

    def _get_available_formats(self):
        """
        Get list of formats this printer supports.

        Returns:
            list: List of supported format strings
        """
        self.ensure_one()
        return [self.supported_formats]

    def test_print(self):
        """
        Send a test print job to the printer.

        Returns:
            dict: Action notification
        """
        self.ensure_one()

        if not self.server_id:
            raise UserError(_('Printer has no associated print server'))

        if self.server_id.state != 'online':
            self.server_id.test_connection()
            if self.server_id.state != 'online':
                raise UserError(_('Print server is not online'))

        try:
            # Create a simple test document
            test_data = {
                'data': b'SMART PRINT TEST PAGE\n\n'
                        b'This is a test print from Odoo Smart Direct Print\n'
                        b'Printer: %s\n'
                        b'Date: %s\n' % (
                            self.name.encode(),
                            fields.Datetime.now().isoformat().encode()
                        ),
                'filename': 'test_print.txt'
            }

            job_id = self.server_id.send_print_job(
                self.external_printer_id,
                test_data,
                {'format': 'raw', 'copies': 1}
            )

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Test Print Sent'),
                    'message': _(
                        'Test print job sent to %(printer)s (Job ID: %(job)s)'
                    ) % {'printer': self.name, 'job': job_id},
                    'type': 'success',
                    'sticky': False,
                }
            }

        except Exception as e:
            raise UserError(_('Test print failed: %s') % str(e))

    def action_view_jobs(self):
        """View print jobs for this printer."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Print Jobs for %s') % self.name,
            'res_model': 'smart.print.job',
            'view_mode': 'tree,form',
            'domain': [('printer_id', '=', self.id)],
        }
    