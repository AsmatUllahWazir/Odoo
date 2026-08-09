# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)


class SmartPrintWizard(models.TransientModel):
    """
    Simple Print Wizard

    A simpler wizard for printing a single document with minimal options.
    """
    _name = 'smart.print.wizard'
    _description = 'Smart Print Wizard'

    # Document
    model = fields.Char(
        string='Model',
        required=True,
        help='Model name of the document to print'
    )
    res_id = fields.Integer(
        string='Record ID',
        required=True,
        help='ID of the record to print'
    )
    report_id = fields.Many2one(
        'ir.actions.report',
        string='Report',
        required=True,
        help='Report to use for printing'
    )

    # Print Options
    printer_id = fields.Many2one(
        'smart.printer',
        string='Printer',
        required=True,
        help='Printer to use'
    )
    copies = fields.Integer(
        string='Copies',
        default=1,
        min=1,
        max=99,
        help='Number of copies to print'
    )
    format = fields.Selection([
        ('pdf', 'PDF'),
        ('zpl', 'ZPL'),
        ('esc_pos', 'ESC/POS'),
        ('raw', 'RAW'),
    ], string='Format', default='pdf', required=True)

    # Status
    job_id = fields.Many2one(
        'smart.print.job',
        string='Print Job',
        readonly=True
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('printed', 'Printed'),
        ('error', 'Error')
    ], string='Status', default='draft')
    error_message = fields.Text(
        string='Error Message',
        readonly=True
    )

    @api.onchange('report_id')
    def _onchange_report_id(self):
        """Auto-fill printer and format from report config."""
        if self.report_id:
            config = self.env['smart.print.report'].get_report_config(self.report_id.id)
            if config:
                if config.default_printer_id and not self.printer_id:
                    self.printer_id = config.default_printer_id.id
                if config.supported_format:
                    self.format = config.supported_format

    @api.onchange('printer_id')
    def _onchange_printer_id(self):
        """Validate printer format compatibility."""
        if self.printer_id and self.format:
            if not self.printer_id.can_print_format(self.format):
                return {
                    'warning': {
                        'title': _('Format Incompatibility'),
                        'message': _(
                            'Printer %(printer)s does not support format %(format)s'
                        ) % {
                                       'printer': self.printer_id.name,
                                       'format': self.format.upper()
                                   }
                    }
                }

    def action_print(self):
        """Execute the print operation."""
        self.ensure_one()

        if self.state == 'printed':
            raise UserError(_('This document has already been printed'))

        try:
            # Get the record
            model_obj = self.env.get(self.model)
            if not model_obj:
                raise ValidationError(_('Model %s not found') % self.model)

            record = model_obj.browse(self.res_id)
            if not record.exists():
                raise ValidationError(_('Record %s does not exist') % self.res_id)

            # Validate printer supports format
            if not self.printer_id.can_print_format(self.format):
                raise ValidationError(_(
                    'Printer %(printer)s does not support format %(format)s'
                ) % {
                                          'printer': self.printer_id.name,
                                          'format': self.format.upper()
                                      })

            # Create print job
            job_vals = {
                'printer_id': self.printer_id.id,
                'user_id': self.env.user.id,
                'model': self.model,
                'res_id': self.res_id,
                'report_id': self.report_id.id,
                'number_of_copies': self.copies,
                'document_format': self.format,
                'priority': 5,
            }

            job = self.env['smart.print.job'].create(job_vals)

            # Send to printer
            job.action_validate()
            job.action_queue()

            self.write({
                'state': 'printed',
                'job_id': job.id,
                'error_message': False
            })

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Print Successful'),
                    'message': _('Document sent to printer %s') % self.printer_id.name,
                    'type': 'success',
                    'sticky': False,
                }
            }

        except Exception as e:
            self.write({
                'state': 'error',
                'error_message': str(e)
            })
            raise UserError(_('Print failed: %s') % str(e))

    def action_view_job(self):
        """View the created print job."""
        self.ensure_one()
        if not self.job_id:
            raise UserError(_('No print job created'))

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'smart.print.job',
            'res_id': self.job_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_cancel(self):
        """Cancel the wizard."""
        return {'type': 'ir.actions.act_window_close'}
