# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class IrActionsReport(models.Model):
    """
    Report Action Extension

    Adds direct-print configuration to standard Odoo reports.
    """
    _inherit = 'ir.actions.report'

    # Add direct-print configuration fields
    direct_print_enabled = fields.Boolean(
        string='Direct Print Enabled',
        default=False,
        help='Enable direct printing for this report'
    )
    direct_print_printer_id = fields.Many2one(
        'smart.printer',
        string='Direct Print Printer',
        help='Printer for direct printing this report'
    )
    direct_print_copies = fields.Integer(
        string='Direct Print Copies',
        default=1,
        min=1,
        max=999,
        help='Default copies for direct printing'
    )
    direct_print_format = fields.Selection([
        ('pdf', 'PDF'),
        ('zpl', 'ZPL'),
        ('esc_pos', 'ESC/POS'),
        ('raw', 'RAW'),
    ], string='Direct Print Format', default='pdf',
        help='Output format for direct printing')

    def action_direct_print(self, records_ids=None, **kwargs):
        """
        Direct print action handler.

        Args:
            records_ids (list): List of record IDs to print
            **kwargs: Additional options

        Returns:
            dict: Action result
        """
        self.ensure_one()

        if not self.direct_print_enabled:
            # Fall back to standard printing
            return super().action_direct_print(records_ids, **kwargs)

        # Get records
        model = self.env[self.model]
        records = model.browse(records_ids or [])
        if not records:
            raise UserError(_('No records selected for printing'))

        # Get printer
        resolver = self.env['smart.printer.resolver']

        # Use explicit printer if provided, otherwise resolve
        printer = kwargs.get('printer')
        if not printer:
            printer = resolver.get_printer_for_document(
                model=self.model,
                record=records[0] if records else None,
                report=self,
                **kwargs
            )

        if not printer:
            # Fall back to standard printing
            _logger.warning(f"No printer found for direct printing, falling back to standard printing")
            return super().action_direct_print(records_ids, **kwargs)

        # Create print jobs
        PrintJob = self.env['smart.print.job']
        jobs = self.env['smart.print.job']

        for record in records:
            job_vals = {
                'printer_id': printer.id,
                'user_id': self.env.user.id,
                'model': self.model,
                'res_id': record.id,
                'report_id': self.id,
                'number_of_copies': kwargs.get('copies', self.direct_print_copies or 1),
                'document_format': kwargs.get('format', self.direct_print_format or 'pdf'),
            }
            job = PrintJob.create(job_vals)
            jobs |= job

        # Queue jobs for printing
        for job in jobs:
            job.action_validate()
            job.action_queue()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Direct Print Initiated'),
                'message': _('Print jobs sent to %(printer)s') % {'printer': printer.name},
                'type': 'success',
                'sticky': False,
            }
        }

    def action_direct_print_report(self, data=None, context=None):
        """
        Alternative entry point for direct printing from report actions.

        Args:
            data (dict): Report data
            context (dict): Report context

        Returns:
            dict: Action result
        """
        records_ids = data.get('ids', []) if data else []
        return self.action_direct_print(records_ids, **data or {})
    