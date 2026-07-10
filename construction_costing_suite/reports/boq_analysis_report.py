# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError
import logging
from datetime import datetime

_logger = logging.getLogger(__name__)


class BOQAnalysisReport(models.AbstractModel):
    """BOQ Analysis Report PDF"""
    _name = 'report.construction_costing_suite.boq_analysis_report'
    _description = 'BOQ Analysis Report'
    _inherit = 'report.report_xlsx.abstract'

    def _get_report_values(self, docids, data=None):
        """Prepare data for the report"""
        docs = self.env['construction.boq'].browse(docids)

        boq_data = []
        for boq in docs:
            total_budget = boq.total
            total_actual = 0.0
            total_variance = 0.0

            lines_data = []
            for line in boq.line_ids:
                variance = line.subtotal - line.actual_cost
                var_percent = (variance / line.subtotal * 100) if line.subtotal > 0 else 0

                lines_data.append({
                    'product': line.product_id.name,
                    'category': dict(line._fields['category'].selection).get(line.category, line.category),
                    'quantity': line.quantity,
                    'unit_price': line.unit_price,
                    'budgeted': line.subtotal,
                    'actual': line.actual_cost,
                    'variance': variance,
                    'variance_percent': var_percent,
                })
                total_actual += line.actual_cost
                total_variance += variance

            boq_data.append({
                'boq': boq,
                'lines': lines_data,
                'total_budget': total_budget,
                'total_actual': total_actual,
                'total_variance': total_variance,
                'variance_percent': (total_variance / total_budget * 100) if total_budget > 0 else 0,
            })

        return {
            'doc_ids': docids,
            'doc_model': 'construction.boq',
            'docs': docs,
            'boq_data': boq_data,
            'date_report': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        }

    def generate_xlsx_report(self, workbook, data, boqs):
        """Generate Excel report"""
        sheet = workbook.add_workbook('BOQ Analysis')
        bold = workbook.add_format({'bold': True})
        currency_fmt = workbook.add_format({'num_format': '#,##0.00'})
        percent_fmt = workbook.add_format({'num_format': '0.00%'})
        variance_fmt = workbook.add_format({'num_format': '#,##0.00'})
        variance_red = workbook.add_format({'num_format': '#,##0.00', 'font_color': 'red'})
        variance_green = workbook.add_format({'num_format': '#,##0.00', 'font_color': 'green'})

        row = 0
        for boq_data in boq_data:
            boq = boq_data['boq']

            # BOQ Header
            sheet.write(row, 0, f'BOQ: {boq.name}', bold)
            row += 1
            sheet.write(row, 0, f'Project: {boq.project_id.name}')
            sheet.write(row, 1, f'Date: {boq.date}')
            sheet.write(row, 2, f'Status: {dict(boq._fields["state"].selection).get(boq.state, boq.state)}')
            row += 2

            # Column headers
            headers = ['Product', 'Category', 'Quantity', 'Unit Price',
                       'Budgeted Amount', 'Actual Cost', 'Variance', 'Variance %']
            for col, header in enumerate(headers):
                sheet.write(row, col, header, bold)
            row += 1

            # Lines
            for line in boq_data['lines']:
                sheet.write(row, 0, line['product'])
                sheet.write(row, 1, line['category'])
                sheet.write(row, 2, line['quantity'])
                sheet.write(row, 3, line['unit_price'], currency_fmt)
                sheet.write(row, 4, line['budgeted'], currency_fmt)
                sheet.write(row, 5, line['actual'], currency_fmt)

                variance_fmt_used = variance_green if line['variance'] >= 0 else variance_red
                sheet.write(row, 6, line['variance'], variance_fmt_used)
                sheet.write(row, 7, line['variance_percent'] / 100, percent_fmt)
                row += 1

            # Totals
            sheet.write(row, 3, 'TOTAL', bold)
            sheet.write(row, 4, boq_data['total_budget'], currency_fmt)
            sheet.write(row, 5, boq_data['total_actual'], currency_fmt)

            variance_fmt_used = variance_green if boq_data['total_variance'] >= 0 else variance_red
            sheet.write(row, 6, boq_data['total_variance'], variance_fmt_used)
            sheet.write(row, 7, boq_data['variance_percent'] / 100, percent_fmt)
            row += 2

            # Summary statistics
            sheet.write(row, 0, 'Summary:', bold)
            row += 1
            sheet.write(row, 0, f'Total Items: {len(boq_data["lines"])}')
            sheet.write(row, 1, f'On Budget Items: {len([l for l in boq_data["lines"] if l["variance"] >= 0])}')
            sheet.write(row, 2, f'Over Budget Items: {len([l for l in boq_data["lines"] if l["variance"] < 0])}')
            row += 2

            # Add some spacing between BOQs
            row += 1

        # Adjust column widths
        sheet.set_column('A:A', 30)
        sheet.set_column('B:B', 20)
        sheet.set_column('C:G', 18)
        sheet.set_column('H:H', 15)
