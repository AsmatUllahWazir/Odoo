# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
import logging
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class PurchaseOrder(models.Model):
    """
    Purchase Order Extension

    Adds automatic printing support for purchase orders.
    """
    _inherit = 'purchase.order'

    def button_confirm(self):
        """
        Override confirm method to trigger print scenarios.
        """
        result = super().button_confirm()

        # Trigger print scenarios for purchase order confirmation
        try:
            self._trigger_print_scenarios('purchase_order_confirmed')
        except Exception as e:
            _logger.error(f"Failed to trigger print scenarios for purchase order: {e}")

        return result

    def _trigger_print_scenarios(self, action_code):
        """
        Trigger print scenarios for this record.

        Args:
            action_code (str): Action code to trigger
        """
        if not self:
            return

        # Check if auto-print is enabled for the user
        if not self.env.user.auto_print_enabled:
            _logger.info(f"Auto-print disabled for user {self.env.user.name}")
            return

        # Trigger scenarios
        scenario_model = self.env['smart.print.scenario']
        jobs = scenario_model.trigger_scenarios(action_code, self)

        if jobs:
            _logger.info(f"Triggered {len(jobs)} print jobs for purchase order {self.name}")

    def action_direct_print_order(self):
        """
        Direct print the purchase order.

        Returns:
            dict: Action result
        """
        self.ensure_one()

        # Find the purchase order report
        report = self.env.ref('purchase.action_report_purchase_order', raise_if_not_found=False)
        if not report:
            raise UserError(_('Purchase order report not found'))

        return report.action_direct_print([self.id])
