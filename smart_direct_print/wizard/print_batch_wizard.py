# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)


class SmartPrintBatchWizard(models.TransientModel):
    """
    Batch Print Wizard

    For printing multiple documents at once with different reports.
    """
    _name = 'smart.print.batch.wizard'
    _description = 'Smart Batch Print Wizard'

    # Batch Information
    name = fields.Char(
        string='Batch Name',
        default=lambda self: _('Batch Print %s') % fields.Datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    )
    description = fields.Text(
        string='Description',
        help='Description of this batch print operation'
    )

    # Print Jobs
    job_line_ids = fields.One2many(
        'smart.print.batch.wizard.line',
        'wizard_id',
        string='Print Lines',
        help='Individual print jobs in this batch'
    )

    # Default Options
    default_printer_id = fields.Many2one(
        'smart.printer',
        string='Default Printer',
        help='Default printer for all jobs in this batch'
    )
    default_copies = fields.Integer(
        string='Default Copies',
        default=1,
        min=1,
        max=99,
        help='Default number of copies'
    )
    default_format = fields.Selection([
        ('pdf', 'PDF'),
        ('zpl', 'ZPL'),
        ('esc_pos', 'ESC/POS'),
        ('raw', 'RAW'),
    ], string='Default Format', default='pdf')

    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('processing', 'Processing'),
        ('done', 'Done'),
        ('error', 'Error')
    ], string='Status', default='draft')
    total_jobs = fields.Integer(
        string='Total Jobs',
        compute='_compute_job_counts'
    )
    successful_jobs = fields.Integer(
        string='Successful Jobs',
        compute='_compute_job_counts'
    )
    failed_jobs = fields.Integer(
        string='Failed Jobs',
        compute='_compute_job_counts'
    )

    @api.depends('job_line_ids', 'job_line_ids.state')
    def _compute_job_counts(self):
        """Compute job statistics."""
        for wizard in self:
            wizard.total_jobs = len(wizard.job_line_ids)
            wizard.successful_jobs = len(wizard.job_line_ids.filtered(lambda l: l.state == 'done'))
            wizard.failed_jobs = len(wizard.job_line_ids.filtered(lambda l: l.state == 'error'))

    def action_add_lines(self):
        """Add lines from a selection."""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Add Print Lines'),
            'res_model': 'smart.print.batch.wizard.line',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_wizard_id': self.id,
                'default_printer_id': self.default_printer_id.id if self.default_printer_id else False,
                'default_copies': self.default_copies,
                'default_format': self.default_format,
            }
        }

    def action_print_batch(self):
        """Execute all jobs in the batch."""
        self.ensure_one()

        if self.state == 'processing':
            raise UserError(_('Batch is already being processed'))

        if not self.job_line_ids:
            raise UserError(_('No print lines configured'))

        self.state = 'processing'

        try:
            for line in self.job_line_ids:
                try:
                    line.action_print()
                except Exception as e:
                    _logger.error(f"Line {line.id} failed: {e}")
                    line.write({
                        'state': 'error',
                        'error_message': str(e)
                    })

            self.state = 'done'

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Batch Print Complete'),
                    'message': _(
                        'Success: %(success)s, Failed: %(failed)s, Total: %(total)s'
                    ) % {
                                   'success': self.successful_jobs,
                                   'failed': self.failed_jobs,
                                   'total': self.total_jobs
                               },
                    'type': 'success' if self.failed_jobs == 0 else 'warning',
                    'sticky': False,
                }
            }

        except Exception as e:
            self.state = 'error'
            raise UserError(_('Batch print failed: %s') % str(e))

    def action_view_jobs(self):
        """View all jobs in this batch."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'smart.print.job',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.job_line_ids.mapped('job_id').ids)],
        }

    def action_cancel(self):
        """Cancel the batch."""
        return {'type': 'ir.actions.act_window_close'}


class SmartPrintBatchWizardLine(models.TransientModel):
    """
    Batch Print Wizard Line

    Individual line in a batch print operation.
    """
    _name = 'smart.print.batch.wizard.line'
    _description = 'Smart Batch Print Wizard Line'

    wizard_id = fields.Many2one(
        'smart.print.batch.wizard',
        string='Wizard',
        required=True,
        ondelete='cascade'
    )

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
    record_name = fields.Char(
        string='Record Name',
        compute='_compute_record_name',
        store=True
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
        ('processing', 'Processing'),
        ('done', 'Done'),
        ('error', 'Error')
    ], string='Status', default='draft')
    error_message = fields.Text(
        string='Error Message',
        readonly=True
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10,
        help='Order of printing'
    )

    @api.depends('model', 'res_id')
    def _compute_record_name(self):
        """Compute the display name of the record."""
        for line in self:
            if line.model and line.res_id:
                try:
                    model_obj = self.env.get(line.model)
                    if model_obj:
                        record = model_obj.browse(line.res_id)
                        if record.exists():
                            line.record_name = record.display_name
                            continue
                except Exception:
                    pass
            line.record_name = f"{line.model}:{line.res_id}" if line.model else ''

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
        """Execute this print line."""
        self.ensure_one()

        if self.state == 'done':
            return

        self.state = 'processing'

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
                'state': 'done',
                'job_id': job.id,
                'error_message': False
            })

        except Exception as e:
            self.write({
                'state': 'error',
                'error_message': str(e)
            })
            raise

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
