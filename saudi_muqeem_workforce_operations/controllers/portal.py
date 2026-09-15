from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal

class SaudiCompliancePortal(CustomerPortal):

    def _employee(self):
        return request.env['hr.employee'].sudo().search([('user_id', '=', request.env.user.id)], limit=1)

    @http.route(['/my/muqeem', '/my/muqeem/dashboard'], type='http', auth='user', website=True)
    def muqeem_dashboard(self, **kw):
        employee = self._employee()
        if not employee:
            return request.redirect('/my/home')
        profile = request.env['muqeem.workforce.profile'].sudo().search([('employee_id', '=', employee.id)], limit=1)
        if not profile:
            return request.render('saudi_muqeem_workforce_operations.muqeem_portal_empty', {'employee': employee})
        return request.render('saudi_muqeem_workforce_operations.muqeem_portal_dashboard', {'profile': profile, 'employee': employee})

    @http.route(['/my/muqeem/service/new'], type='http', auth='user', website=True, methods=['GET', 'POST'], csrf=True)
    def muqeem_new_service(self, **post):
        employee = self._employee()
        profile = request.env['muqeem.workforce.profile'].sudo().search([('employee_id', '=', employee.id)], limit=1) if employee else False
        if not profile:
            return request.redirect('/my/home')
        if request.httprequest.method == 'POST':
            request.env['muqeem.service.request'].sudo().create({'profile_id': profile.id, 'service_code': post.get('service_code'), 'notes': post.get('notes')})
            return request.redirect('/my/muqeem')
        return request.render('saudi_muqeem_workforce_operations.muqeem_portal_new_service', {'profile': profile})
