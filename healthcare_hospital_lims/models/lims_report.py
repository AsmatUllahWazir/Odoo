# -*- coding: utf-8 -*-
"""
Report Management Module for LIMS
Generates and manages professional laboratory reports
"""
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime
import base64
import io
import logging
from datetime import timedelta

_logger = logging.getLogger(__name__)


class LimsReport(models.Model):
    """
    Comprehensive Report Model
    Manages generation, storage, and distribution of laboratory reports
    """
    _name = 'lims.report'
    _description = 'LIMS Report'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'create_date desc'

    # ===================== BASIC IDENTIFICATION =====================
    name = fields.Char(
        string='Report Number',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
        help='Unique report identifier'
    )

    test_order_id = fields.Many2one(
        'lims.test_order',
        string='Test Order',
        required=True,
        help='Test order this report is based on'
    )

    patient_id = fields.Many2one(
        'lims.patient',
        string='Patient',
        related='test_order_id.patient_id',
        store=True,
        readonly=True
    )

    # ===================== REPORT DETAILS =====================
    report_date = fields.Datetime(
        string='Report Date',
        required=True,
        default=fields.Datetime.now,
        help='Date and time of report generation'
    )

    report_type = fields.Selection([
        ('standard', 'Standard Report'),
        ('detailed', 'Detailed Report with Interpretation'),
        ('summary', 'Summary Report'),
        ('emergency', 'Emergency Report'),
        ('comprehensive', 'Comprehensive Report'),
        ('graphical', 'Graphical Report')
    ], string='Report Type', required=True, default='standard')

    report_language = fields.Selection([
        ('en', 'English'),
        ('es', 'Spanish'),
        ('fr', 'French'),
        ('de', 'German'),
        ('ar', 'Arabic'),
        ('zh', 'Chinese'),
        ('other', 'Other')
    ], string='Report Language', default='en')

    # ===================== REPORT CONTENT =====================
    report_content = fields.Html(
        string='Report Content',
        help='HTML content of the report'
    )

    xml_content = fields.Text(
        string='XML Content',
        help='XML representation of report data'
    )

    json_content = fields.Text(
        string='JSON Content',
        help='JSON representation of report data'
    )

    # ===================== STATUS AND DISTRIBUTION =====================
    state = fields.Selection([
        ('draft', 'Draft'),
        ('generated', 'Generated'),
        ('reviewed', 'Reviewed'),
        ('approved', 'Approved'),
        ('sent', 'Sent'),
        ('received', 'Received by Patient'),
        ('archived', 'Archived')
    ], string='Status', required=True, default='draft', tracking=True)

    # ===================== ATTACHMENTS =====================
    attachment_id = fields.Many2one(
        'ir.attachment',
        string='PDF Attachment',
        help='Generated PDF file'
    )

    print_count = fields.Integer(
        string='Print Count',
        default=0,
        help='Number of times the report has been printed'
    )

    view_count = fields.Integer(
        string='View Count',
        default=0,
        help='Number of times the report has been viewed'
    )

    # ===================== DISTRIBUTION =====================
    sent_date = fields.Datetime(
        string='Sent Date',
        help='Date and time when report was sent'
    )

    sent_by = fields.Many2one(
        'res.users',
        string='Sent By',
        help='User who sent the report'
    )

    sent_to = fields.Char(
        string='Sent To',
        help='Email or address where report was sent'
    )

    delivery_method = fields.Selection([
        ('email', 'Email'),
        ('print', 'Printed Copy'),
        ('portal', 'Patient Portal'),
        ('fax', 'Fax'),
        ('sms', 'SMS'),
        ('other', 'Other')
    ], string='Delivery Method')

    # ===================== REVIEW AND APPROVAL =====================
    reviewed_by = fields.Many2one(
        'hr.employee',
        string='Reviewed By',
        help='Person who reviewed the report'
    )

    review_date = fields.Datetime(
        string='Review Date',
        help='Date and time of review'
    )

    review_notes = fields.Text(
        string='Review Notes',
        help='Notes from the reviewer'
    )

    approved_by = fields.Many2one(
        'hr.employee',
        string='Approved By',
        help='Person who approved the report'
    )

    approval_date = fields.Datetime(
        string='Approval Date',
        help='Date and time of approval'
    )

    # ===================== SIGNATURES =====================
    doctor_signature = fields.Binary(
        string='Doctor Signature',
        help='Digital signature of the doctor'
    )

    technician_signature = fields.Binary(
        string='Technician Signature',
        help='Digital signature of the technician'
    )

    digital_stamp = fields.Binary(
        string='Digital Stamp',
        help='Laboratory digital stamp'
    )

    # ===================== NOTES =====================
    notes = fields.Text(
        string='Notes',
        help='Additional notes about the report'
    )

    disclaimer = fields.Text(
        string='Disclaimer',
        default="This report is generated automatically. Please consult your doctor for clinical interpretation.",
        help='Legal disclaimer for the report'
    )

    # ===================== COMPUTED FIELDS =====================
    patient_name = fields.Char(
        string='Patient Name',
        related='patient_id.name',
        store=True,
        readonly=True
    )

    patient_gender = fields.Char(
        string='Patient Gender',
        store=True,
        readonly=True
    )

    # patient_gender = fields.Char(
    #     string='Patient Gender',
    #     related='patient_id.gender',
    #     store=True,
    #     readonly=True
    # )

    patient_age = fields.Integer(
        string='Patient Age',
        related='patient_id.age',
        store=True,
        readonly=True
    )

    order_date = fields.Datetime(
        string='Order Date',
        related='test_order_id.date_ordered',
        store=True,
        readonly=True
    )

    doctor_name = fields.Char(
        string='Doctor Name',
        related='test_order_id.doctor_id.name',
        store=True,
        readonly=True
    )

    total_tests = fields.Integer(
        compute='_compute_report_stats',
        store=True,
        help='Total tests in the report'
    )

    abnormal_count = fields.Integer(
        compute='_compute_report_stats',
        store=True,
        help='Number of abnormal results'
    )

    has_abnormal = fields.Boolean(
        compute='_compute_report_stats',
        store=True,
        help='Whether the report has abnormal results'
    )

    # ===================== COMPUTE METHODS =====================

    @api.depends('test_order_id', 'test_order_id.order_line_ids')
    def _compute_report_stats(self):
        """Compute report statistics"""
        for record in self:
            lines = record.test_order_id.order_line_ids
            record.total_tests = len(lines)
            record.abnormal_count = len(lines.filtered(lambda l: l.is_abnormal))
            record.has_abnormal = record.abnormal_count > 0

    # ===================== CONSTRAINTS =====================

    @api.constrains('report_type')
    def _check_report_type(self):
        """Validate report type based on order"""
        for record in self:
            if record.test_order_id and record.test_order_id.priority == 'emergency':
                if record.report_type != 'emergency':
                    raise ValidationError(_('Emergency orders require emergency report type!'))

    # ===================== CRUD OVERRIDES =====================

    @api.model
    def create(self, vals):
        """Override create to generate name sequence"""
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('lims.report') or _('New')

        report = super(LimsReport, self).create(vals)

        # Auto-generate content
        report._generate_report_content()

        report.message_post(
            body=_('Report created: %s') % report.name,
            message_type='notification'
        )

        return report

    # ===================== REPORT GENERATION =====================

    def _generate_report_content(self):
        """Generate HTML report content with all necessary data"""
        for report in self:
            order = report.test_order_id
            patient = order.patient_id

            # Build comprehensive HTML content
            html = self._build_report_html(order, patient)
            report.report_content = html

            # Generate JSON data for potential export
            report.json_content = self._build_report_json(order, patient)

            # Update state
            if report.state == 'draft':
                report.state = 'generated'

    def _build_report_html(self, order, patient):
        """Build the HTML report content"""
        # Start building HTML
        html = self._get_report_header()

        # Add patient information
        html += self._get_patient_section(patient)

        # Add order information
        html += self._get_order_section(order)

        # Add test results
        html += self._get_results_section(order)

        # Add interpretation if needed
        if self.report_type in ['detailed', 'comprehensive']:
            html += self._get_interpretation_section(order)

        # Add summary
        html += self._get_summary_section(order)

        # Add signatures
        html += self._get_signatures_section()

        # Add disclaimer
        html += self._get_disclaimer_section()

        # Close HTML
        html += self._get_report_footer()

        return html

    def _get_report_header(self):
        """Get report header HTML"""
        return """
        <div style="font-family: Arial, sans-serif; padding: 20px; max-width: 900px; margin: 0 auto;">
            <div style="text-align: center; border-bottom: 3px solid #2c3e50; padding-bottom: 20px; margin-bottom: 30px;">
                <h1 style="color: #2c3e50; font-size: 28px; margin: 0;">LABORATORY INFORMATION MANAGEMENT SYSTEM</h1>
                <h2 style="color: #34495e; font-size: 20px; margin: 5px 0;">PATHOLOGY REPORT</h2>
                <p style="color: #7f8c8d; font-size: 12px; margin: 5px 0;">This report contains laboratory test results for clinical use only</p>
            </div>
        """

    def _get_patient_section(self, patient):
        """Get patient information section HTML"""
        gender_map = dict(patient._fields['gender'].selection)
        return f"""
        <div style="margin-bottom: 25px;">
            <h3 style="color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 5px;">PATIENT INFORMATION</h3>
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 8px; width: 50%;"><strong>Patient Name:</strong> {patient.name}</td>
                    <td style="padding: 8px; width: 50%;"><strong>Patient ID:</strong> {patient.patient_id}</td>
                </tr>
                <tr>
                    <td style="padding: 8px;"><strong>Date of Birth:</strong> {patient.date_of_birth}</td>
                    <td style="padding: 8px;"><strong>Age:</strong> {patient.age} years</td>
                </tr>
                <tr>
                    <td style="padding: 8px;"><strong>Gender:</strong> {gender_map.get(patient.gender, patient.gender)}</td>
                    <td style="padding: 8px;"><strong>Blood Type:</strong> {patient.blood_type or 'N/A'}</td>
                </tr>
                <tr>
                    <td style="padding: 8px;" colspan="2"><strong>Allergies:</strong> {patient.allergies or 'None reported'}</td>
                </tr>
            </table>
        </div>
        """

    def _get_order_section(self, order):
        """Get order information section HTML"""
        state_map = dict(order._fields['state'].selection)
        priority_map = dict(order._fields['priority'].selection)
        return f"""
        <div style="margin-bottom: 25px;">
            <h3 style="color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 5px;">ORDER INFORMATION</h3>
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 8px; width: 50%;"><strong>Order ID:</strong> {order.order_id}</td>
                    <td style="padding: 8px; width: 50%;"><strong>Order Date:</strong> {order.date_ordered}</td>
                </tr>
                <tr>
                    <td style="padding: 8px;"><strong>Priority:</strong> {priority_map.get(order.priority, order.priority)}</td>
                    <td style="padding: 8px;"><strong>Status:</strong> {state_map.get(order.state, order.state)}</td>
                </tr>
                <tr>
                    <td style="padding: 8px;" colspan="2"><strong>Ordering Doctor:</strong> {order.doctor_id.name}</td>
                </tr>
                <tr>
                    <td style="padding: 8px;" colspan="2"><strong>Clinical Indications:</strong> {order.clinical_indications or 'Not specified'}</td>
                </tr>
            </table>
        </div>
        """

    def _get_results_section(self, order):
        """Get test results section HTML"""
        html = """
        <div style="margin-bottom: 25px;">
            <h3 style="color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 5px;">TEST RESULTS</h3>
            <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
                <tr style="background-color: #f2f2f2;">
                    <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Test Name</th>
                    <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Result</th>
                    <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Unit</th>
                    <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Normal Range</th>
                    <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Status</th>
                </tr>
        """

        for line in order.order_line_ids:
            result_display = line.get_result_display()
            status_info = line.get_result_status()

            # Set color based on status
            color = {
                'Normal': '#27ae60',
                'Abnormal': '#f39c12',
                'Critical': '#e74c3c',
                'In Progress': '#3498db',
                'Pending': '#95a5a6'
            }.get(status_info['status'], '#95a5a6')

            html += f"""
                <tr>
                    <td style="border: 1px solid #ddd; padding: 8px;">{line.test_type_id.name}</td>
                    <td style="border: 1px solid #ddd; padding: 8px; font-weight: bold;">{result_display}</td>
                    <td style="border: 1px solid #ddd; padding: 8px;">{line.result_unit or '-'}</td>
                    <td style="border: 1px solid #ddd; padding: 8px;">{line.normal_range or 'N/A'}</td>
                    <td style="border: 1px solid #ddd; padding: 8px; color: {color};">
                        <span style="font-weight: bold;">{status_info['status']}</span>
                        {f' <i class="fa fa-{status_info["icon"]}"></i>' if status_info.get('icon') else ''}
                    </td>
                </tr>
            """

        html += "</table></div>"
        return html

    def _get_interpretation_section(self, order):
        """Get interpretation section HTML for detailed reports"""
        html = """
        <div style="margin-bottom: 25px;">
            <h3 style="color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 5px;">INTERPRETATION</h3>
        """

        for line in order.order_line_ids:
            if line.interpretation or line.is_abnormal:
                html += f"""
                <div style="margin: 10px 0; padding: 10px; background-color: {'#fff5f5' if line.is_abnormal else '#f0f9f4'}; border-left: 4px solid {'#e74c3c' if line.is_abnormal else '#27ae60'};">
                    <p style="margin: 0;"><strong>{line.test_type_id.name}:</strong></p>
                    <p style="margin: 5px 0 0 20px;">{line.interpretation or ('**Abnormal result** - Please consult with physician.' if line.is_abnormal else 'Normal result')}</p>
                </div>
                """

        html += "</div>"
        return html

    def _get_summary_section(self, order):
        """Get summary section HTML"""
        return f"""
        <div style="margin-bottom: 25px;">
            <h3 style="color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 5px;">REPORT SUMMARY</h3>
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 5px;"><strong>Total Tests:</strong> {len(order.order_line_ids)}</td>
                    <td style="padding: 5px;"><strong>Abnormal Results:</strong> {len(order.order_line_ids.filtered(lambda l: l.is_abnormal))}</td>
                </tr>
                <tr>
                    <td style="padding: 5px;"><strong>Turnaround Time:</strong> {order.actual_turnaround_hours:.1f} hours</td>
                    <td style="padding: 5px;"><strong>Expected TAT:</strong> {order.expected_turnaround_hours:.1f} hours</td>
                </tr>
                <tr>
                    <td style="padding: 5px;"><strong>Total Amount:</strong> {order.amount_total:.2f}</td>
                    <td style="padding: 5px;"><strong>Report Generated:</strong> {self.report_date}</td>
                </tr>
            </table>
        </div>
        """

    def _get_signatures_section(self):
        """Get signatures section HTML"""
        return """
        <div style="margin: 30px 0 20px 0; padding: 20px; border-top: 2px solid #2c3e50;">
            <table style="width: 100%;">
                <tr>
                    <td style="width: 33%; text-align: center;">
                        <div style="border-bottom: 1px solid #333; padding-bottom: 5px; min-height: 50px;">
                            <img src="/web/binary/lims_sig/technician" style="max-height: 50px;" />
                        </div>
                        <p style="font-size: 12px; margin-top: 5px;">Laboratory Technician</p>
                    </td>
                    <td style="width: 33%; text-align: center;">
                        <div style="border-bottom: 1px solid #333; padding-bottom: 5px; min-height: 50px;">
                            <img src="/web/binary/lims_sig/doctor" style="max-height: 50px;" />
                        </div>
                        <p style="font-size: 12px; margin-top: 5px;">Pathologist / Doctor</p>
                    </td>
                    <td style="width: 33%; text-align: center;">
                        <div style="border-bottom: 1px solid #333; padding-bottom: 5px; min-height: 50px;">
                            <img src="/web/binary/lims_sig/stamp" style="max-height: 50px;" />
                        </div>
                        <p style="font-size: 12px; margin-top: 5px;">Laboratory Stamp</p>
                    </td>
                </tr>
            </table>
        </div>
        """

    def _get_disclaimer_section(self):
        """Get disclaimer section HTML"""
        return f"""
        <div style="margin-top: 30px; padding: 15px; background-color: #f8f9fa; border-left: 4px solid #95a5a6; font-size: 12px; color: #7f8c8d;">
            <p style="margin: 0;"><strong>DISCLAIMER:</strong></p>
            <p style="margin: 5px 0 0 20px;">{self.disclaimer}</p>
            <p style="margin: 5px 0 0 20px; font-size: 10px;">Report ID: {self.name} | Generated: {self.report_date} | Version: 1.0</p>
        </div>
        </div>
        """

    def _get_report_footer(self):
        """Get report footer HTML"""
        return """
        <div style="text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; font-size: 11px; color: #95a5a6;">
            <p>© 2024 Laboratory Information Management System. All rights reserved.</p>
            <p>This report is electronically generated and does not require a physical signature.</p>
        </div>
        """

    def _build_report_json(self, order, patient):
        """Build JSON representation of report data"""
        import json
        data = {
            'report_id': self.name,
            'report_date': self.report_date.isoformat() if self.report_date else None,
            'patient': {
                'id': patient.id,
                'patient_id': patient.patient_id,
                'name': patient.name,
                'date_of_birth': patient.date_of_birth.isoformat() if patient.date_of_birth else None,
                'age': patient.age,
                'gender': patient.gender,
                'blood_type': patient.blood_type,
                'allergies': patient.allergies,
            },
            'order': {
                'order_id': order.order_id,
                'date_ordered': order.date_ordered.isoformat() if order.date_ordered else None,
                'priority': order.priority,
                'state': order.state,
                'doctor': order.doctor_id.name if order.doctor_id else None,
                'total_amount': order.amount_total,
            },
            'results': []
        }

        for line in order.order_line_ids:
            data['results'].append({
                'test_name': line.test_type_id.name,
                'test_code': line.test_type_id.code,
                'result': line.result_value,
                'result_text': line.result_text,
                'unit': line.result_unit,
                'normal_range': line.normal_range,
                'is_abnormal': line.is_abnormal,
                'is_critical': line.is_critical,
                'interpretation': line.interpretation,
                'status': line.state,
            })

        return json.dumps(data, indent=2)

    # ===================== WORKFLOW ACTIONS =====================

    def action_generate(self):
        """Generate the report"""
        self.ensure_one()
        self._generate_report_content()
        self.state = 'generated'
        self.message_post(body=_('Report generated'))

    def action_review(self):
        """Review the report"""
        self.ensure_one()
        self.reviewed_by = self.env.user.employee_id.id
        self.review_date = fields.Datetime.now()
        self.state = 'reviewed'
        self.message_post(body=_('Report reviewed by %s') % self.reviewed_by.name)

    def action_approve(self):
        """Approve the report"""
        self.ensure_one()
        if self.state != 'reviewed':
            raise UserError(_('Report must be reviewed before approval!'))
        self.approved_by = self.env.user.employee_id.id
        self.approval_date = fields.Datetime.now()
        self.state = 'approved'
        self.message_post(body=_('Report approved by %s') % self.approved_by.name)

    def action_send(self):
        """Send the report"""
        self.ensure_one()
        self.sent_date = fields.Datetime.now()
        self.sent_by = self.env.user.id
        self.state = 'sent'
        self.message_post(body=_('Report sent to %s') % (self.sent_to or 'patient'))

    def action_send_email(self):
        """Send report via email"""
        self.ensure_one()
        if not self.patient_id.email:
            raise UserError(_('Patient email address not found!'))

        template = self.env.ref('hospital_lims.email_template_report_send', raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=True)
            self.sent_to = self.patient_id.email
            self.delivery_method = 'email'
            self.action_send()
            self.message_post(body=_('Report sent via email to %s') % self.patient_id.email)
        else:
            raise UserError(_('Email template not found!'))

    def action_archive(self):
        """Archive the report"""
        self.ensure_one()
        self.state = 'archived'
        self.message_post(body=_('Report archived'))

    def action_print_pdf(self):
        """Print report as PDF"""
        self.ensure_one()
        self.print_count += 1
        return self.env.ref('hospital_lims.action_report_lims_pdf').report_action(self)

    def action_download_pdf(self):
        """Download report as PDF"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': f'/lims/report/download/{self.id}',
            'target': 'new',
        }

    def action_view_order(self):
        """View associated test order"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Test Order'),
            'res_model': 'lims.test_order',
            'view_mode': 'form',
            'res_id': self.test_order_id.id,
        }

    def action_view_patient(self):
        """View associated patient"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Patient'),
            'res_model': 'lims.patient',
            'view_mode': 'form',
            'res_id': self.patient_id.id,
        }

    # ===================== UTILITY METHODS =====================

    def get_report_summary(self):
        """Get a summary of the report"""
        self.ensure_one()
        return {
            'report_id': self.name,
            'patient': self.patient_name,
            'order': self.test_order_id.order_id,
            'report_date': self.report_date,
            'state': self.state,
            'total_tests': self.total_tests,
            'abnormal_count': self.abnormal_count,
            'has_abnormal': self.has_abnormal,
            'print_count': self.print_count,
            'view_count': self.view_count,
        }

    def get_statistics(self):
        """Get report statistics"""
        self.ensure_one()
        return {
            'total_tests': self.total_tests,
            'abnormal_count': self.abnormal_count,
            'normal_count': self.total_tests - self.abnormal_count,
            'abnormal_percentage': (self.abnormal_count / self.total_tests * 100) if self.total_tests > 0 else 0,
            'has_critical': any(self.test_order_id.order_line_ids.mapped('is_critical')),
        }

    # ===================== STATISTICAL METHODS =====================

    @api.model
    def get_report_stats(self, period='month'):
        """Get comprehensive report statistics"""
        today = datetime.now().date()

        if period == 'today':
            start_date = today
        elif period == 'week':
            start_date = today - timedelta(days=7)
        elif period == 'month':
            start_date = today - timedelta(days=30)
        elif period == 'year':
            start_date = today - timedelta(days=365)
        else:
            start_date = today - timedelta(days=30)

        reports = self.search([
            ('report_date', '>=', start_date),
            ('state', '!=', 'draft')
        ])

        return {
            'total_reports': len(reports),
            'generated': len(reports.filtered(lambda r: r.state == 'generated')),
            'reviewed': len(reports.filtered(lambda r: r.state == 'reviewed')),
            'approved': len(reports.filtered(lambda r: r.state == 'approved')),
            'sent': len(reports.filtered(lambda r: r.state == 'sent')),
            'archived': len(reports.filtered(lambda r: r.state == 'archived')),
            'with_abnormal': len(reports.filtered(lambda r: r.has_abnormal)),
            'avg_abnormal_rate': sum(r.abnormal_count for r in reports) / max(len(reports), 1),
            'total_prints': sum(reports.mapped('print_count')),
            'avg_turnaround': sum(r.test_order_id.actual_turnaround_hours for r in reports if r.test_order_id) / max(
                len(reports), 1),
        }
