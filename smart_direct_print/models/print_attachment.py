# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import base64
import logging

_logger = logging.getLogger(__name__)


class SmartPrintAttachment(models.Model):
    """
    Print Attachment Model

    Handles direct printing of ir.attachment records.
    """
    _name = 'smart.print.attachment'
    _description = 'Smart Print Attachment'
    _order = 'create_date desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # Basic Information
    name = fields.Char(
        string='Attachment Name',
        required=True,
        tracking=True,
        help='Name of the attachment print configuration'
    )
    attachment_id = fields.Many2one(
        'ir.attachment',
        string='Attachment',
        required=True,
        tracking=True,
        help='The attachment to print'
    )

    # Related Record
    model = fields.Char(
        string='Related Model',
        help='Model of the related record'
    )
    res_id = fields.Integer(
        string='Related Record ID',
        help='ID of the related record'
    )

    # Printing Options
    printer_id = fields.Many2one(
        'smart.printer',
        string='Printer',
        required=True,
        tracking=True,
        help='Printer to use'
    )
    copies = fields.Integer(
        string='Copies',
        default=1,
        min=1,
        max=999,
        tracking=True,
        help='Number of copies to print'
    )
    format = fields.Selection([
        ('pdf', 'PDF'),
        ('png', 'PNG'),
        ('jpg', 'JPG'),
        ('zpl', 'ZPL'),
        ('esc_pos', 'ESC/POS'),
        ('raw', 'RAW'),
    ], string='Document Format', required=True, default='pdf', tracking=True)

    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('printing', 'Printing'),
        ('printed', 'Printed'),
        ('error', 'Error'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', tracking=True)
    print_job_id = fields.Many2one(
        'smart.print.job',
        string='Print Job',
        help='The print job created for this attachment'
    )
    error_message = fields.Text(
        string='Error Message',
        help='Error details if printing failed'
    )

    # Company
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True,
        help='Company this configuration belongs to'
    )

    _sql_constraints = [
        ('unique_attachment_company', 'unique(attachment_id, company_id)',
         'Attachment configuration must be unique per company!')
    ]

    @api.constrains('format')
    def _check_format_compatibility(self):
        """Check that the format is compatible with the attachment."""
        for config in self:
            if config.attachment_id and config.attachment_id.mimetype:
                mime_type = config.attachment_id.mimetype.lower()
                format_map = {
                    'pdf': 'application/pdf',
                    'png': 'image/png',
                    'jpg': ['image/jpeg', 'image/jpg'],
                    'zpl': ['application/x-zpl', 'text/plain'],
                    'esc_pos': ['application/x-escpos', 'text/plain'],
                }

                if config.format in format_map:
                    expected = format_map[config.format]
                    if isinstance(expected, list):
                        if mime_type not in expected:
                            # Don't block, just warn
                            _logger.warning(
                                f"Attachment {config.attachment_id.name} with MIME type "
                                f"{mime_type} may not be compatible with format {config.format}"
                            )
                    else:
                        if mime_type != expected:
                            _logger.warning(
                                f"Attachment {config.attachment_id.name} with MIME type "
                                f"{mime_type} may not be compatible with format {config.format}"
                            )

    def action_print(self):
        """
        Print the attachment.

        Returns:
            smart.print.job: The created print job
        """
        self.ensure_one()

        if self.state in ['printing', 'printed']:
            raise UserError(_('This attachment is already being printed or has been printed'))

        if not self.attachment_id or not self.attachment_id.datas:
            raise UserError(_('Attachment data not found'))

        # Check printer supports format
        if not self.printer_id.can_print_format(self.format):
            raise UserError(_(
                'Printer %(printer)s does not support format %(format)s'
            ) % {
                                'printer': self.printer_id.name,
                                'format': self.format.upper()
                            })

        self.write({'state': 'printing'})

        try:
            # Create print job
            job_vals = {
                'name': f"{self.name}-{fields.Datetime.now().strftime('%Y%m%d%H%M%S')}",
                'printer_id': self.printer_id.id,
                'user_id': self.env.user.id,
                'model': self.model or 'ir.attachment',
                'res_id': self.res_id or self.attachment_id.id,
                'attachment_id': self.attachment_id.id,
                'document_format': self.format,
                'number_of_copies': self.copies,
            }

            job = self.env['smart.print.job'].create(job_vals)
            job.action_validate()
            job.action_queue()

            self.write({
                'state': 'printed',
                'print_job_id': job.id,
                'error_message': False
            })

            return job

        except Exception as e:
            self.write({
                'state': 'error',
                'error_message': str(e)
            })
            raise UserError(_('Failed to print attachment: %s') % str(e))

    def action_cancel(self):
        """Cancel the print operation."""
        self.ensure_one()

        if self.state not in ['draft', 'printing']:
            raise UserError(_('Cannot cancel this operation'))

        if self.print_job_id and self.print_job_id.state not in ['done', 'cancelled']:
            try:
                self.print_job_id.action_cancel()
            except Exception as e:
                _logger.warning(f"Failed to cancel print job: {e}")

        self.write({
            'state': 'cancelled',
            'error_message': _('Cancelled by user')
        })

    def action_view_job(self):
        """View the associated print job."""
        self.ensure_one()
        if not self.print_job_id:
            raise UserError(_('No print job associated with this attachment'))

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'smart.print.job',
            'res_id': self.print_job_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
    