# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError
import logging
from datetime import datetime

_logger = logging.getLogger(__name__)


class ProgressBillingReport(models.AbstractModel):
    """Progress Billing Report PDF"""
    _name = 'report.construction_costing_suite.progress_billing_report'
    _description = 'Progress Billing Report'
    _inherit = 'report.report_xlsx.abstract'

    def _get_report_values(self, docids, data=None):
        """Prepare data for the report"""
        docs = self.env['construction.progress.billing'].browse(docids)

        billing_data = []
        total_billed = 0.0
        total_retainage = 0.0
        total_net = 0.0

        for billing in docs:
            billing_data.append({
                'billing': billing,
                'billed_amount': billing.billed_amount,
                'retainage_amount': billing.retainage_amount,
                'net_amount': billing.net_amount,
                'invoice': billing.invoice_id,
                'milestones': billing.project_id.milestone_ids.filtered(
                    lambda m: m.state == 'invoiced'
                ),
            })
            total_billed += billing.billed_amount
            total_retainage += billing.retainage_amount
            total_net += billing.net_amount

        return {
            'doc_ids': docids,
            'doc_model': 'construction.progress.billing',
            'docs': docs,
            'billing_data': billing_data,
            'total_billed': total_billed,
            'total_retainage': total_retainage,
            'total_net': total_net,
            'date_report': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        }

    def generate_xlsx_report(self, workbook, data, billings):
        """Generate Excel report"""
        sheet = workbook.add_workbook('Progress Billing Report')
        bold = workbook.add_format({'bold': True})
        currency_fmt = workbook.add_format({'num_format': '#,##0.00'})

        # Header
        sheet.write('A1', 'Progress Billing Report', bold)
        sheet.write('A2', f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}')

        # Summary
        sheet.write('A4', 'Summary:', bold)
        sheet.write('A5', 'Total Billings:')
        sheet.write('B5', f'=SUM(H{7}:H{7 + len(billings)})', currency_fmt)
        sheet.write('A6', 'Total Retainage:')
        sheet.write('B6', f'=SUM(I{7}:I{7 + len(billings)})', currency_fmt)
        sheet.write('A7', 'Total Net:')
        sheet.write('B7', f'=SUM(J{7}:J{7 + len(billings)})', currency_fmt)

        # Column headers
        headers = ['Billing #', 'Project', 'Billing Date', 'Method',
                   'Milestones', 'Billed Amount', 'Retainage %',
                   'Retainage Amount', 'Net Amount', 'Invoice #', 'Status']

        row = 9
        for col, header in enumerate(headers):
            sheet.write(row, col, header, bold)

        # Data
        row = 10
        for billing in billings:
            sheet.write(row, 0, billing.name)
            sheet.write(row, 1, billing.project_id.name)
            sheet.write(row, 2, billing.billing_date)
            sheet.write(row, 3, dict(billing._fields['billing_method'].selection).get(
                billing.billing_method, billing.billing_method
            ))

            # Milestones
            milestones = billing.project_id.milestone_ids.filtered(
                lambda m: m.state == 'invoiced'
            )
            sheet.write(row, 4, ', '.join(m.name for m in milestones))

            sheet.write(row, 5, billing.billed_amount, currency_fmt)
            sheet.write(row, 6, billing.retainage_percentage)
            sheet.write(row, 7, billing.retainage_amount, currency_fmt)
            sheet.write(row, 8, billing.net_amount, currency_fmt)
            sheet.write(row, 9, billing.invoice_id.name if billing.invoice_id else '')
            sheet.write(row, 10, dict(billing._fields['state'].selection).get(
                billing.state, billing.state
            ))
            row += 1

        # Adjust column widths
        sheet.set_column('A:A', 15)
        sheet.set_column('B:B', 25)
        sheet.set_column('C:C', 15)
        sheet.set_column('D:D', 18)
        sheet.set_column('E:E', 30)
        sheet.set_column('F:J', 18)
        sheet.set_column('K:K', 15)
        