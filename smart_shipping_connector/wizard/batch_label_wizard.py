from odoo import api, fields, models, _
from odoo.exceptions import UserError
import logging
import base64
from io import BytesIO

_logger = logging.getLogger(__name__)


class BatchLabelWizard(models.TransientModel):
    _name = 'shipping.batch.label.wizard'
    _description = 'Batch Label Generation Wizard'

    shipment_ids = fields.Many2many(
        'shipping.shipment',
        string='Shipments',
        required=True,
        help='Select shipments to generate labels for'
    )

    label_format = fields.Selection([
        ('pdf', 'PDF'),
        ('zpl', 'ZPL'),
        ('png', 'PNG'),
    ], string='Label Format', default='pdf')

    include_return_labels = fields.Boolean(
        string='Include Return Labels',
        default=False,
        help='Generate return labels as well'
    )

    notes = fields.Text(string='Notes')

    def action_generate_labels(self):
        """Generate labels for selected shipments"""
        self.ensure_one()

        if not self.shipment_ids:
            raise UserError(_('Please select at least one shipment.'))

        generated_count = 0
        failed_count = 0
        errors = []

        for shipment in self.shipment_ids:
            try:
                if shipment.state not in ['confirmed', 'label_generated', 'processing']:
                    errors.append(f"{shipment.name}: Invalid state '{shipment.state}'")
                    failed_count += 1
                    continue

                shipment.action_generate_label()
                generated_count += 1

                # Generate return label if requested
                if self.include_return_labels and shipment.return_ids:
                    for return_order in shipment.return_ids:
                        if return_order.state == 'approved':
                            return_order.action_generate_label()

            except Exception as e:
                errors.append(f"{shipment.name}: {str(e)}")
                failed_count += 1

        message = f"Generated {generated_count} labels"
        if failed_count > 0:
            message += f", {failed_count} failed"
            if errors:
                message += f"\nErrors:\n{chr(10).join(errors)}"

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Batch Label Generation'),
                'message': message,
                'type': 'success' if failed_count == 0 else 'warning',
                'sticky': True,
            }
        }
    