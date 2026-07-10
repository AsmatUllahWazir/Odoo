# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from datetime import timedelta

class ConstructionDashboard(models.Model):
    _name = 'construction.dashboard'
    _description = 'Construction Dashboard'
    _rec_name = 'project_id'
    _auto = True  # This ensures the table is created

    project_id = fields.Many2one('project.project', string='Project', required=True)

    total_budget = fields.Monetary(string='Total Budget', compute='_compute_kpis', currency_field='currency_id')
    total_actual_cost = fields.Monetary(string='Total Actual Cost', compute='_compute_kpis', currency_field='currency_id')
    total_billed = fields.Monetary(string='Total Billed', compute='_compute_kpis', currency_field='currency_id')
    total_committed = fields.Monetary(string='Total Committed', compute='_compute_kpis', currency_field='currency_id')
    profit_margin = fields.Float(string='Profit Margin %', compute='_compute_kpis', digits=(16, 2))
    cost_variance = fields.Monetary(string='Cost Variance', compute='_compute_kpis', currency_field='currency_id')
    physical_completion = fields.Float(string='Physical Completion %', compute='_compute_kpis', digits=(16, 2))
    financial_completion = fields.Float(string='Financial Completion %', compute='_compute_kpis', digits=(16, 2))

    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)

    category_cost_data = fields.Text(string='Cost by Category', compute='_compute_graph_data')
    monthly_cost_data = fields.Text(string='Monthly Cost Trend', compute='_compute_graph_data')

    # def default_get(self, fields_list):
    #     res = super(ConstructionDashboard, self).default_get(fields_list)
    #     active_id = self.env.context.get('active_id')
    #     if active_id and self.env.context.get('active_model') == 'project.project':
    #         project = self.env['project.project'].browse(active_id)
    #         res['project_id'] = project.id
    #     return res

    def _compute_kpis(self):
        for dashboard in self:
            project = dashboard.project_id
            if project:
                dashboard.total_budget = project.total_budget or 0.0
                dashboard.total_actual_cost = project.total_actual_cost or 0.0
                dashboard.total_billed = project.total_billed or 0.0
                dashboard.total_committed = project.total_committed or 0.0
                dashboard.physical_completion = project.physical_completion or 0.0
                dashboard.financial_completion = project.financial_completion or 0.0
                dashboard.cost_variance = project.cost_variance or 0.0

                if dashboard.total_billed > 0 and dashboard.total_actual_cost > 0:
                    dashboard.profit_margin = ((dashboard.total_billed - dashboard.total_actual_cost) / dashboard.total_billed) * 100
                else:
                    dashboard.profit_margin = 0.0

    def _compute_graph_data(self):
        for dashboard in self:
            project = dashboard.project_id
            if not project:
                continue

            category_data = {}
            for cost_line in project.job_cost_line_ids:
                cat = cost_line.category or 'other'
                if cat not in category_data:
                    category_data[cat] = 0.0
                category_data[cat] += cost_line.actual_cost

            dashboard.category_cost_data = str([
                {'label': k, 'value': v}
                for k, v in category_data.items()
            ])

            today = fields.Date.today()
            monthly_data = []
            for i in range(6):
                month_date = today - timedelta(days=30 * i)
                month_start = month_date.replace(day=1)
                month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)

                monthly_lines = project.job_cost_line_ids.filtered(
                    lambda l: l.create_date and month_start <= l.create_date.date() <= month_end
                )
                monthly_total = sum(monthly_lines.mapped('actual_cost'))

                monthly_data.append({
                    'month': month_start.strftime('%b %Y'),
                    'cost': monthly_total
                })

            dashboard.monthly_cost_data = str(monthly_data[-6:])

    def action_refresh_dashboard(self):
        self._compute_kpis()
        self._compute_graph_data()
        return True

    def action_view_project(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'project.project',
            'res_id': self.project_id.id,
            'view_mode': 'form',
        }


class ConstructionProjectAnalytics(models.TransientModel):
    _name = 'construction.project.analytics'
    _description = 'Project Analytics'

    date_from = fields.Date(string='From Date', required=True)
    date_to = fields.Date(string='To Date', required=True)
    project_ids = fields.Many2many('project.project', string='Projects', required=True)

    total_projects = fields.Integer(compute='_compute_analytics', string='Total Projects')
    total_budget = fields.Monetary(compute='_compute_analytics', string='Total Budget', currency_field='currency_id')
    total_actual_cost = fields.Monetary(compute='_compute_analytics', string='Total Actual Cost', currency_field='currency_id')
    total_billed = fields.Monetary(compute='_compute_analytics', string='Total Billed', currency_field='currency_id')
    average_profit_margin = fields.Float(compute='_compute_analytics', string='Avg Profit Margin %', digits=(16, 2))
    completed_projects = fields.Integer(compute='_compute_analytics', string='Completed Projects')
    in_progress_projects = fields.Integer(compute='_compute_analytics', string='In Progress')

    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)

    def _compute_analytics(self):
        for analytics in self:
            projects = analytics.project_ids.filtered(lambda p: p.is_construction_project)

            analytics.total_projects = len(projects)
            analytics.total_budget = sum(projects.mapped('total_budget'))
            analytics.total_actual_cost = sum(projects.mapped('total_actual_cost'))
            analytics.total_billed = sum(projects.mapped('total_billed'))
            analytics.completed_projects = len(projects.filtered(lambda p: p.construction_status == 'completed'))
            analytics.in_progress_projects = len(projects.filtered(lambda p: p.construction_status == 'in_progress'))

            profit_margins = []
            for project in projects:
                if project.total_billed > 0 and project.total_actual_cost > 0:
                    margin = ((project.total_billed - project.total_actual_cost) / project.total_billed) * 100
                    profit_margins.append(margin)

            if profit_margins:
                analytics.average_profit_margin = sum(profit_margins) / len(profit_margins)
            else:
                analytics.average_profit_margin = 0.0

    def action_view_details(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'project.project',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.project_ids.ids)],
        }
