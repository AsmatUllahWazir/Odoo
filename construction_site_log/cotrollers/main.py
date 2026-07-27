# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request
from odoo.addons.web.controllers.main import Home


class ConstructionSiteController(Home):

    @http.route('/construction/dashboard', type='http', auth='user', website=True)
    def construction_dashboard(self, **kwargs):
        """Main construction dashboard."""
        user = request.env.user

        # Get statistics
        Log = request.env['construction.site.daily.log']
        Obs = request.env['construction.safety.observation']
        Inc = request.env['construction.incident.report']
        Talk = request.env['construction.toolbox.talk']

        today = fields.Date.today()
        week_start = today - timedelta(days=7)

        # Daily logs
        total_logs = Log.search_count([])
        my_logs = Log.search_count([('site_supervisor_id.user_id', '=', user.id)])
        today_logs = Log.search_count([('date', '=', today)])
        week_logs = Log.search_count([('date', '>=', week_start)])
        pending_approval = Log.search_count([('state', '=', 'submitted')])

        # Safety observations
        total_obs = Obs.search_count([])
        open_obs = Obs.search_count([('status', 'in', ['open', 'in_progress'])])
        critical_obs = Obs.search_count([('severity', 'in', ['high', 'critical'])])
        my_obs = Obs.search_count([('responsible_person_id.user_id', '=', user.id)])

        # Incidents
        total_inc = Inc.search_count([])
        open_inc = Inc.search_count([('status', 'in', ['draft', 'under_investigation'])])
        my_inc = Inc.search_count([('investigation_lead_id.user_id', '=', user.id)])

        # Toolbox talks
        total_talks = Talk.search_count([])
        today_talks = Talk.search_count([('date', '=', today)])
        my_talks = Talk.search_count([('presenter_id.user_id', '=', user.id)])

        # Recent activities
        recent_logs = Log.search([], limit=5, order='create_date desc')
        recent_obs = Obs.search([], limit=5, order='create_date desc')
        recent_inc = Inc.search([], limit=5, order='create_date desc')

        values = {
            'user': user,
            'total_logs': total_logs,
            'my_logs': my_logs,
            'today_logs': today_logs,
            'week_logs': week_logs,
            'pending_approval': pending_approval,
            'total_obs': total_obs,
            'open_obs': open_obs,
            'critical_obs': critical_obs,
            'my_obs': my_obs,
            'total_inc': total_inc,
            'open_inc': open_inc,
            'my_inc': my_inc,
            'total_talks': total_talks,
            'today_talks': today_talks,
            'my_talks': my_talks,
            'recent_logs': recent_logs,
            'recent_obs': recent_obs,
            'recent_inc': recent_inc,
        }

        return request.render('construction_site_log.portal_dashboard', values)

    @http.route('/construction/daily_log/<int:log_id>', type='http', auth='user', website=True)
    def construction_daily_log_view(self, log_id, **kwargs):
        """View a specific daily log."""
        log = request.env['construction.site.daily.log'].sudo().browse(log_id)

        if not log.exists():
            return request.not_found()

        # Check access
        user = request.env.user
        if not request.env.user.has_group('construction_site_log.group_construction_site_worker'):
            return request.not_found()

        values = {
            'log': log,
            'user': user,
        }

        return request.render('construction_site_log.portal_daily_log_view', values)

    @http.route('/construction/safety_observation/<int:obs_id>', type='http', auth='user', website=True)
    def construction_safety_observation_view(self, obs_id, **kwargs):
        """View a specific safety observation."""
        obs = request.env['construction.safety.observation'].sudo().browse(obs_id)

        if not obs.exists():
            return request.not_found()

        values = {
            'observation': obs,
            'user': request.env.user,
        }

        return request.render('construction_site_log.portal_safety_observation_view', values)

    @http.route('/construction/incident_report/<int:inc_id>', type='http', auth='user', website=True)
    def construction_incident_report_view(self, inc_id, **kwargs):
        """View a specific incident report."""
        inc = request.env['construction.incident.report'].sudo().browse(inc_id)

        if not inc.exists():
            return request.not_found()

        values = {
            'incident': inc,
            'user': request.env.user,
        }

        return request.render('construction_site_log.portal_incident_report_view', values)

    @http.route('/construction/toolbox_talk/<int:talk_id>', type='http', auth='user', website=True)
    def construction_toolbox_talk_view(self, talk_id, **kwargs):
        """View a specific toolbox talk."""
        talk = request.env['construction.toolbox.talk'].sudo().browse(talk_id)

        if not talk.exists():
            return request.not_found()

        values = {
            'talk': talk,
            'user': request.env.user,
        }

        return request.render('construction_site_log.portal_toolbox_talk_view', values)

    @http.route('/construction/reports', type='http', auth='user', website=True)
    def construction_reports(self, **kwargs):
        """Construction reports page."""
        values = {
            'user': request.env.user,
        }
        return request.render('construction_site_log.portal_reports', values)
