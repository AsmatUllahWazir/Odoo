# -*- coding: utf-8 -*-
"""
Patient Portal Controllers for LIMS
Handles public access for patients to view reports
"""
from odoo import http
from odoo.http import request, Response
from odoo.exceptions import AccessError
from odoo.tools import html_escape
import logging

_logger = logging.getLogger(__name__)


class LimsPortalControllers(http.Controller):
    """
    Patient portal controllers for public access    """

    @http.route('/lims/portal/login', type='http', auth='public', methods=['GET', 'POST'], website=True)
    def portal_login(self, **kwargs):
        """
        Patient portal login page
        """
        if request.httprequest.method == 'POST':
            patient_id = kwargs.get('patient_id', '').strip()
            access_token = kwargs.get('access_token', '').strip()

            if not patient_id or not access_token:
                return request.render('hospital_lims.portal_login', {
                    'error': 'Please enter both Patient ID and Access Token'
                })

            patient = request.env['lims.patient'].sudo().search([
                ('patient_id', '=', patient_id),
                ('access_token', '=', access_token)
            ])

            if not patient:
                return request.render('hospital_lims.portal_login', {
                    'error': 'Invalid Patient ID or Access Token. Please check and try again.'
                })

            # Redirect to patient portal
            return request.redirect(f'/lims/portal/patient/{patient.id}?token={access_token}')

        return request.render('hospital_lims.portal_login', {})

    @http.route('/lims/portal/patient/<int:patient_id>', type='http', auth='public', methods=['GET'], website=True)
    def portal_dashboard(self, patient_id, **kwargs):
        """
        Patient portal dashboard
        """
        try:
            access_token = kwargs.get('token')
            if not access_token:
                return request.redirect('/lims/portal/login')

            patient = request.env['lims.patient'].sudo().search([
                ('id', '=', patient_id),
                ('access_token', '=', access_token)
            ])

            if not patient:
                return request.render('hospital_lims.portal_access_denied', {})

            # Get active orders and reports
            orders = patient.test_order_ids.filtered(
                lambda o: o.state not in ['cancelled']
            )

            reports = patient.report_ids.filtered(
                lambda r: r.state in ['generated', 'sent', 'received']
            )

            return request.render('hospital_lims.portal_dashboard', {
                'patient': patient,
                'orders': orders,
                'reports': reports,
                'base_url': request.env['ir.config_parameter'].sudo().get_param('web.base.url'),
            })
        except Exception as e:
            _logger.error(f"Error in portal_dashboard: {str(e)}")
            return request.render('hospital_lims.portal_error', {'error': str(e)})

    @http.route('/lims/portal/report/<int:report_id>', type='http', auth='public', methods=['GET'], website=True)
    def portal_view_report(self, report_id, **kwargs):
        """
        View a specific report in the portal
        """
        try:
            access_token = kwargs.get('token')
            if not access_token:
                return request.redirect('/lims/portal/login')

            report = request.env['lims.report'].sudo().browse(report_id)
            if not report.exists():
                return request.render('hospital_lims.portal_error', {'error': 'Report not found'})

            # Verify access
            if report.patient_id.access_token != access_token:
                return request.render('hospital_lims.portal_access_denied', {})

            # Increment view count
            report.write({'view_count': report.view_count + 1})

            return request.render('hospital_lims.portal_report_view', {
                'report': report,
                'patient': report.patient_id,
                'base_url': request.env['ir.config_parameter'].sudo().get_param('web.base.url'),
            })
        except Exception as e:
            _logger.error(f"Error in portal_view_report: {str(e)}")
            return request.render('hospital_lims.portal_error', {'error': str(e)})

    @http.route('/lims/portal/report/download/<int:report_id>', type='http', auth='public', methods=['GET'])
    def portal_download_report(self, report_id, **kwargs):
        """
        Download report as PDF from portal
        """
        try:
            access_token = kwargs.get('token')
            if not access_token:
                return Response('Access denied', status=403)

            report = request.env['lims.report'].sudo().browse(report_id)
            if not report.exists():
                return Response('Report not found', status=404)

            # Verify access
            if report.patient_id.access_token != access_token:
                return Response('Access denied', status=403)

            # Generate PDF
            pdf_content, _ = request.env.ref('hospital_lims.action_report_lims_pdf').sudo()._render_qweb_pdf(
                [report.id])

            # Increment download count (use print_count for tracking)
            report.write({'print_count': report.print_count + 1})

            filename = f"LIMS_Report_{report.name}.pdf"

            return request.make_response(
                pdf_content,
                headers=[
                    ('Content-Type', 'application/pdf'),
                    ('Content-Disposition', f'attachment; filename="{filename}"'),
                ]
            )
        except Exception as e:
            _logger.error(f"Error in portal_download_report: {str(e)}")
            return Response('Error downloading report', status=500)

    @http.route('/lims/portal/order/<int:order_id>', type='http', auth='public', methods=['GET'], website=True)
    def portal_view_order(self, order_id, **kwargs):
        """
        View order details in the portal
        """
        try:
            access_token = kwargs.get('token')
            if not access_token:
                return request.redirect('/lims/portal/login')

            order = request.env['lims.test_order'].sudo().browse(order_id)
            if not order.exists():
                return request.render('hospital_lims.portal_error', {'error': 'Order not found'})

            # Verify access
            if order.patient_id.access_token != access_token:
                return request.render('hospital_lims.portal_access_denied', {})

            return request.render('hospital_lims.portal_order_view', {
                'order': order,
                'patient': order.patient_id,
                'lines': order.order_line_ids,
            })
        except Exception as e:
            _logger.error(f"Error in portal_view_order: {str(e)}")
            return request.render('hospital_lims.portal_error', {'error': str(e)})

    @http.route('/lims/portal/settings', type='http', auth='public', methods=['GET', 'POST'], website=True)
    def portal_settings(self, **kwargs):
        """
        Patient portal settings page
        """
        try:
            access_token = kwargs.get('token')
            if not access_token:
                return request.redirect('/lims/portal/login')

            patient_id = kwargs.get('patient_id')
            if not patient_id:
                return request.redirect('/lims/portal/login')

            patient = request.env['lims.patient'].sudo().search([
                ('id', '=', int(patient_id)),
                ('access_token', '=', access_token)
            ])

            if not patient:
                return request.render('hospital_lims.portal_access_denied', {})

            if request.httprequest.method == 'POST':
                # Update patient settings
                vals = {}
                if kwargs.get('email'):
                    vals['email'] = kwargs.get('email')
                if kwargs.get('phone'):
                    vals['phone'] = kwargs.get('phone')
                if kwargs.get('mobile'):
                    vals['mobile'] = kwargs.get('mobile')
                if kwargs.get('street'):
                    vals['street'] = kwargs.get('street')
                if kwargs.get('city'):
                    vals['city'] = kwargs.get('city')
                if kwargs.get('zip'):
                    vals['zip'] = kwargs.get('zip')

                if vals:
                    patient.write(vals)
                    return request.render('hospital_lims.portal_settings', {
                        'patient': patient,
                        'success': 'Settings updated successfully!',
                    })

            return request.render('hospital_lims.portal_settings', {
                'patient': patient,
            })
        except Exception as e:
            _logger.error(f"Error in portal_settings: {str(e)}")
            return request.render('hospital_lims.portal_error', {'error': str(e)})
        