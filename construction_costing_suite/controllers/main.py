# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.exceptions import AccessError, MissingError
import logging

_logger = logging.getLogger(__name__)


class ConstructionPortal(CustomerPortal):
    """Portal controller for construction projects"""

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'construction_projects_count' in counters:
            values['construction_projects_count'] = self._get_construction_projects_count()
        return values

    def _get_construction_projects_count(self):
        user = request.env.user
        if user.has_group('construction_costing_suite.group_construction_user'):
            project_model = request.env['project.project']
            count = project_model.search_count([
                ('is_construction_project', '=', True),
                ('partner_id', '=', user.partner_id.id)
            ])
            return count
        return 0

    @http.route(['/my/construction/projects', '/my/construction/projects/page/<int:page>'],
                type='http', auth='user', website=True)
    def portal_construction_projects(self, page=1, sortby=None, search=None, **kw):
        values = self._prepare_portal_layout_values()
        user = request.env.user

        project_domain = [
            ('is_construction_project', '=', True),
            ('privacy_visibility', 'in', ['portal', 'followers'])
        ]

        if not user.has_group('construction_costing_suite.group_construction_manager'):
            project_domain += [('partner_id', '=', user.partner_id.id)]

        searchbar_sortings = {
            'name': {'label': 'Name', 'order': 'name asc'},
            'date': {'label': 'Start Date', 'order': 'date_start desc'},
            'status': {'label': 'Status', 'order': 'construction_status asc'},
            'progress': {'label': 'Progress', 'order': 'physical_completion desc'},
        }

        if not sortby:
            sortby = 'name'
        order = searchbar_sortings[sortby]['order']

        pager = portal_pager(
            url='/my/construction/projects',
            url_args={'sortby': sortby},
            total=request.env['project.project'].search_count(project_domain),
            page=page,
            step=self._items_per_page
        )

        projects = request.env['project.project'].search(
            project_domain,
            order=order,
            limit=self._items_per_page,
            offset=pager['offset']
        )

        values.update({
            'projects': projects,
            'page_name': 'construction_projects',
            'pager': pager,
            'sortby': sortby,
            'searchbar_sortings': searchbar_sortings,
            'default_url': '/my/construction/projects',
        })

        return request.render('construction_costing_suite.portal_construction_projects', values)

    @http.route('/my/construction/project/<int:project_id>', type='http', auth='user', website=True)
    def portal_construction_project_detail(self, project_id, **kw):
        try:
            project = request.env['project.project'].sudo().browse(project_id)
            if not project.exists():
                raise MissingError("Project not found.")

            if not project._check_access('read', raise_exception=False):
                raise AccessError("You don't have access to this project.")

            values = {
                'project': project,
                'boqs': project.boq_ids,
                'milestones': project.milestone_ids,
                'tasks': project.task_ids,
                'cost_lines': project.job_cost_line_ids,
                'requisitions': project.requisition_ids,
                'page_name': 'construction_project_detail',
                'breadcrumb': f"Project: {project.name}",
            }

            return request.render('construction_costing_suite.portal_construction_project_detail', values)

        except (AccessError, MissingError) as e:
            return request.redirect('/my')

    @http.route('/my/construction/project/<int:project_id>/boq/<int:boq_id>',
                type='http', auth='user', website=True)
    def portal_boq_detail(self, project_id, boq_id, **kw):
        try:
            boq = request.env['construction.boq'].sudo().browse(boq_id)
            if not boq.exists() or boq.project_id.id != project_id:
                raise MissingError("BOQ not found.")

            if not boq._check_access('read', raise_exception=False):
                raise AccessError("You don't have access to this BOQ.")

            values = {
                'boq': boq,
                'project': boq.project_id,
                'lines': boq.line_ids,
                'page_name': 'construction_boq_detail',
                'breadcrumb': f"BOQ: {boq.name}",
            }

            return request.render('construction_costing_suite.portal_boq_detail', values)

        except (AccessError, MissingError) as e:
            return request.redirect('/my')

    @http.route('/my/construction/project/<int:project_id>/milestone/<int:milestone_id>',
                type='http', auth='user', website=True)
    def portal_milestone_detail(self, project_id, milestone_id, **kw):
        try:
            milestone = request.env['construction.milestone'].sudo().browse(milestone_id)
            if not milestone.exists() or milestone.project_id.id != project_id:
                raise MissingError("Milestone not found.")

            if not milestone._check_access('read', raise_exception=False):
                raise AccessError("You don't have access to this milestone.")

            values = {
                'milestone': milestone,
                'project': milestone.project_id,
                'page_name': 'construction_milestone_detail',
                'breadcrumb': f"Milestone: {milestone.name}",
            }

            return request.render('construction_costing_suite.portal_milestone_detail', values)

        except (AccessError, MissingError) as e:
            return request.redirect('/my')
        