# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from datetime import timedelta
import logging
import base64

_logger = logging.getLogger(__name__)


class SmartPrintJob(models.Model):
    """
    Print Job Model

    Represents every print request sent through the system.
    """
    _name = 'smart.print.job'
    _description = 'Smart Print Job'
    _order = 'create_date desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # Identification
    name = fields.Char(
        string='Reference',
        required=True,
        default=lambda self: self._get_default_name(),
        tracking=True,
        help='Unique job reference'
    )
    reference = fields.Char(
        string='Job Reference',
        help='External job reference or custom reference'
    )

    # Printer & Server
    printer_id = fields.Many2one(
        'smart.printer',
        string='Printer',
        required=True,
        tracking=True,
        help='Printer that will process this job'
    )
    server_id = fields.Many2one(
        'smart.print.server',
        string='Print Server',
        related='printer_id.server_id',
        store=True,
        readonly=True,
        help='Server handling this job'
    )

    # User & Company
    user_id = fields.Many2one(
        'res.users',
        string='User',
        required=True,
        default=lambda self: self.env.user,
        tracking=True,
        help='User who submitted this job'
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        related='user_id.company_id',
        store=True,
        readonly=True,
        help='Company of the user who submitted the job'
    )

    # Document
    model = fields.Char(
        string='Document Model',
        required=True,
        help='Odoo model name of the printed document'
    )
    res_id = fields.Integer(
        string='Record ID',
        required=True,
        help='ID of the printed record'
    )
    report_id = fields.Many2one(
        'ir.actions.report',
        string='Report',
        help='Report used to generate the document'
    )
    attachment_id = fields.Many2one(
        'ir.attachment',
        string='Attachment',
        help='Attachment that was printed (if any)'
    )

    # Print Options
    document_format = fields.Selection([
        ('pdf', 'PDF'),
        ('zpl', 'ZPL'),
        ('esc_pos', 'ESC/POS'),
        ('raw', 'RAW'),
        ('png', 'PNG'),
        ('jpg', 'JPG'),
        ('tiff', 'TIFF'),
    ], string='Document Format', required=True, default='pdf', tracking=True)

    number_of_copies = fields.Integer(
        string='Number of Copies',
        default=1,
        required=True,
        min=1,
        max=999,
        tracking=True,
        help='Number of copies to print'
    )

    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('queued', 'Queued'),
        ('processing', 'Processing'),
        ('sent', 'Sent to Printer'),
        ('done', 'Completed'),
        ('error', 'Error'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', tracking=True)

    external_job_id = fields.Char(
        string='External Job ID',
        help='Job ID assigned by the external print server'
    )
    error_message = fields.Text(
        string='Error Message',
        help='Error details if the job failed'
    )

    # Timestamps
    created_at = fields.Datetime(
        string='Created At',
        default=fields.Datetime.now,
        readonly=True,
        help='Job creation timestamp'
    )
    queued_at = fields.Datetime(
        string='Queued At',
        readonly=True,
        help='Timestamp when the job was queued'
    )
    sent_at = fields.Datetime(
        string='Sent At',
        readonly=True,
        help='Timestamp when the job was sent to the printer'
    )
    completed_at = fields.Datetime(
        string='Completed At',
        readonly=True,
        help='Timestamp when the job was completed'
    )

    # Retry
    retry_count = fields.Integer(
        string='Retry Count',
        default=0,
        readonly=True,
        help='Number of times this job has been retried'
    )
    max_retries = fields.Integer(
        string='Max Retries',
        default=3,
        help='Maximum number of retry attempts'
    )

    # Additional
    document_size = fields.Integer(
        string='Document Size (bytes)',
        help='Size of the document in bytes'
    )
    priority = fields.Integer(
        string='Priority',
        default=0,
        help='Job priority (higher number = higher priority)'
    )

    _sql_constraints = [
        ('unique_external_job', 'unique(external_job_id)',
         'External job ID must be unique!'),
        ('unique_name', 'unique(name)', 'Job reference must be unique!')
    ]

    @api.model
    def _get_default_name(self):
        """Generate a unique job reference."""
        return f"PRINT-{fields.Datetime.now().strftime('%Y%m%d%H%M%S')}-{self.env.user.id}"

    @api.constrains('model', 'res_id')
    def _check_record_exists(self):
        """Check that the referenced record exists."""
        for job in self:
            if job.model and job.res_id:
                model = self.env.get(job.model)
                if model:
                    record = model.browse(job.res_id)
                    if not record.exists():
                        raise ValidationError(_(
                            'Record %(model)s with ID %(id)s does not exist'
                        ) % {'model': job.model, 'id': job.res_id})

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to set default name if not provided."""
        for vals in vals_list:
            if not vals.get('name'):
                vals['name'] = self._get_default_name()
        return super().create(vals_list)

    def action_validate(self):
        """Validate the job and mark it as ready for printing."""
        for job in self:
            if job.state == 'cancelled':
                raise UserError(_('Cannot validate a cancelled job'))

            if job.state != 'draft':
                continue

            job.write({
                'state': 'queued',
                'queued_at': fields.Datetime.now()
            })

    def action_queue(self):
        """
        Queue the print job for sending to the printer.

        This method validates the job and sends it to the printer.
        """
        for job in self:
            if job.state not in ['draft', 'error']:
                continue

            # Validate required fields
            if not job.printer_id:
                job.write({
                    'state': 'error',
                    'error_message': _('No printer selected')
                })
                continue

            if not job.printer_id.server_id:
                job.write({
                    'state': 'error',
                    'error_message': _('Printer has no associated server')
                })
                continue

            # Validate printer supports format
            if not job.printer_id.can_print_format(job.document_format):
                job.write({
                    'state': 'error',
                    'error_message': _(
                        'Printer %(printer)s does not support format %(format)s'
                    ) % {
                                         'printer': job.printer_id.name,
                                         'format': job.document_format.upper()
                                     }
                })
                continue

            # Send to printer
            try:
                job.write({
                    'state': 'queued',
                    'queued_at': fields.Datetime.now()
                })
                job._send_to_printer()
            except Exception as e:
                _logger.error(f"Failed to queue job {job.name}: {e}")
                job.write({
                    'state': 'error',
                    'error_message': str(e)
                })
                raise UserError(_('Failed to queue print job: %s') % str(e))

    def _send_to_printer(self):
        """
        Send the job to the printer.

        This method prepares the document and sends it to the print server.
        """
        self.ensure_one()

        if self.state not in ['draft', 'queued', 'error']:
            _logger.warning(f"Job {self.name} is in state {self.state}, not sending")
            return

        try:
            # Get document data
            document_data = self._get_document_data()
            if not document_data:
                raise UserError(_('Could not generate document data'))

            # Store document size
            doc_size = len(document_data.get('data', b''))
            self.write({'document_size': doc_size})

            # Prepare job options
            job_options = {
                'copies': self.number_of_copies,
                'format': self.document_format,
                'priority': self.priority,
            }

            # Send to server
            server = self.printer_id.server_id
            external_id = server.send_print_job(
                self.printer_id.external_printer_id,
                document_data,
                job_options
            )

            self.write({
                'state': 'sent',
                'sent_at': fields.Datetime.now(),
                'external_job_id': external_id,
                'error_message': False
            })

            _logger.info(f"Job {self.name} sent to printer {self.printer_id.name}")

            # Start monitoring the job status
            self._monitor_job_status()

        except Exception as e:
            _logger.error(f"Failed to send job {self.name}: {e}")
            self.write({
                'state': 'error',
                'error_message': str(e)
            })
            raise

    def _get_document_data(self):
        """
        Get the document data to print.

        Returns:
            dict: Document data with 'data' and 'filename' keys
        """
        self.ensure_one()

        if self.report_id:
            # Render report
            return self._render_report()

        elif self.attachment_id:
            # Use attachment
            return self._get_attachment_data()

        else:
            raise UserError(_('No report or attachment selected for printing'))

    def _render_report(self):
        """Render the report as PDF."""
        self.ensure_one()

        report = self.report_id
        model = self.env[self.model]
        record = model.browse(self.res_id)

        if not record.exists():
            raise UserError(_('Record %s does not exist') % self.res_id)

        try:
            # Render the report
            report_data, content_type = report._render_qweb_pdf(
                [record.id],
                data=report._prepare_data([record.id])
            )

            if not report_data:
                raise UserError(_('Report rendering produced no data'))

            return {
                'data': base64.b64encode(report_data).decode('utf-8'),
                'filename': f"{report.name}_{record.display_name or record.id}.pdf",
                'binary': report_data
            }

        except Exception as e:
            _logger.error(f"Failed to render report {report.name}: {e}")
            raise UserError(_('Failed to render report: %s') % str(e))

    def _get_attachment_data(self):
        """Get data from an attachment."""
        self.ensure_one()

        attachment = self.attachment_id
        if not attachment.datas:
            raise UserError(_('Attachment has no data'))

        try:
            datas = base64.b64decode(attachment.datas)
            return {
                'data': attachment.datas,
                'filename': attachment.name,
                'binary': datas
            }
        except Exception as e:
            _logger.error(f"Failed to decode attachment {attachment.name}: {e}")
            raise UserError(_('Failed to decode attachment data'))

    def _monitor_job_status(self):
        """
        Monitor job status with the server.

        This method is called after sending a job and periodically
        updates the job status.
        """
        self.ensure_one()

        if not self.external_job_id:
            return

        # Use a cron or scheduled action for status updates
        # For now, we set a flag that will be picked up by the scheduler
        self._check_status_async()

    def _check_status_async(self):
        """Check status asynchronously (cron job)."""
        jobs = self.search([
            ('external_job_id', '!=', False),
            ('state', 'in', ['queued', 'sent', 'processing'])
        ])

        for job in jobs:
            job._update_status()

    def _update_status(self):
        """Update job status from the server."""
        self.ensure_one()

        if not self.external_job_id or not self.printer_id.server_id:
            return

        server = self.printer_id.server_id
        status_data = server.get_job_status(self.external_job_id)

        if status_data.get('status') == 'completed':
            self.write({
                'state': 'done',
                'completed_at': fields.Datetime.now()
            })
            _logger.info(f"Job {self.name} completed successfully")

        elif status_data.get('status') in ['error', 'failed']:
            error_msg = status_data.get('message', _('Unknown error'))
            self.write({
                'state': 'error',
                'error_message': error_msg
            })
            _logger.error(f"Job {self.name} failed: {error_msg}")

        elif status_data.get('status') in ['processing', 'printing']:
            self.write({
                'state': 'processing'
            })

    def action_retry(self):
        """
        Retry a failed job.

        This method resets the job to draft and attempts to send it again.
        """
        for job in self:
            if job.state != 'error':
                continue

            if job.retry_count >= job.max_retries:
                raise UserError(_(
                    'Maximum retry attempts (%(max)s) reached for job %(job)s'
                ) % {'max': job.max_retries, 'job': job.name})

            job.write({
                'state': 'draft',
                'retry_count': job.retry_count + 1,
                'error_message': False,
                'external_job_id': False,
            })

            try:
                job.action_queue()
            except Exception as e:
                _logger.error(f"Retry {job.retry_count} failed for job {job.name}: {e}")
                job.write({
                    'state': 'error',
                    'error_message': str(e)
                })
                raise

    def action_cancel(self):
        """
        Cancel a job.

        Cancels the job on the server if it hasn't been completed yet.
        """
        for job in self:
            if job.state in ['done', 'cancelled']:
                continue

            if job.external_job_id and job.printer_id.server_id:
                try:
                    job.printer_id.server_id.cancel_job(job.external_job_id)
                except Exception as e:
                    _logger.warning(f"Could not cancel job {job.name}: {e}")

            job.write({
                'state': 'cancelled',
                'error_message': _('Cancelled by user')
            })

            _logger.info(f"Job {job.name} cancelled by {self.env.user.name}")

    def action_view_record(self):
        """
        View the related record.

        Returns:
            dict: Action to view the record
        """
        self.ensure_one()

        model = self.env.get(self.model)
        if not model:
            raise UserError(_('Model %s does not exist') % self.model)

        record = model.browse(self.res_id)
        if not record.exists():
            raise UserError(_('Record does not exist'))

        return {
            'type': 'ir.actions.act_window',
            'res_model': self.model,
            'res_id': self.res_id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_archive(self):
        """Archive old completed jobs."""
        jobs = self.search([
            ('state', '=', 'done'),
            ('completed_at', '<=', fields.Datetime.now() - timedelta(days=30))
        ])
        jobs.write({'active': False})
        return len(jobs)
