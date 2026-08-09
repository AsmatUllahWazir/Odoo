# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    """
    Stock Picking Extension

    Adds automatic printing support for stock pickings.
    """
    _inherit = 'stock.picking'

    def button_validate(self):
        """
        Override validate method to trigger print scenarios.
        """
        result = super().button_validate()

        # Trigger print scenarios for picking validation
        try:
            self._trigger_print_scenarios('stock_picking_validated')
        except Exception as e:
            _logger.error(f"Failed to trigger print scenarios for picking: {e}")

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
            _logger.info(f"Triggered {len(jobs)} print jobs for picking {self.name}")

    def action_direct_print_delivery_slip(self):
        """
        Direct print the delivery slip.

        Returns:
            dict: Action result
        """
        self.ensure_one()

        # Find the delivery slip report
        report = self.env.ref('stock.action_report_delivery', raise_if_not_found=False)
        if not report:
            # Try alternate report name
            report = self.env['ir.actions.report'].search([
                ('model', '=', 'stock.picking'),
                ('name', 'ilike', 'Delivery')
            ], limit=1)

        if not report:
            raise UserError(_('Delivery slip report not found'))

        return report.action_direct_print([self.id])

    def action_direct_print_picking_operation(self):
        """
        Direct print the picking operation.

        Returns:
            dict: Action result
        """
        self.ensure_one()

        # Find the picking operation report
        report = self.env.ref('stock.action_report_picking', raise_if_not_found=False)
        if not report:
            raise UserError(_('Picking operation report not found'))

        return report.action_direct_print([self.id])
