# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.addons import decimal_precision as dp
import logging
from datetime import datetime

_logger = logging.getLogger(__name__)


class JobCostReport(models.AbstractModel):
    """Job Cost Report PDF"""
    _name = 'report.construction_costing_suite.job_cost_report'
    _description = 'Job Cost Report'
    _inherit = 'report.report_xlsx.abstract'

    def _get_report_values(self, docids, data=None):
        """Prepare data for the report"""
        docs = self.env['construction.job.cost.line'].browse(docids)

        # Group by project
        projects_data = {}
        total_budget = 0.0
        total_actual = 0.0
        total_variance = 0.0

        for line in docs:
            project = line.project_id
            if project not in projects_data:
                projects_data[project] = {
                    'project': project,
                    'lines': [],
                    'total_budget': 0.0,
                    'total_actual': 0.0,
                    'total_variance': 0.0,
                }

            projects_data[project]['lines'].append(line)
            projects_data[project]['total_budget'] += line.budgeted_amount
            projects_data[project]['total_actual'] += line.actual_cost
            projects_data[project]['total_variance'] += line.cost_variance

            total_budget += line.budgeted_amount
            total_actual += line.actual_cost
            total_variance += line.cost_variance

        # Calculate percentages
        for project_data in projects_data.values():
            if project_data['total_budget'] > 0:
                project_data['completion'] = (project_data['total_actual'] / project_data['total_budget']) * 100
            else:
                project_data['completion'] = 0.0

        return {
            'doc_ids': docids,
            'doc_model': 'construction.job.cost.line',
            'docs': docs,
            'projects_data': projects_data,
            'total_budget': total_budget,
            'total_actual': total_actual,
            'total_variance': total_variance,
            'date_report': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        }

    def generate_xlsx_report(self, workbook, data, lines):
        """Generate Excel report"""
        sheet = workbook.add_workbook('Job Cost Report')
        bold = workbook.add_format({'bold': True})
        currency_fmt = workbook.add_format({'num_format': '#,##0.00'})
        percent_fmt = workbook.add_format({'num_format': '0.00%'})

        # Header
        sheet.write('A1', 'Job Cost Report', bold)
        sheet.write('A2', f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}')

        # Column headers
        headers = ['Project', 'Category', 'Product', 'Description',
                   'Budget Qty', 'Budget Amount', 'Actual Qty', 'Actual Cost',
                   'Committed Cost', 'Cost Variance', 'Completion %']

        row = 4
        for col, header in enumerate(headers):
            sheet.write(row, col, header, bold)

        # Data
        row = 5
        for line in lines:
            sheet.write(row, 0, line.project_id.name)
            sheet.write(row, 1, dict(line._fields['category'].selection).get(line.category, line.category))
            sheet.write(row, 2, line.product_id.name if line.product_id else '')
            sheet.write(row, 3, line.name)
            sheet.write(row, 4, line.budgeted_quantity)
            sheet.write(row, 5, line.budgeted_amount, currency_fmt)
            sheet.write(row, 6, line.actual_quantity)
            sheet.write(row, 7, line.actual_cost, currency_fmt)
            sheet.write(row, 8, line.committed_cost, currency_fmt)
            sheet.write(row, 9, line.cost_variance, currency_fmt)
            sheet.write(row, 10, line.completion_percentage / 100, percent_fmt)
            row += 1

        # Totals
        sheet.write(row, 4, 'TOTAL', bold)
        sheet.write(row, 5, f'=SUM(F{5}:F{row})', currency_fmt)
        sheet.write(row, 7, f'=SUM(H{5}:H{row})', currency_fmt)
        sheet.write(row, 8, f'=SUM(I{5}:I{row})', currency_fmt)
        sheet.write(row, 9, f'=SUM(J{5}:J{row})', currency_fmt)

        # Adjust column widths
        sheet.set_column('A:A', 30)
        sheet.set_column('B:B', 15)
        sheet.set_column('C:C', 25)
        sheet.set_column('D:D', 30)
        sheet.set_column('E:I', 15)
        sheet.set_column('J:J', 18)
        sheet.set_column('K:K', 15)
        