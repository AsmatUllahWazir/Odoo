# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import pager as portal_pager
from odoo.addons.portal.controllers import portal
from datetime import datetime, timedelta


class ConstructionPortal(portal.CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)

        if 'construction_log_count' in counters:
            values['construction_log_count'] = request.env['construction.site.daily.log'].search_count([
                ('site_supervisor_id.user_id', '=', request.env.user.id)
            ])

        if 'construction_obs_count' in counters:
            values['construction_obs_count'] = request.env['construction.safety.observation'].search_count([
                ('responsible_person_id.user_id', '=', request.env.user.id)
            ])

        if 'construction_inc_count' in counters:
            values['construction_inc_count'] = request.env['construction.incident.report'].search_count([
                ('investigation_lead_id.user_id', '=', request.env.user.id)
            ])

        return values

    @http.route(['/my/construction/daily_logs', '/my/construction/daily_logs/page/<int:page>'],
                type='http', auth='user', website=True)
    def portal_my_daily_logs(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):
        """My daily logs portal page."""
        values = self._prepare_portal_layout_values()
        user = request.env.user

        domain = [('site_supervisor_id.user_id', '=', user.id)]

        if date_begin and date_end:
            domain += [('date', '>=', date_begin), ('date', '<=', date_end)]

        # Sort
        if sortby == 'date_desc':
            order = 'date desc, name desc'
        elif sortby == 'date_asc':
            order = 'date asc'
        elif sortby == 'status':
            order = 'state desc, date desc'
        else:
            order = 'date desc, name desc'

        # Pager
        Log = request.env['construction.site.daily.log']
        log_count = Log.search_count(domain)
        pager = portal_pager(
            url="/my/construction/daily_logs",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby},
            total=log_count,
            page=page,
            step=self._items_per_page
        )

        logs = Log.search(domain, order=order, limit=self._items_per_page, offset=pager['offset'])

        values.update({
            'logs': logs,
            'page_name': 'daily_logs',
            'pager': pager,
            'date_begin': date_begin,
            'date_end': date_end,
            'sortby': sortby,
            'default_url': '/my/construction/daily_logs',
        })

        return request.render('construction_site_log.portal_my_daily_logs', values)

    @http.route(['/my/construction/safety_observations', '/my/construction/safety_observations/page/<int:page>'],
                type='http', auth='user', website=True)
    def portal_my_safety_observations(self, page=1, **kw):
        """My safety observations portal page."""
        values = self._prepare_portal_layout_values()
        user = request.env.user

        domain = [('responsible_person_id.user_id', '=', user.id)]

        # Pager
        Obs = request.env['construction.safety.observation']
        obs_count = Obs.search_count(domain)
        pager = portal_pager(
            url="/my/construction/safety_observations",
            total=obs_count,
            page=page,
            step=self._items_per_page
        )

        obs = Obs.search(domain, order='date desc, create_date desc',
                         limit=self._items_per_page, offset=pager['offset'])

        values.update({
            'observations': obs,
            'page_name': 'safety_observations',
            'pager': pager,
            'default_url': '/my/construction/safety_observations',
        })

        return request.render('construction_site_log.portal_my_safety_observations', values)

    @http.route(['/my/construction/incident_reports', '/my/construction/incident_reports/page/<int:page>'],
                type='http', auth='user', website=True)
    def portal_my_incident_reports(self, page=1, **kw):
        """My incident reports portal page."""
        values = self._prepare_portal_layout_values()
        user = request.env.user

        domain = [('investigation_lead_id.user_id', '=', user.id)]

        # Pager
        Inc = request.env['construction.incident.report']
        inc_count = Inc.search_count(domain)
        pager = portal_pager(
            url="/my/construction/incident_reports",
            total=inc_count,
            page=page,
            step=self._items_per_page
        )

        incs = Inc.search(domain, order='date desc, create_date desc',
                          limit=self._items_per_page, offset=pager['offset'])

        values.update({
            'incidents': incs,
            'page_name': 'incident_reports',
            'pager': pager,
            'default_url': '/my/construction/incident_reports',
        })

        return request.render('construction_site_log.portal_my_incident_reports', values)

    @http.route('/my/construction/daily_log/<int:log_id>', type='http', auth='user', website=True)
    def portal_daily_log_detail(self, log_id, **kw):
        """Daily log detail page."""
        log = request.env['construction.site.daily.log'].sudo().browse(log_id)

        if not log.exists():
            return request.not_found()

        # Check if user has access
        user = request.env.user
        if (log.site_supervisor_id.user_id != user and
                not user.has_group('construction_site_log.group_construction_project_manager')):
            return request.not_found()

        values = {
            'log': log,
            'user': user,
            'page_name': 'daily_log_detail',
        }

        return request.render('construction_site_log.portal_daily_log_detail', values)

    @http.route('/my/construction/submit_log/<int:log_id>', type='http', auth='user', website=True, methods=['POST'])
    def portal_submit_log(self, log_id, **kw):
        """Submit a daily log from portal."""
        log = request.env['construction.site.daily.log'].sudo().browse(log_id)

        if not log.exists():
            return request.not_found()

        if log.site_supervisor_id.user_id != request.env.user:
            return request.not_found()

        try:
            log.action_submit()
            return request.redirect('/my/construction/daily_log/%d?message=submitted' % log_id)
        except Exception as e:
            return request.redirect('/my/construction/daily_log/%d?error=%s' % (log_id, str(e)))

    @http.route('/construction/portal/share/<int:log_id>', type='http', auth='public', website=True)
    def portal_share_log(self, log_id, token=None, **kw):
        """Public share page for a log."""
        portal_log = request.env['construction.portal.log'].sudo().search([
            ('daily_log_id', '=', log_id)
        ], limit=1)

        if not portal_log:
            return request.not_found()

        if token != portal_log.share_token:
            return request.not_found()

        log = portal_log.daily_log_id

        # Record view
        portal_log.action_record_view()

        values = {
            'log': log,
            'portal_log': portal_log,
            'is_public': True,
        }

        return request.render('construction_site_log.portal_shared_log', values)

    @http.route('/construction/download_log_pdf/<int:log_id>', type='http', auth='user', website=True)
    def portal_download_log_pdf(self, log_id, **kw):
        """Download log PDF from portal."""
        log = request.env['construction.site.daily.log'].sudo().browse(log_id)

        if not log.exists():
            return request.not_found()

        # Check access
        user = request.env.user
        if (log.site_supervisor_id.user_id != user and
                not user.has_group('construction_site_log.group_construction_project_manager')):
            return request.not_found()

        return log.action_generate_report()
