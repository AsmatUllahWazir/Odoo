# -*- coding: utf-8 -*-
"""
Controllers Module for LIMS
Handles web routes, API endpoints, and file downloads
"""
from odoo import http
from odoo.http import request, Response
from odoo.exceptions import AccessError, ValidationError
from odoo.tools import html_escape
import base64
import json
import io
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)


class LimsControllers(http.Controller):
    """
    Main controllers for LIMS module
    Handles web routes for reports, barcodes, and API endpoints
    """

    # ===================== REPORT ENDPOINTS =====================

    @http.route('/lims/report/download/<int:report_id>', type='http', auth='user', methods=['GET'])
    def download_report_pdf(self, report_id, **kwargs):
        """
        Download report as PDF
        """
        try:
            report = request.env['lims.report'].sudo().browse(report_id)
            if not report.exists():
                return Response('Report not found', status=404)

            # Generate PDF
            pdf_content, _ = request.env.ref('hospital_lims.action_report_lims_pdf').sudo()._render_qweb_pdf(
                [report.id])

            # Create filename
            filename = f"LIMS_Report_{report.name}_{datetime.now().strftime('%Y%m%d')}.pdf"

            # Return PDF
            return request.make_response(
                pdf_content,
                headers=[
                    ('Content-Type', 'application/pdf'),
                    ('Content-Disposition', f'attachment; filename="{filename}"'),
                ]
            )
        except Exception as e:
            _logger.error(f"Error downloading report: {str(e)}")
            return Response('Error generating report', status=500)

    @http.route('/lims/report/preview/<int:report_id>', type='http', auth='user', methods=['GET'])
    def preview_report_pdf(self, report_id, **kwargs):
        """
        Preview report in browser
        """
        try:
            report = request.env['lims.report'].sudo().browse(report_id)
            if not report.exists():
                return Response('Report not found', status=404)

            # Generate PDF
            pdf_content, _ = request.env.ref('hospital_lims.action_report_lims_pdf').sudo()._render_qweb_pdf(
                [report.id])

            # Return PDF for inline display
            return request.make_response(
                pdf_content,
                headers=[
                    ('Content-Type', 'application/pdf'),
                    ('Content-Disposition', 'inline; filename="report.pdf"'),
                ]
            )
        except Exception as e:
            _logger.error(f"Error previewing report: {str(e)}")
            return Response('Error generating report', status=500)

    @http.route('/lims/report/print/<int:report_id>', type='http', auth='user', methods=['GET'])
    def print_report(self, report_id, **kwargs):
        """
        Print report directly (increment print count)
        """
        try:
            report = request.env['lims.report'].sudo().browse(report_id)
            if not report.exists():
                return Response('Report not found', status=404)

            # Increment print count
            report.write({'print_count': report.print_count + 1})

            # Generate PDF
            pdf_content, _ = request.env.ref('hospital_lims.action_report_lims_pdf').sudo()._render_qweb_pdf(
                [report.id])

            return request.make_response(
                pdf_content,
                headers=[
                    ('Content-Type', 'application/pdf'),
                    ('Content-Disposition', f'attachment; filename="LIMS_Report_{report.name}.pdf"'),
                ]
            )
        except Exception as e:
            _logger.error(f"Error printing report: {str(e)}")
            return Response('Error printing report', status=500)

    # ===================== BARCODE ENDPOINTS =====================

    @http.route('/lims/barcode/generate/<string:barcode_data>', type='http', auth='user', methods=['GET'])
    def generate_barcode(self, barcode_data, **kwargs):
        """
        Generate barcode image for given data
        """
        try:
            import barcode
            from barcode.writer import ImageWriter
            from io import BytesIO

            # Generate barcode
            code = barcode.get_barcode_class('code128')
            barcode_instance = code(barcode_data, writer=ImageWriter())
            buffer = BytesIO()
            barcode_instance.write(buffer, {
                'format': 'PNG',
                'module_width': 0.2,
                'module_height': 15,
                'quiet_zone': 6,
                'font_size': 8,
                'text_distance': 5,
                'background': 'white',
                'foreground': 'black',
            })
            buffer.seek(0)

            # Return image
            return request.make_response(
                buffer.getvalue(),
                headers=[
                    ('Content-Type', 'image/png'),
                    ('Content-Disposition', 'inline; filename="barcode.png"'),
                ]
            )
        except ImportError:
            _logger.warning("python-barcode library not installed")
            # Return a simple text-based barcode as fallback
            return self._generate_text_barcode(barcode_data)
        except Exception as e:
            _logger.error(f"Error generating barcode: {str(e)}")
            return self._generate_text_barcode(barcode_data)

    def _generate_text_barcode(self, data):
        """Generate a simple text-based barcode as fallback"""
        html = f"""
        <html>
        <head><title>Barcode</title></head>
        <body style="font-family: monospace; text-align: center; padding: 40px;">
            <div style="font-size: 48px; letter-spacing: 4px; font-weight: bold;">
                {'*' + data + '*'}
            </div>
            <div style="margin-top: 10px; font-size: 14px; font-family: Arial;">
                {data}
            </div>
            <div style="margin-top: 20px; color: #999; font-size: 12px;">
                (Barcode library not available - text representation)
            </div>
        </body>
        </html>
        """
        return request.make_response(html, headers=[('Content-Type', 'text/html')])

    @http.route('/lims/barcode/sample/<int:sample_id>', type='http', auth='user', methods=['GET'])
    def generate_sample_barcode(self, sample_id, **kwargs):
        """
        Generate barcode for a specific sample
        """
        try:
            sample = request.env['lims.sample'].sudo().browse(sample_id)
            if not sample.exists():
                return Response('Sample not found', status=404)

            if not sample.barcode:
                # Generate barcode if not exists
                sample.write({
                    'barcode': f"SMP{datetime.now().strftime('%Y%m%d')}{sample.id}"
                })

            return self.generate_barcode(sample.barcode)
        except Exception as e:
            _logger.error(f"Error generating sample barcode: {str(e)}")
            return Response('Error generating barcode', status=500)

    # ===================== API ENDPOINTS =====================

    @http.route('/lims/api/orders/pending', type='json', auth='user', methods=['GET'])
    def api_pending_orders(self, **kwargs):
        """
        API endpoint to get pending orders
        """
        try:
            orders = request.env['lims.test_order'].sudo().search([
                ('state', 'in', ['draft', 'confirmed', 'sample_collection', 'in_progress']),
                ('priority', 'in', ['urgent', 'emergency', 'stat'])
            ])

            result = []
            for order in orders:
                result.append({
                    'id': order.id,
                    'order_id': order.order_id,
                    'patient_name': order.patient_name,
                    'priority': order.priority,
                    'date_ordered': order.date_ordered.isoformat() if order.date_ordered else None,
                    'total_tests': order.total_tests,
                    'completion_percentage': order.completion_percentage,
                    'is_overdue': order.is_overdue,
                })

            return {
                'status': 'success',
                'data': result,
                'count': len(result),
            }
        except Exception as e:
            _logger.error(f"Error in api_pending_orders: {str(e)}")
            return {'status': 'error', 'message': str(e)}

    @http.route('/lims/api/orders/statistics', type='json', auth='user', methods=['GET'])
    def api_order_statistics(self, **kwargs):
        """
        API endpoint to get order statistics
        """
        try:
            dashboard = request.env['lims.dashboard'].sudo()
            stats = dashboard.get_dashboard_data()
            return {
                'status': 'success',
                'data': stats,
            }
        except Exception as e:
            _logger.error(f"Error in api_order_statistics: {str(e)}")
            return {'status': 'error', 'message': str(e)}

    @http.route('/lims/api/patient/search', type='json', auth='user', methods=['POST'])
    def api_search_patients(self, **kwargs):
        """
        API endpoint to search patients
        """
        try:
            search_term = kwargs.get('search_term', '')
            limit = int(kwargs.get('limit', 20))

            if not search_term:
                return {'status': 'error', 'message': 'Search term required'}

            patients = request.env['lims.patient'].sudo().search([
                '|',
                ('name', 'ilike', search_term),
                ('patient_id', 'ilike', search_term)
            ], limit=limit)

            result = []
            for patient in patients:
                result.append({
                    'id': patient.id,
                    'patient_id': patient.patient_id,
                    'name': patient.name,
                    'age': patient.age,
                    'gender': patient.gender,
                    'phone': patient.phone,
                    'email': patient.email,
                    'blood_type': patient.blood_type,
                })

            return {
                'status': 'success',
                'data': result,
                'count': len(result),
            }
        except Exception as e:
            _logger.error(f"Error in api_search_patients: {str(e)}")
            return {'status': 'error', 'message': str(e)}

    @http.route('/lims/api/qc/recent', type='json', auth='user', methods=['GET'])
    def api_recent_qc(self, **kwargs):
        """
        API endpoint to get recent QC records
        """
        try:
            limit = int(kwargs.get('limit', 10))

            qcs = request.env['lims.quality_control'].sudo().search([
                ('state', 'in', ['approved', 'review'])
            ], limit=limit, order='date desc')

            result = []
            for qc in qcs:
                result.append({
                    'id': qc.id,
                    'name': qc.name,
                    'test_type': qc.test_type_name,
                    'date': qc.date.isoformat() if qc.date else None,
                    'result_value': qc.result_value,
                    'target_value': qc.target_value,
                    'is_passed': qc.is_passed,
                    'deviation_percentage': qc.deviation_percentage,
                    'technician': qc.technician_id.name if qc.technician_id else None,
                })

            return {
                'status': 'success',
                'data': result,
                'count': len(result),
            }
        except Exception as e:
            _logger.error(f"Error in api_recent_qc: {str(e)}")
            return {'status': 'error', 'message': str(e)}

    @http.route('/lims/api/test_types', type='json', auth='user', methods=['GET'])
    def api_test_types(self, **kwargs):
        """
        API endpoint to get active test types
        """
        try:
            test_types = request.env['lims.test_type'].sudo().search([
                ('active', '=', True)
            ])

            result = []
            for tt in test_types:
                result.append({
                    'id': tt.id,
                    'name': tt.name,
                    'code': tt.code,
                    'price': tt.price,
                    'category': tt.category,
                    'required_sample_type': tt.required_sample_type,
                    'turnaround_time': tt.turnaround_time,
                })

            return {
                'status': 'success',
                'data': result,
                'count': len(result),
            }
        except Exception as e:
            _logger.error(f"Error in api_test_types: {str(e)}")
            return {'status': 'error', 'message': str(e)}

    # ===================== WEBHOOK ENDPOINTS =====================

    @http.route('/lims/webhook/order/update', type='json', auth='public', methods=['POST'], csrf=False)
    def webhook_update_order(self, **kwargs):
        """
        Webhook endpoint for external systems to update order status
        """
        try:
            # Validate API key
            api_key = kwargs.get('api_key')
            config_key = request.env['ir.config_parameter'].sudo().get_param('lims.webhook_api_key', default='')

            if api_key != config_key:
                return {'status': 'error', 'message': 'Invalid API key'}

            order_id = kwargs.get('order_id')
            status = kwargs.get('status')

            if not order_id or not status:
                return {'status': 'error', 'message': 'order_id and status required'}

            order = request.env['lims.test_order'].sudo().browse(int(order_id))
            if not order.exists():
                return {'status': 'error', 'message': 'Order not found'}

            # Map status
            status_map = {
                'confirmed': 'confirmed',
                'processing': 'in_progress',
                'completed': 'reported',
                'cancelled': 'cancelled',
                'on_hold': 'on_hold',
            }

            mapped_status = status_map.get(status)
            if not mapped_status:
                return {'status': 'error', 'message': f'Invalid status: {status}'}

            # Update order
            order.write({'state': mapped_status})

            return {
                'status': 'success',
                'message': f'Order {order.order_id} updated to {mapped_status}',
                'data': {
                    'order_id': order.order_id,
                    'new_state': mapped_status,
                }
            }
        except Exception as e:
            _logger.error(f"Error in webhook_update_order: {str(e)}")
            return {'status': 'error', 'message': str(e)}

    @http.route('/lims/webhook/result/update', type='json', auth='public', methods=['POST'], csrf=False)
    def webhook_update_result(self, **kwargs):
        """
        Webhook endpoint for external systems to update test results
        """
        try:
            # Validate API key
            api_key = kwargs.get('api_key')
            config_key = request.env['ir.config_parameter'].sudo().get_param('lims.webhook_api_key', default='')

            if api_key != config_key:
                return {'status': 'error', 'message': 'Invalid API key'}

            order_line_id = kwargs.get('order_line_id')
            result_value = kwargs.get('result_value')
            result_text = kwargs.get('result_text')

            if not order_line_id:
                return {'status': 'error', 'message': 'order_line_id required'}

            line = request.env['lims.test_order_line'].sudo().browse(int(order_line_id))
            if not line.exists():
                return {'status': 'error', 'message': 'Test line not found'}

            # Update result
            vals = {}
            if result_value is not None:
                vals['result_value'] = float(result_value)
            if result_text:
                vals['result_text'] = result_text
            vals['result_date'] = datetime.now()
            vals['state'] = 'completed'

            line.write(vals)

            return {
                'status': 'success',
                'message': f'Result updated for test line {line.id}',
                'data': {
                    'line_id': line.id,
                    'result_value': line.result_value,
                    'result_text': line.result_text,
                    'is_abnormal': line.is_abnormal,
                }
            }
        except Exception as e:
            _logger.error(f"Error in webhook_update_result: {str(e)}")
            return {'status': 'error', 'message': str(e)}

    # ===================== PATIENT PORTAL ENDPOINTS =====================

    @http.route('/lims/portal/patient/<int:patient_id>', type='http', auth='public', methods=['GET'])
    def patient_portal(self, patient_id, **kwargs):
        """
        Simple patient portal page to view reports
        """
        try:
            # Check access token
            access_token = kwargs.get('token')
            if not access_token:
                return request.render('hospital_lims.portal_access_denied', {})

            patient = request.env['lims.patient'].sudo().search([
                ('id', '=', patient_id),
                ('access_token', '=', access_token)
            ])

            if not patient:
                return request.render('hospital_lims.portal_access_denied', {})

            # Get reports
            reports = patient.report_ids.filtered(lambda r: r.state in ['generated', 'sent', 'received'])

            # Render portal page
            return request.render('hospital_lims.portal_patient_page', {
                'patient': patient,
                'orders': patient.test_order_ids,
                'reports': reports,
                'base_url': request.env['ir.config_parameter'].sudo().get_param('web.base.url'),
            })
        except Exception as e:
            _logger.error(f"Error in patient_portal: {str(e)}")
            return request.render('hospital_lims.portal_error', {'error': str(e)})

    @http.route('/lims/portal/report/<int:report_id>', type='http', auth='public', methods=['GET'])
    def portal_view_report(self, report_id, **kwargs):
        """
        Public portal endpoint to view a report
        """
        try:
            access_token = kwargs.get('token')
            if not access_token:
                return Response('Access denied', status=403)

            report = request.env['lims.report'].sudo().browse(report_id)
            if not report.exists():
                return Response('Report not found', status=404)

            # Verify token matches patient
            if report.patient_id.access_token != access_token:
                return Response('Access denied', status=403)

            # Increment view count
            report.write({'view_count': report.view_count + 1})

            # Render report
            return request.render('hospital_lims.portal_report_view', {
                'report': report,
                'patient': report.patient_id,
            })
        except Exception as e:
            _logger.error(f"Error in portal_view_report: {str(e)}")
            return Response('Error loading report', status=500)

    # ===================== EXPORT ENDPOINTS =====================

    @http.route('/lims/export/report/<int:report_id>/json', type='http', auth='user', methods=['GET'])
    def export_report_json(self, report_id, **kwargs):
        """
        Export report as JSON
        """
        try:
            report = request.env['lims.report'].sudo().browse(report_id)
            if not report.exists():
                return Response('Report not found', status=404)

            if not report.json_content:
                # Generate JSON content if not available
                report._generate_report_content()

            return request.make_response(
                report.json_content,
                headers=[
                    ('Content-Type', 'application/json'),
                    ('Content-Disposition', f'attachment; filename="LIMS_Report_{report.name}.json"'),
                ]
            )
        except Exception as e:
            _logger.error(f"Error exporting report as JSON: {str(e)}")
            return Response('Error exporting report', status=500)

    @http.route('/lims/export/report/<int:report_id>/xml', type='http', auth='user', methods=['GET'])
    def export_report_xml(self, report_id, **kwargs):
        """
        Export report as XML
        """
        try:
            report = request.env['lims.report'].sudo().browse(report_id)
            if not report.exists():
                return Response('Report not found', status=404)

            # Generate XML
            xml_content = self._generate_report_xml(report)

            return request.make_response(
                xml_content,
                headers=[
                    ('Content-Type', 'application/xml'),
                    ('Content-Disposition', f'attachment; filename="LIMS_Report_{report.name}.xml"'),
                ]
            )
        except Exception as e:
            _logger.error(f"Error exporting report as XML: {str(e)}")
            return Response('Error exporting report', status=500)

    def _generate_report_xml(self, report):
        """Generate XML representation of a report"""
        xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<lims_report>
    <report>
        <id>{report.name}</id>
        <date>{report.report_date}</date>
        <type>{report.report_type}</type>
        <status>{report.state}</status>
    </report>
    <patient>
        <id>{report.patient_id.patient_id}</id>
        <name>{html_escape(report.patient_id.name)}</name>
        <date_of_birth>{report.patient_id.date_of_birth}</date_of_birth>
        <age>{report.patient_id.age}</age>
        <gender>{report.patient_id.gender}</gender>
        <blood_type>{report.patient_id.blood_type or ''}</blood_type>
    </patient>
    <order>
        <id>{report.test_order_id.order_id}</id>
        <date>{report.test_order_id.date_ordered}</date>
        <priority>{report.test_order_id.priority}</priority>
        <doctor>{html_escape(report.test_order_id.doctor_id.name) if report.test_order_id.doctor_id else ''}</doctor>
    </order>
    <results>
"""
        for line in report.test_order_id.order_line_ids:
            xml += f"""
        <test>
            <name>{html_escape(line.test_type_id.name)}</name>
            <code>{line.test_type_id.code}</code>
            <result>{line.result_value or line.result_text or ''}</result>
            <unit>{line.result_unit or ''}</unit>
            <normal_range>{html_escape(line.normal_range or '')}</normal_range>
            <is_abnormal>{line.is_abnormal}</is_abnormal>
            <is_critical>{line.is_critical}</is_critical>
            <interpretation>{html_escape(line.interpretation or '')}</interpretation>
        </test>
"""

        xml += """
    </results>
    <summary>
        <total_tests>""" + str(len(report.test_order_id.order_line_ids)) + """</total_tests>
        <abnormal_count>""" + str(report.abnormal_count) + """</abnormal_count>
        <has_abnormal>""" + str(report.has_abnormal) + """</has_abnormal>
    </summary>
</lims_report>"""
        return xml

    @http.route('/lims/export/orders/csv', type='http', auth='user', methods=['GET'])
    def export_orders_csv(self, **kwargs):
        """
        Export orders as CSV
        """
        try:
            import csv
            from io import StringIO

            # Get filters from params
            state = kwargs.get('state', '')
            date_from = kwargs.get('date_from', '')
            date_to = kwargs.get('date_to', '')

            domain = []
            if state:
                domain.append(('state', '=', state))
            if date_from:
                domain.append(('date_ordered', '>=', date_from))
            if date_to:
                domain.append(('date_ordered', '<=', date_to))

            orders = request.env['lims.test_order'].sudo().search(domain)

            output = StringIO()
            writer = csv.writer(output)

            # Write header
            writer.writerow([
                'Order ID', 'Patient', 'Patient ID', 'Doctor', 'Date',
                'Priority', 'Status', 'Total Tests', 'Total Amount',
                'Abnormal Count', 'Turnaround Hours'
            ])

            # Write data
            for order in orders:
                writer.writerow([
                    order.order_id,
                    order.patient_name,
                    order.patient_id.patient_id if order.patient_id else '',
                    order.doctor_id.name if order.doctor_id else '',
                    order.date_ordered,
                    order.priority,
                    order.state,
                    order.total_tests,
                    order.amount_total,
                    order.abnormal_line_count,
                    order.actual_turnaround_hours,
                ])

            csv_content = output.getvalue()
            output.close()

            return request.make_response(
                csv_content,
                headers=[
                    ('Content-Type', 'text/csv'),
                    ('Content-Disposition',
                     f'attachment; filename="LIMS_Orders_{datetime.now().strftime("%Y%m%d")}.csv"'),
                ]
            )
        except Exception as e:
            _logger.error(f"Error exporting orders CSV: {str(e)}")
            return Response('Error exporting data', status=500)
        