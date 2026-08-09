# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class IrAttachment(models.Model):
    """
    Attachment Extension

    Adds direct-print support for attachments.
    """
    _inherit = 'ir.attachment'

    # Direct print configuration
    direct_print_enabled = fields.Boolean(
        string='Direct Print Enabled',
        default=False,
        help='Enable direct printing for this attachment'
    )
    direct_print_printer_id = fields.Many2one(
        'smart.printer',
        string='Direct Print Printer',
        help='Printer for direct printing'
    )
    direct_print_copies = fields.Integer(
        string='Direct Print Copies',
        default=1,
        min=1,
        max=999,
        help='Number of copies to print'
    )
    direct_print_format = fields.Selection([
        ('pdf', 'PDF'),
        ('png', 'PNG'),
        ('jpg', 'JPG'),
        ('zpl', 'ZPL'),
    ], string='Direct Print Format', default='pdf',
        help='Output format for direct printing')

    # Print status
    print_status = fields.Selection([
        ('not_printed', 'Not Printed'),
        ('printing', 'Printing'),
        ('printed', 'Printed'),
        ('error', 'Error')
    ], string='Print Status', default='not_printed')
    print_job_ids = fields.One2many(
        'smart.print.job',
        'attachment_id',
        string='Print Jobs',
        help='Print jobs associated with this attachment'
    )
    last_print_date = fields.Datetime(
        string='Last Print Date',
        help='Date of the last successful print'
    )

    def action_direct_print(self, **kwargs):
        """
        Direct print this attachment.

        Args:
            **kwargs: Additional options

        Returns:
            dict: Action result
        """
        self.ensure_one()

        if not self.datas:
            raise UserError(_('Attachment has no data to print'))

        if not self.direct_print_enabled:
            raise UserError(_('Direct printing is not enabled for this attachment'))

        # Get printer
        printer = kwargs.get('printer') or self.direct_print_printer_id
        if not printer:
            # Try to resolve printer
            resolver = self.env['smart.printer.resolver']
            printer = resolver.get_printer_for_document(
                model='ir.attachment',
                record=self,
                **kwargs
            )

        if not printer:
            raise UserError(_('No printer available for this attachment'))

        # Create print configuration
        print_config = self.env['smart.print.attachment'].create({
            'name': f"{self.name} - {fields.Datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            'attachment_id': self.id,
            'model': self.res_model,
            'res_id': self.res_id,
            'printer_id': printer.id,
            'copies': kwargs.get('copies', self.direct_print_copies or 1),
            'format': kwargs.get('format', self.direct_print_format or 'pdf'),
        })

        # Print
        job = print_config.action_print()

        # Update attachment
        self.write({
            'print_status': 'printing',
            'last_print_date': fields.Datetime.now()
        })

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Printing Attachment'),
                'message': _('Printing %(name)s on %(printer)s') % {
                    'name': self.name,
                    'printer': printer.name
                },
                'type': 'info',
                'sticky': False,
            }
        }

    def action_view_print_jobs(self):
        """View print jobs for this attachment."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'smart.print.job',
            'view_mode': 'tree,form',
            'domain': [('attachment_id', '=', self.id)],
            'context': {'default_attachment_id': self.id},
        }
    