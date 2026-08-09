# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import base64
import logging

_logger = logging.getLogger(__name__)


class SmartPrintOperations(models.TransientModel):
    """
    Print Operations Wizard

    Provides a reusable wizard for manual printing operations.
    """
    _name = 'smart.print.operations'
    _description = 'Smart Print Operations Wizard'

    # Document Selection
    model_id = fields.Many2one(
        'ir.model',
        string='Model',
        required=True,
        help='Model of the records to print'
    )
    record_ids = fields.Text(
        string='Record IDs',
        required=True,
        help='Comma-separated list of record IDs to print'
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
    number_of_copies = fields.Integer(
        string='Copies',
        default=1,
        required=True,
        min=1,
        max=999,
        help='Number of copies to print'
    )
    output_format = fields.Selection([
        ('pdf', 'PDF'),
        ('zpl', 'ZPL'),
        ('esc_pos', 'ESC/POS'),
        ('raw', 'RAW'),
    ], string='Output Format', default='pdf', required=True,
        help='Document output format')

    # Additional Options
    print_immediately = fields.Boolean(
        string='Print Immediately',
        default=True,
        help='Send the job to the printer immediately'
    )
    show_preview = fields.Boolean(
        string='Show Preview',
        default=False,
        help='Show a preview before printing'
    )

    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('processing', 'Processing'),
        ('done', 'Done'),
        ('error', 'Error')
    ], string='Status', default='draft')
    error_message = fields.Text(
        string='Error Message',
        help='Error details if the operation failed'
    )
    job_ids = fields.Many2many(
        'smart.print.job',
        string='Print Jobs',
        help='Created print jobs'
    )

    @api.onchange('model_id')
    def _onchange_model_id(self):
        """Filter reports based on model."""
        if self.model_id:
            domain = [('binding_model_id', '=', self.model_id.id)]
            return {'domain': {'report_id': domain}}

    @api.onchange('report_id')
    def _onchange_report_id(self):
        """Auto-fill printer and format from report config."""
        if self.report_id:
            config = self.env['smart.print.report'].get_report_config(self.report_id.id)
            if config:
                if config.default_printer_id and not self.printer_id:
                    self.printer_id = config.default_printer_id.id
                if config.supported_format:
                    self.output_format = config.supported_format
                if config.number_of_copies > 1:
                    self.number_of_copies = config.number_of_copies

    @api.onchange('printer_id')
    def _onchange_printer_id(self):
        """Validate printer format compatibility."""
        if self.printer_id and self.output_format:
            if not self.printer_id.can_print_format(self.output_format):
                return {
                    'warning': {
                        'title': _('Format Incompatibility'),
                        'message': _(
                            'Printer %(printer)s does not support format %(format)s'
                        ) % {
                                       'printer': self.printer_id.name,
                                       'format': self.output_format.upper()
                                   }
                    }
                }

    def _get_records(self):
        """
        Get the records to print.

        Returns:
            Model: Recordset of records to print
        """
        if not self.record_ids:
            return self.env[self.model_id.model].browse()

        ids = []
        for item in self.record_ids.split(','):
            item = item.strip()
            if item:
                try:
                    ids.append(int(item))
                except ValueError:
                    raise ValidationError(_('Invalid record ID: %s') % item)

        if not ids:
            raise ValidationError(_('No valid record IDs provided'))

        records = self.env[self.model_id.model].browse(ids)
        if not records:
            raise ValidationError(_('No records found with the provided IDs'))

        return records

    def action_print(self):
        """
        Execute the print operation.

        Returns:
            dict: Action result
        """
        self.ensure_one()

        if self.state == 'processing':
            raise UserError(_('Print operation already in progress'))

        self.state = 'processing'

        try:
            # Get records
            records = self._get_records()

            # Validate printer supports format
            if not self.printer_id.can_print_format(self.output_format):
                raise ValidationError(_(
                    'Printer %(printer)s does not support format %(format)s'
                ) % {
                                          'printer': self.printer_id.name,
                                          'format': self.output_format.upper()
                                      })

            # Create print jobs
            jobs = self._create_print_jobs(records)

            if self.print_immediately:
                for job in jobs:
                    try:
                        job.action_validate()
                        job.action_queue()
                    except Exception as e:
                        _logger.error(f"Failed to send job {job.name}: {e}")
                        # Continue with other jobs

            self.write({
                'state': 'done',
                'job_ids': [(6, 0, jobs.ids)]
            })

            # Show success message
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Print Operation Complete'),
                    'message': _(
                        'Created %(count)s print jobs for %(records)s records'
                    ) % {
                                   'count': len(jobs),
                                   'records': len(records)
                               },
                    'type': 'success',
                    'sticky': False,
                }
            }

        except Exception as e:
            self.write({
                'state': 'error',
                'error_message': str(e)
            })
            raise UserError(_('Print operation failed: %s') % str(e))

    def _create_print_jobs(self, records):
        """
        Create print jobs for selected records.

        Args:
            records (Model): Records to print

        Returns:
            smart.print.job: Created print jobs
        """
        PrintJob = self.env['smart.print.job']
        jobs = self.env['smart.print.job']

        for record in records:
            job_vals = {
                'printer_id': self.printer_id.id,
                'user_id': self.env.user.id,
                'model': record._name,
                'res_id': record.id,
                'report_id': self.report_id.id,
                'number_of_copies': self.number_of_copies,
                'document_format': self.output_format,
                'priority': 10,  # Manual print priority
            }
            job = PrintJob.create(job_vals)
            jobs |= job

        return jobs

    def action_cancel(self):
        """Cancel the operation."""
        self.write({'state': 'draft'})
        return {'type': 'ir.actions.act_window_close'}

    def action_view_jobs(self):
        """View created print jobs."""
        self.ensure_one()
        if not self.job_ids:
            raise UserError(_('No print jobs created'))

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'smart.print.job',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.job_ids.ids)],
            'context': {'create': False},
        }

    def action_retry_failed(self):
        """Retry failed jobs."""
        self.ensure_one()

        failed_jobs = self.job_ids.filtered(lambda j: j.state == 'error')
        if not failed_jobs:
            raise UserError(_('No failed jobs to retry'))

        for job in failed_jobs:
            try:
                job.action_retry()
            except Exception as e:
                _logger.error(f"Failed to retry job {job.name}: {e}")

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Retry Initiated'),
                'message': _('Retrying %(count)s failed jobs') % {
                    'count': len(failed_jobs)
                },
                'type': 'info',
                'sticky': False,
            }
        }
