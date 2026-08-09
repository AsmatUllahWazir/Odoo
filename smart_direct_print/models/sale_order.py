# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    """
    Sale Order Extension

    Adds automatic printing support for sale orders.
    """
    _inherit = 'sale.order'

    def action_confirm(self):
        """
        Override confirm method to trigger print scenarios.
        """
        result = super().action_confirm()

        # Trigger print scenarios for sale order confirmation
        try:
            self._trigger_print_scenarios('sale_order_confirmed')
        except Exception as e:
            _logger.error(f"Failed to trigger print scenarios for sale order: {e}")

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
            _logger.info(f"Triggered {len(jobs)} print jobs for sale order {self.name}")

    def action_direct_print_quotation(self):
        """
        Direct print the sale order quotation.

        Returns:
            dict: Action result
        """
        self.ensure_one()

        # Find the quotation report
        report = self.env.ref('sale.action_report_saleorder', raise_if_not_found=False)
        if not report:
            raise UserError(_('Sale order report not found'))

        return report.action_direct_print([self.id])

    def action_direct_print_order(self):
        """
        Direct print the sale order.

        Returns:
            dict: Action result
        """
        self.ensure_one()

        # Find the order report
        report = self.env.ref('sale.action_report_saleorder', raise_if_not_found=False)
        if not report:
            raise UserError(_('Sale order report not found'))

        return report.action_direct_print([self.id])
