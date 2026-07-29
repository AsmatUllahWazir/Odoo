from odoo import api, fields, models, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class TrackingUpdateWizard(models.TransientModel):
    _name = 'shipping.tracking.update.wizard'
    _description = 'Tracking Update Wizard'

    shipment_ids = fields.Many2many(
        'shipping.shipment',
        string='Shipments',
        required=True,
        help='Select shipments to update tracking for'
    )

    force_update = fields.Boolean(
        string='Force Update',
        default=False,
        help='Force update even if recently updated'
    )

    notes = fields.Text(string='Notes')

    def action_update_tracking(self):
        """Update tracking for selected shipments"""
        self.ensure_one()

        if not self.shipment_ids:
            raise UserError(_('Please select at least one shipment.'))

        updated_count = 0
        failed_count = 0
        errors = []

        for shipment in self.shipment_ids:
            try:
                if not shipment.tracking_number:
                    errors.append(f"{shipment.name}: No tracking number")
                    failed_count += 1
                    continue

                # Check if recently updated (within last hour) unless forced
                if not self.force_update and shipment.last_tracking_date:
                    from datetime import datetime, timedelta
                    if shipment.last_tracking_date > (datetime.now() - timedelta(hours=1)):
                        errors.append(f"{shipment.name}: Recently updated, use force to override")
                        failed_count += 1
                        continue

                shipment.action_update_tracking()
                updated_count += 1

            except Exception as e:
                errors.append(f"{shipment.name}: {str(e)}")
                failed_count += 1

        message = f"Updated tracking for {updated_count} shipments"
        if failed_count > 0:
            message += f", {failed_count} failed"
            if errors:
                message += f"\nErrors:\n{chr(10).join(errors)}"

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Tracking Update'),
                'message': message,
                'type': 'success' if failed_count == 0 else 'warning',
                'sticky': True,
            }
        }
    