# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
import logging
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    """
    Account Move Extension

    Adds automatic printing support for invoices.
    """
    _inherit = 'account.move'

    def action_post(self):
        """
        Override post method to trigger print scenarios.
        """
        result = super().action_post()

        # Trigger print scenarios for invoice posting
        try:
            # Only trigger for customer invoices
            invoice_records = self.filtered(lambda m: m.move_type in ['out_invoice', 'out_refund'])
            if invoice_records:
                invoice_records._trigger_print_scenarios('account_invoice_posted')
        except Exception as e:
            _logger.error(f"Failed to trigger print scenarios for invoice: {e}")

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
            _logger.info(f"Triggered {len(jobs)} print jobs for invoice {self.name}")

    def action_direct_print_invoice(self):
        """
        Direct print the invoice.

        Returns:
            dict: Action result
        """
        self.ensure_one()

        # Find the invoice report
        report = self.env.ref('account.account_invoices', raise_if_not_found=False)
        if not report:
            raise UserError(_('Invoice report not found'))

        return report.action_direct_print([self.id])
