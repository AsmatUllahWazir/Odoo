# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError
import logging
from datetime import datetime

_logger = logging.getLogger(__name__)


class ClosingReport(models.AbstractModel):
    """Project Closing Report PDF"""
    _name = 'report.construction_costing_suite.closing_report'
    _description = 'Project Closing Report'

    def _get_report_values(self, docids, data=None):
        """Prepare data for the report"""
        docs = self.env['close.project.wizard'].browse(docids)

        report_data = []
        for wizard in docs:
            project = wizard.project_id

            # Get all cost lines grouped by category
            categories = {}
            for line in project.job_cost_line_ids:
                cat = line.category
                if cat not in categories:
                    categories[cat] = {
                        'budgeted': 0.0,
                        'actual': 0.0,
                        'variance': 0.0,
                    }
                categories[cat]['budgeted'] += line.budgeted_amount
                categories[cat]['actual'] += line.actual_cost
                categories[cat]['variance'] += line.cost_variance

            # Get milestone summary
            milestones = project.milestone_ids
            completed_milestones = milestones.filtered(lambda m: m.is_completed)
            invoiced_milestones = milestones.filtered(lambda m: m.is_invoiced)

            report_data.append({
                'project': project,
                'wizard': wizard,
                'categories': categories,
                'milestones': {
                    'total': len(milestones),
                    'completed': len(completed_milestones),
                    'invoiced': len(invoiced_milestones),
                },
                'final_cost': wizard.final_cost,
                'final_billed': wizard.final_billed,
                'final_profit': wizard.final_profit,
                'profit_margin': wizard.profit_margin,
            })

        return {
            'doc_ids': docids,
            'doc_model': 'close.project.wizard',
            'docs': docs,
            'report_data': report_data,
            'date_report': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        }
