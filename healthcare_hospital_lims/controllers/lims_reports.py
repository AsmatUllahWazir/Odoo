# -*- coding: utf-8 -*-
"""
Report Controllers for LIMS
Specialized endpoints for report generation and viewing
"""
from odoo import http
from odoo.http import request, Response
from odoo.exceptions import UserError
import base64
import io
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)


class LimsReportControllers(http.Controller):
    """
    Specialized controllers for report generation
    """

    @http.route('/lims/report/generate/<int:order_id>', type='http', auth='user', methods=['GET'])
    def generate_report_from_order(self, order_id, **kwargs):
        """
        Generate a report from a test order
        """
        try:
            order = request.env['lims.test_order'].sudo().browse(order_id)
            if not order.exists():
                return Response('Order not found', status=404)

            # Create report
            report_vals = {
                'test_order_id': order.id,
                'patient_id': order.patient_id.id,
                'report_date': datetime.now(),
                'report_type': 'standard',
                'state': 'draft',
            }
            report = request.env['lims.report'].sudo().create(report_vals)
            report._generate_report_content()
            report.action_generate()

            # Return to report form
            return {
                'type': 'ir.actions.act_window',
                'name': 'Report Generated',
                'res_model': 'lims.report',
                'res_id': report.id,
                'view_mode': 'form',
                'target': 'current',
            }
        except Exception as e:
            _logger.error(f"Error generating report from order: {str(e)}")
            return Response('Error generating report', status=500)

    @http.route('/lims/report/batch', type='json', auth='user', methods=['POST'])
    def generate_batch_reports(self, **kwargs):
        """
        Generate reports for multiple orders
        """
        try:
            order_ids = kwargs.get('order_ids', [])
            report_type = kwargs.get('report_type', 'standard')

            if not order_ids:
                return {'status': 'error', 'message': 'No order IDs provided'}

            orders = request.env['lims.test_order'].sudo().browse(order_ids)

            generated = 0
            failed = 0
            reports = []
            errors = []

            for order in orders:
                try:
                    report_vals = {
                        'test_order_id': order.id,
                        'patient_id': order.patient_id.id,
                        'report_date': datetime.now(),
                        'report_type': report_type,
                        'state': 'draft',
                    }
                    report = request.env['lims.report'].sudo().create(report_vals)
                    report._generate_report_content()
                    report.action_generate()
                    reports.append(report.id)
                    generated += 1
                except Exception as e:
                    _logger.error(f"Error generating report for order {order.order_id}: {str(e)}")
                    failed += 1
                    errors.append({
                        'order_id': order.order_id,
                        'error': str(e)
                    })

            return {
                'status': 'success' if generated > 0 else 'partial',
                'generated': generated,
                'failed': failed,
                'report_ids': reports,
                'errors': errors,
            }
        except Exception as e:
            _logger.error(f"Error generating batch reports: {str(e)}")
            return {'status': 'error', 'message': str(e)}

    @http.route('/lims/report/send/<int:report_id>', type='json', auth='user', methods=['POST'])
    def send_report(self, report_id, **kwargs):
        """
        Send a report to patient via email
        """
        try:
            report = request.env['lims.report'].sudo().browse(report_id)
            if not report.exists():
                return {'status': 'error', 'message': 'Report not found'}

            if not report.patient_id.email:
                return {'status': 'error', 'message': 'Patient email not found'}

            # Generate PDF
            pdf_content, _ = request.env.ref('hospital_lims.action_report_lims_pdf').sudo()._render_qweb_pdf(
                [report.id])

            # Create attachment
            attachment_vals = {
                'name': f"LIMS_Report_{report.name}.pdf",
                'type': 'binary',
                'datas': base64.b64encode(pdf_content),
                'res_model': 'lims.report',
                'res_id': report.id,
                'mimetype': 'application/pdf',
            }
            attachment = request.env['ir.attachment'].sudo().create(attachment_vals)
            report.write({'attachment_id': attachment.id})

            # Send email
            template = request.env.ref('hospital_lims.email_template_report_send', raise_if_not_found=False)
            if template:
                template.send_mail(report.id, force_send=True)
                report.write({
                    'sent_date': datetime.now(),
                    'sent_by': request.env.user.id,
                    'sent_to': report.patient_id.email,
                    'delivery_method': 'email',
                    'state': 'sent',
                })

                return {
                    'status': 'success',
                    'message': f'Report sent to {report.patient_id.email}',
                }
            else:
                return {'status': 'error', 'message': 'Email template not found'}
        except Exception as e:
            _logger.error(f"Error sending report: {str(e)}")
            return {'status': 'error', 'message': str(e)}

    @http.route('/lims/report/regenerate/<int:report_id>', type='http', auth='user', methods=['GET'])
    def regenerate_report(self, report_id, **kwargs):
        """
        Regenerate a report
        """
        try:
            report = request.env['lims.report'].sudo().browse(report_id)
            if not report.exists():
                return Response('Report not found', status=404)

            report._generate_report_content()
            report.state = 'generated'

            return {
                'type': 'ir.actions.act_window',
                'name': 'Report Regenerated',
                'res_model': 'lims.report',
                'res_id': report.id,
                'view_mode': 'form',
                'target': 'current',
            }
        except Exception as e:
            _logger.error(f"Error regenerating report: {str(e)}")
            return Response('Error regenerating report', status=500)

    @http.route('/lims/report/bulk_send', type='json', auth='user', methods=['POST'])
    def bulk_send_reports(self, **kwargs):
        """
        Send multiple reports
        """
        try:
            report_ids = kwargs.get('report_ids', [])

            if not report_ids:
                return {'status': 'error', 'message': 'No report IDs provided'}

            reports = request.env['lims.report'].sudo().browse(report_ids)

            sent = 0
            failed = 0
            errors = []

            for report in reports:
                try:
                    if not report.patient_id.email:
                        failed += 1
                        errors.append({
                            'report_id': report.id,
                            'error': 'No email address'
                        })
                        continue

                    # Generate PDF
                    pdf_content, _ = request.env.ref('hospital_lims.action_report_lims_pdf').sudo()._render_qweb_pdf(
                        [report.id])

                    # Create attachment
                    attachment_vals = {
                        'name': f"LIMS_Report_{report.name}.pdf",
                        'type': 'binary',
                        'datas': base64.b64encode(pdf_content),
                        'res_model': 'lims.report',
                        'res_id': report.id,
                        'mimetype': 'application/pdf',
                    }
                    attachment = request.env['ir.attachment'].sudo().create(attachment_vals)
                    report.write({'attachment_id': attachment.id})

                    # Send email
                    template = request.env.ref('hospital_lims.email_template_report_send', raise_if_not_found=False)
                    if template:
                        template.send_mail(report.id, force_send=True)
                        report.write({
                            'sent_date': datetime.now(),
                            'sent_by': request.env.user.id,
                            'sent_to': report.patient_id.email,
                            'delivery_method': 'email',
                            'state': 'sent',
                        })
                        sent += 1
                    else:
                        failed += 1
                        errors.append({
                            'report_id': report.id,
                            'error': 'Email template not found'
                        })
                except Exception as e:
                    failed += 1
                    errors.append({
                        'report_id': report.id,
                        'error': str(e)
                    })

            return {
                'status': 'success' if sent > 0 else 'partial',
                'sent': sent,
                'failed': failed,
                'errors': errors,
            }
        except Exception as e:
            _logger.error(f"Error in bulk_send_reports: {str(e)}")
            return {'status': 'error', 'message': str(e)}

    @http.route('/lims/report/bulk_print', type='json', auth='user', methods=['POST'])
    def bulk_print_reports(self, **kwargs):
        """
        Bulk print reports (generates single PDF with all reports)
        """
        try:
            report_ids = kwargs.get('report_ids', [])

            if not report_ids:
                return {'status': 'error', 'message': 'No report IDs provided'}

            reports = request.env['lims.report'].sudo().browse(report_ids)

            # Generate combined PDF
            pdf_content = b''
            for report in reports:
                report.write({'print_count': report.print_count + 1})
                report_pdf, _ = request.env.ref('hospital_lims.action_report_lims_pdf').sudo()._render_qweb_pdf(
                    [report.id])
                pdf_content += report_pdf

            # Return combined PDF
            return request.make_response(
                pdf_content,
                headers=[
                    ('Content-Type', 'application/pdf'),
                    ('Content-Disposition',
                     f'attachment; filename="LIMS_Bulk_Reports_{datetime.now().strftime("%Y%m%d")}.pdf"'),
                ]
            )
        except Exception as e:
            _logger.error(f"Error in bulk_print_reports: {str(e)}")
            return {'status': 'error', 'message': str(e)}
        