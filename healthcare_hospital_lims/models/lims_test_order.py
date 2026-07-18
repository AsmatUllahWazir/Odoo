# -*- coding: utf-8 -*-
"""
Test Order Management Module for LIMS
Manages complete laboratory test order lifecycle from creation to invoicing
"""
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError, AccessError
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import logging

_logger = logging.getLogger(__name__)


class LimsTestOrder(models.Model):
    """
    Comprehensive Test Order Model
    Manages the complete workflow from order creation to final invoicing
    """
    _name = 'lims.test_order'
    _description = 'LIMS Test Order'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'order_id'
    _order = 'order_id desc'

    # ===================== BASIC IDENTIFICATION =====================
    order_id = fields.Char(
        string='Order ID',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
        help='Unique identifier for the test order. Auto-generated using sequence.'
    )

    patient_id = fields.Many2one(
        'lims.patient',
        string='Patient',
        required=True,
        tracking=True,
        help='Patient for whom the tests are ordered'
    )

    doctor_id = fields.Many2one(
        'hr.employee',
        string='Ordering Doctor',
        required=True,
        tracking=True,
        help='Doctor who ordered the tests'
    )

    # ===================== ORDER DETAILS =====================
    date_ordered = fields.Datetime(
        string='Order Date',
        required=True,
        default=fields.Datetime.now,
        tracking=True,
        help='Date and time when the order was created'
    )

    priority = fields.Selection([
        ('routine', 'Routine'),
        ('urgent', 'Urgent'),
        ('emergency', 'Emergency'),
        ('stat', 'STAT')
    ], string='Priority', default='routine', tracking=True)

    order_type = fields.Selection([
        ('outpatient', 'Outpatient'),
        ('inpatient', 'Inpatient'),
        ('emergency', 'Emergency'),
        ('routine', 'Routine Checkup'),
        ('followup', 'Follow-up'),
        ('preoperative', 'Pre-operative'),
        ('postoperative', 'Post-operative')
    ], string='Order Type', default='outpatient')

    department = fields.Selection([
        ('pathology', 'Pathology'),
        ('microbiology', 'Microbiology'),
        ('biochemistry', 'Biochemistry'),
        ('hematology', 'Hematology'),
        ('immunology', 'Immunology'),
        ('serology', 'Serology'),
        ('molecular', 'Molecular Diagnostics'),
        ('genetics', 'Genetics'),
        ('other', 'Other')
    ], string='Department', help='Laboratory department handling the order')

    # ===================== WORKFLOW STATE =====================
    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending_approval', 'Pending Approval'),
        ('approved', 'Approved'),
        ('confirmed', 'Confirmed'),
        ('sample_collection', 'Sample Collection'),
        ('in_progress', 'In Progress'),
        ('quality_check', 'Quality Check'),
        ('results_ready', 'Results Ready'),
        ('review_pending', 'Review Pending'),
        ('reported', 'Reported'),
        ('invoiced', 'Invoiced'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('on_hold', 'On Hold')
    ], string='Status', required=True, default='draft', tracking=True)

    # ===================== ORDER LINES =====================
    order_line_ids = fields.One2many(
        'lims.test_order_line',
        'test_order_id',
        string='Test Lines',
        copy=True,
        help='Individual test items in this order'
    )

    line_count = fields.Integer(
        string='Number of Tests',
        compute='_compute_line_stats',
        store=True
    )

    completed_line_count = fields.Integer(
        string='Completed Tests',
        compute='_compute_line_stats',
        store=True
    )

    abnormal_line_count = fields.Integer(
        string='Abnormal Tests',
        compute='_compute_line_stats',
        store=True
    )

    # ===================== FINANCIAL INFORMATION =====================
    amount_subtotal = fields.Monetary(
        compute='_compute_amounts',
        store=True,
        currency_field='currency_id',
        help='Subtotal before tax'
    )

    amount_tax = fields.Monetary(
        compute='_compute_amounts',
        store=True,
        currency_field='currency_id',
        help='Tax amount'
    )

    amount_total = fields.Monetary(
        compute='_compute_amounts',
        store=True,
        currency_field='currency_id',
        help='Total amount including tax'
    )

    tax_ids = fields.Many2many(
        'account.tax',
        string='Taxes',
        help='Taxes applied to the order'
    )

    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id.id
    )

    discount = fields.Float(
        string='Discount (%)',
        default=0.0,
        help='Discount percentage applied to the order'
    )

    discount_amount = fields.Monetary(
        compute='_compute_amounts',
        store=True,
        currency_field='currency_id',
        help='Discount amount'
    )

    # ===================== INVOICING =====================
    invoice_id = fields.Many2one(
        'account.move',
        string='Invoice',
        readonly=True,
        help='Generated invoice for this order'
    )

    invoice_status = fields.Selection([
        ('not_invoiced', 'Not Invoiced'),
        ('invoicing', 'Invoicing'),
        ('invoiced', 'Invoiced'),
        ('partial', 'Partial Invoice')
    ], string='Invoice Status', default='not_invoiced', tracking=True)

    invoice_date = fields.Date(
        string='Invoice Date',
        help='Date when invoice was created'
    )

    payment_status = fields.Selection([
        ('unpaid', 'Unpaid'),
        ('partial', 'Partially Paid'),
        ('paid', 'Paid')
    ], string='Payment Status', default='unpaid')

    # ===================== SAMPLE MANAGEMENT =====================
    sample_ids = fields.One2many(
        'lims.sample',
        'test_order_id',
        string='Samples',
        help='Samples collected for this order'
    )

    sample_count = fields.Integer(
        compute='_compute_sample_info',
        store=True,
        help='Total number of samples for this order'
    )

    sample_collection_status = fields.Selection([
        ('pending', 'Pending Collection'),
        ('partial', 'Partially Collected'),
        ('collected', 'All Collected'),
        ('received', 'Received in Lab'),
        ('processing', 'Processing')
    ], string='Sample Collection Status', compute='_compute_sample_info', store=True)

    # ===================== REPORTS =====================
    report_ids = fields.One2many(
        'lims.report',
        'test_order_id',
        string='Reports',
        help='Generated reports for this order'
    )

    latest_report_id = fields.Many2one(
        'lims.report',
        compute='_compute_report_info',
        store=True,
        help='Most recent report for this order'
    )

    report_count = fields.Integer(
        compute='_compute_report_info',
        store=True,
        help='Number of reports generated'
    )

    # ===================== QUALITY CONTROL =====================
    qc_ids = fields.One2many(
        'lims.quality_control',
        'test_order_id',
        string='Quality Controls',
        help='Quality control records for this order'
    )

    qc_passed = fields.Boolean(
        compute='_compute_qc_status',
        store=True,
        help='Whether all quality controls passed'
    )

    qc_notes = fields.Text(string='Quality Control Notes')

    # ===================== NOTES AND REFERENCES =====================
    notes = fields.Html(
        string='Notes',
        help='Additional notes or special instructions'
    )

    internal_notes = fields.Text(
        string='Internal Notes',
        help='Internal notes for laboratory staff'
    )

    clinical_indications = fields.Text(
        string='Clinical Indications',
        help='Clinical reasons for ordering these tests'
    )

    referral_reference = fields.Char(
        string='Referral Reference',
        help='Reference number from referring doctor/facility'
    )

    # ===================== TIMELINE TRACKING =====================
    confirmation_date = fields.Datetime(
        string='Confirmation Date',
        readonly=True,
        help='Date when order was confirmed'
    )

    sample_collection_date = fields.Datetime(
        string='Sample Collection Date',
        readonly=True,
        help='Date when samples were collected'
    )

    processing_start_date = fields.Datetime(
        string='Processing Start Date',
        readonly=True,
        help='Date when processing started'
    )

    results_ready_date = fields.Datetime(
        string='Results Ready Date',
        readonly=True,
        help='Date when results were ready'
    )

    reported_date = fields.Datetime(
        string='Reported Date',
        readonly=True,
        help='Date when report was generated'
    )

    completed_date = fields.Datetime(
        string='Completion Date',
        readonly=True,
        help='Date when order was completed'
    )

    # ===================== TURNAROUND TIME =====================
    actual_turnaround_hours = fields.Float(
        compute='_compute_turnaround',
        store=True,
        help='Actual turnaround time in hours'
    )

    expected_turnaround_hours = fields.Float(
        compute='_compute_turnaround',
        store=True,
        help='Expected turnaround time in hours based on test types'
    )

    is_overdue = fields.Boolean(
        compute='_compute_turnaround',
        store=True,
        help='Whether the order is overdue'
    )

    overdue_days = fields.Integer(
        compute='_compute_turnaround',
        store=True,
        help='Number of days overdue'
    )

    # ===================== COMPUTED FIELDS =====================
    patient_name = fields.Char(
        string='Patient Name',
        compute='_compute_patient_info',
        store=True
    )

    doctor_name = fields.Char(
        string='Doctor Name',
        compute='_compute_patient_info',
        store=True
    )

    patient_age = fields.Integer(
        string='Patient Age',
        compute='_compute_patient_info',
        store=True
    )

    patient_gender = fields.Char(
        string='Patient Gender',
        compute='_compute_patient_info',
        store=True
    )

    total_tests = fields.Integer(
        compute='_compute_line_stats',
        store=True
    )

    completion_percentage = fields.Float(
        compute='_compute_line_stats',
        store=True
    )

    has_abnormal_results = fields.Boolean(
        compute='_compute_line_stats',
        store=True,
        help='Whether any test in this order has abnormal results'
    )

    is_high_priority = fields.Boolean(
        compute='_compute_priority',
        store=True,
        help='Whether this is a high priority order'
    )

    completed_tests = fields.Float()

    # ===================== COMPUTE METHODS =====================

    @api.depends('order_line_ids', 'order_line_ids.state')
    def _compute_line_stats(self):
        """Compute comprehensive line statistics"""
        for record in self:
            lines = record.order_line_ids
            record.total_tests = len(lines)
            record.line_count = len(lines)

            completed = lines.filtered(lambda l: l.state in ['completed', 'verified', 'reported'])
            record.completed_line_count = len(completed)
            record.completed_tests = len(completed)

            abnormal = lines.filtered(lambda l: l.is_abnormal)
            record.abnormal_line_count = len(abnormal)

            record.completion_percentage = (
                        record.completed_tests / record.total_tests * 100) if record.total_tests > 0 else 0

            # Check for abnormal results
            record.has_abnormal_results = any(lines.mapped('is_abnormal'))

    @api.depends('order_line_ids', 'order_line_ids.subtotal', 'discount', 'tax_ids')
    def _compute_amounts(self):
        """Compute financial amounts with taxes and discounts"""
        for record in self:
            subtotal = sum(record.order_line_ids.mapped('subtotal'))
            record.amount_subtotal = subtotal

            # Calculate discount
            record.discount_amount = (subtotal * record.discount / 100) if record.discount > 0 else 0

            # Calculate tax (simplified - can be enhanced with proper tax computation)
            tax_amount = 0
            if record.tax_ids:
                # This is a simplified tax calculation
                taxable_amount = subtotal - record.discount_amount
                for tax in record.tax_ids:
                    if tax.amount_type == 'percent':
                        tax_amount += taxable_amount * (tax.amount / 100)
                    elif tax.amount_type == 'fixed':
                        tax_amount += tax.amount

            record.amount_tax = tax_amount
            record.amount_total = record.amount_subtotal - record.discount_amount + record.amount_tax

    @api.depends('patient_id')
    def _compute_patient_info(self):
        """Compute patient-related information"""
        for record in self:
            if record.patient_id:
                record.patient_name = record.patient_id.name
                record.patient_age = record.patient_id.age
                record.patient_gender = dict(record.patient_id._fields['gender'].selection).get(
                    record.patient_id.gender)
            else:
                record.patient_name = ''
                record.patient_age = 0
                record.patient_gender = ''

            if record.doctor_id:
                record.doctor_name = record.doctor_id.name
            else:
                record.doctor_name = ''

    @api.depends('sample_ids', 'sample_ids.status')
    def _compute_sample_info(self):
        """Compute sample-related information"""
        for record in self:
            samples = record.sample_ids
            record.sample_count = len(samples)

            if not samples:
                record.sample_collection_status = 'pending'
            else:
                statuses = samples.mapped('status')
                if all(s in ['collected', 'received', 'processing', 'analyzed', 'reported'] for s in statuses):
                    record.sample_collection_status = 'collected'
                elif any(s in ['processing', 'analyzed'] for s in statuses):
                    record.sample_collection_status = 'processing'
                elif any(s in ['received'] for s in statuses):
                    record.sample_collection_status = 'received'
                elif any(s in ['collected'] for s in statuses):
                    record.sample_collection_status = 'partial'
                else:
                    record.sample_collection_status = 'pending'

    @api.depends('report_ids')
    def _compute_report_info(self):
        """Compute report-related information"""
        for record in self:
            reports = record.report_ids
            record.report_count = len(reports)
            record.latest_report_id = reports.sorted('create_date', reverse=True)[:1].id if reports else False

    @api.depends('qc_ids', 'qc_ids.is_passed')
    def _compute_qc_status(self):
        """Compute quality control status"""
        for record in self:
            qcs = record.qc_ids
            if qcs:
                record.qc_passed = all(qcs.mapped('is_passed'))
            else:
                record.qc_passed = True  # No QC means passed by default

    @api.depends('priority')
    def _compute_priority(self):
        """Determine if order is high priority"""
        for record in self:
            record.is_high_priority = record.priority in ['urgent', 'emergency', 'stat']

    @api.depends('date_ordered', 'reported_date', 'expected_turnaround_hours')
    def _compute_turnaround(self):
        """Compute turnaround time and overdue status"""
        for record in self:
            if record.date_ordered and record.reported_date:
                delta = record.reported_date - record.date_ordered
                record.actual_turnaround_hours = delta.total_seconds() / 3600
            else:
                record.actual_turnaround_hours = 0

            # Calculate expected turnaround based on test types
            if record.order_line_ids:
                max_tat = max(record.order_line_ids.mapped('test_type_id.turnaround_time') or [24])
                record.expected_turnaround_hours = max_tat
            else:
                record.expected_turnaround_hours = 24

            # Check if overdue
            if record.state not in ['reported', 'invoiced', 'completed', 'cancelled']:
                if record.date_ordered:
                    expected_date = record.date_ordered + timedelta(hours=record.expected_turnaround_hours)
                    if datetime.now() > expected_date:
                        record.is_overdue = True
                        record.overdue_days = (datetime.now() - expected_date).days
                    else:
                        record.is_overdue = False
                        record.overdue_days = 0
                else:
                    record.is_overdue = False
                    record.overdue_days = 0
            else:
                record.is_overdue = False
                record.overdue_days = 0

    # ===================== CONSTRAINTS =====================

    @api.constrains('date_ordered')
    def _check_date_ordered(self):
        """Validate order date"""
        for record in self:
            if record.date_ordered and record.date_ordered > fields.Datetime.now() + timedelta(days=1):
                raise ValidationError(_('Order date cannot be in the future!'))

    @api.constrains('discount')
    def _check_discount(self):
        """Validate discount percentage"""
        for record in self:
            if record.discount < 0:
                raise ValidationError(_('Discount cannot be negative!'))
            if record.discount > 100:
                raise ValidationError(_('Discount cannot exceed 100%!'))

    @api.constrains('order_line_ids')
    def _check_order_lines(self):
        """Ensure order has at least one test line"""
        for record in self:
            if record.state != 'draft' and not record.order_line_ids:
                raise ValidationError(_('Order must have at least one test line!'))

    # ===================== CRUD OVERRIDES =====================

    @api.model
    def create(self, vals):
        """Override create to generate order_id sequence and create samples"""
        if vals.get('order_id', _('New')) == _('New'):
            vals['order_id'] = self.env['ir.sequence'].next_by_code('lims.test.order') or _('New')

        # Set default doctor if not provided
        if not vals.get('doctor_id'):
            vals['doctor_id'] = self.env.user.employee_id.id

        order = super(LimsTestOrder, self).create(vals)

        # Create samples automatically
        order._create_samples()

        # Log creation
        order.message_post(
            body=_('Test order created: %s for patient %s') % (order.order_id, order.patient_name),
            message_type='notification'
        )

        return order

    def write(self, vals):
        """Override write to track state changes and update timelines"""
        for record in self:
            # Track state changes
            if 'state' in vals:
                old_state = record.state
                new_state = vals['state']
                if old_state != new_state:
                    record._handle_state_change(old_state, new_state)

            result = super(LimsTestOrder, record).write(vals)

        return result

    def _handle_state_change(self, old_state, new_state):
        """Handle state change actions"""
        self.ensure_one()

        state_actions = {
            'confirmed': self._action_on_confirm,
            'sample_collection': self._action_on_sample_collection,
            'in_progress': self._action_on_start_processing,
            'results_ready': self._action_on_results_ready,
            'reported': self._action_on_report,
            'invoiced': self._action_on_invoice,
            'completed': self._action_on_complete,
            'cancelled': self._action_on_cancel,
            'on_hold': self._action_on_hold,
        }

        if new_state in state_actions:
            state_actions[new_state]()

    def _action_on_confirm(self):
        """Actions when order is confirmed"""
        self.confirmation_date = fields.Datetime.now()
        self.message_post(body=_('Order confirmed by %s') % self.env.user.name)

    def _action_on_sample_collection(self):
        """Actions when sample collection starts"""
        self.sample_collection_date = fields.Datetime.now()
        self.message_post(body=_('Sample collection started'))

    def _action_on_start_processing(self):
        """Actions when processing starts"""
        self.processing_start_date = fields.Datetime.now()
        self.message_post(body=_('Processing started'))

    def _action_on_results_ready(self):
        """Actions when results are ready"""
        self.results_ready_date = fields.Datetime.now()
        self.message_post(body=_('Results are ready for review'))

    def _action_on_report(self):
        """Actions when report is generated"""
        self.reported_date = fields.Datetime.now()
        self.message_post(body=_('Report generated'))

    def _action_on_invoice(self):
        """Actions when invoice is created"""
        self.invoice_date = fields.Date.today()
        self.message_post(body=_('Invoice generated'))

    def _action_on_complete(self):
        """Actions when order is completed"""
        self.completed_date = fields.Datetime.now()
        self.message_post(body=_('Order completed'))

    def _action_on_cancel(self):
        """Actions when order is cancelled"""
        self.message_post(body=_('Order cancelled by %s') % self.env.user.name)

    def _action_on_hold(self):
        """Actions when order is put on hold"""
        self.message_post(body=_('Order put on hold by %s') % self.env.user.name)

    # ===================== SAMPLE CREATION =====================

    def _create_samples(self):
        """Create samples for test order"""
        for line in self.order_line_ids:
            if line.test_type_id and not line.sample_id:
                sample_vals = {
                    'patient_id': self.patient_id.id,
                    'test_order_id': self.id,
                    'sample_type': line.test_type_id.required_sample_type or 'other',
                    'status': 'registered',
                    'collection_date': fields.Datetime.now(),
                    'collector_id': self.env.user.employee_id.id,
                }
                sample = self.env['lims.sample'].create(sample_vals)
                line.sample_id = sample.id

    def _create_samples_for_lines(self, line_ids=None):
        """Create samples for specific order lines"""
        lines = self.order_line_ids
        if line_ids:
            lines = lines.filtered(lambda l: l.id in line_ids)

        for line in lines:
            if line.test_type_id and not line.sample_id:
                sample_vals = {
                    'patient_id': self.patient_id.id,
                    'test_order_id': self.id,
                    'sample_type': line.test_type_id.required_sample_type or 'other',
                    'status': 'registered',
                    'collection_date': fields.Datetime.now(),
                    'collector_id': self.env.user.employee_id.id,
                }
                sample = self.env['lims.sample'].create(sample_vals)
                line.sample_id = sample.id

    # ===================== WORKFLOW ACTIONS =====================

    def action_draft(self):
        """Move order to draft state"""
        self.state = 'draft'
        self.message_post(body=_('Order returned to draft'))

    def action_submit_for_approval(self):
        """Submit order for approval"""
        if not self.order_line_ids:
            raise UserError(_('Cannot submit order without test lines!'))
        self.state = 'pending_approval'
        self.message_post(body=_('Order submitted for approval'))

    def action_approve(self):
        """Approve the order"""
        self.state = 'approved'
        self.message_post(body=_('Order approved'))

    def action_confirm(self):
        """Confirm the test order"""
        if not self.doctor_id:
            raise UserError(_('Please assign a doctor before confirming!'))
        self.state = 'confirmed'
        self._action_on_confirm()

        # Create samples for all lines if not already created
        for line in self.order_line_ids:
            if line.test_type_id and not line.sample_id:
                self._create_samples()

    def action_start_sample_collection(self):
        """Start sample collection"""
        self.state = 'sample_collection'
        self._action_on_sample_collection()
        self.message_post(body=_('Sample collection process started'))

    def action_complete_collection(self):
        """Complete sample collection"""
        if not self.sample_ids:
            raise UserError(_('No samples collected for this order!'))

        # Check if all samples are collected
        pending_samples = self.sample_ids.filtered(lambda s: s.status == 'registered')
        if pending_samples:
            raise UserError(_('Some samples are still pending collection!'))

        self.state = 'in_progress'
        self._action_on_start_processing()
        self.message_post(body=_('Sample collection completed, processing started'))

    def action_start_processing(self):
        """Start processing the order"""
        if not self.order_line_ids:
            raise UserError(_('Cannot process order without test lines!'))

        # Check if samples are collected
        if not all(self.sample_ids.mapped('status') in ['collected', 'received', 'processing', 'analyzed']):
            raise UserError(_('Samples must be collected before processing!'))

        self.state = 'in_progress'
        self._action_on_start_processing()
        self.message_post(body=_('Processing started'))

    def action_submit_qc(self):
        """Submit order for quality control"""
        self.state = 'quality_check'
        self.message_post(body=_('Submitted for quality control'))

    def action_approve_qc(self):
        """Approve quality control"""
        if not self.qc_passed:
            raise UserError(_('Quality control checks have not passed!'))
        self.state = 'results_ready'
        self._action_on_results_ready()
        self.message_post(body=_('Quality control approved'))

    def action_results_ready(self):
        """Mark results as ready"""
        # Check if all tests are completed
        incomplete = self.order_line_ids.filtered(lambda l: l.state not in ['completed', 'verified', 'reported'])
        if incomplete:
            raise UserError(_('All tests must be completed before marking results ready!'))

        self.state = 'results_ready'
        self._action_on_results_ready()

        # Send notification
        self._send_result_notification()
        self.message_post(body=_('All results are ready for review'))

    def action_submit_review(self):
        """Submit for final review"""
        self.state = 'review_pending'
        self.message_post(body=_('Submitted for final review'))

    def action_approve_review(self):
        """Approve final review"""
        self.state = 'reported'
        self._action_on_report()

        # Generate report
        self._generate_report()
        self.message_post(body=_('Review approved, report generated'))

    def action_generate_report(self):
        """Generate report manually"""
        self._generate_report()
        self.state = 'reported'
        self._action_on_report()
        self.message_post(body=_('Report generated'))

    def _generate_report(self):
        """Generate a report for the order"""
        report_vals = {
            'test_order_id': self.id,
            'patient_id': self.patient_id.id,
            'report_date': fields.Datetime.now(),
            'report_type': 'standard',
            'state': 'generated',
        }
        report = self.env['lims.report'].create(report_vals)
        report._generate_report_content()
        self.message_post(body=_('Report %s generated') % report.name)

    def _send_result_notification(self):
        """Send notification that results are ready"""
        template = self.env.ref('hospital_lims.email_template_result_ready', raise_if_not_found=False)
        if template and self.patient_id.email:
            template.send_mail(self.id, force_send=True)

    def action_invoice(self):
        """Generate invoice for the order"""
        if self.invoice_id:
            raise UserError(_('This order already has an invoice!'))

        if self.amount_total <= 0:
            raise UserError(_('Cannot invoice with zero amount!'))

        try:
            # Create invoice
            invoice_vals = self._prepare_invoice_vals()
            invoice = self.env['account.move'].create(invoice_vals)

            # Create invoice lines
            for line in self.order_line_ids:
                if line.price > 0:
                    invoice_line_vals = self._prepare_invoice_line_vals(line)
                    self.env['account.move.line'].create(invoice_line_vals)

            self.invoice_id = invoice.id
            self.invoice_status = 'invoiced'
            self.invoice_date = fields.Date.today()
            self.state = 'invoiced'
            self._action_on_invoice()

            self.message_post(
                body=_('Invoice generated: <a href="#" data-oe-model="account.move" data-oe-id="%d">%s</a>') % (
                    invoice.id, invoice.name)
            )

            return {
                'type': 'ir.actions.act_window',
                'name': _('Invoice'),
                'res_model': 'account.move',
                'view_mode': 'form',
                'res_id': invoice.id,
            }

        except Exception as e:
            _logger.error(f'Error creating invoice: {str(e)}')
            raise UserError(_('Failed to create invoice. Please check your accounting configuration.'))

    def _prepare_invoice_vals(self):
        """Prepare invoice values"""
        return {
            'move_type': 'out_invoice',
            'partner_id': self.patient_id.id,
            'invoice_date': fields.Date.today(),
            'ref': self.order_id,
            'narration': f'Laboratory tests for {self.patient_name} - Order {self.order_id}',
            'invoice_line_ids': [],
            'invoice_payment_term_id': self.env.ref('account.account_payment_term_net30').id,
        }

    def _prepare_invoice_line_vals(self, line):
        """Prepare invoice line values"""
        return {
            'move_id': self.invoice_id.id,
            'product_id': line.test_type_id.product_id.id or False,
            'name': f"{line.test_type_id.name} - {self.order_id}",
            'quantity': 1,
            'price_unit': line.price or 0,
            'tax_ids': [(6, 0, [])],
            'discount': self.discount,
        }

    def action_cancel(self):
        """Cancel the order"""
        if self.state == 'invoiced':
            raise UserError(_('Cannot cancel an invoiced order!'))
        if self.state == 'completed':
            raise UserError(_('Cannot cancel a completed order!'))

        self.state = 'cancelled'
        self._action_on_cancel()

        # Cancel any samples
        self.sample_ids.status = 'rejected'
        self.message_post(body=_('Order cancelled'))

    def action_hold(self):
        """Put order on hold"""
        if self.state in ['draft', 'cancelled', 'completed']:
            raise UserError(_('Cannot put order on hold in current state!'))
        self.state = 'on_hold'
        self._action_on_hold()

    def action_resume(self):
        """Resume order from hold"""
        if self.state != 'on_hold':
            raise UserError(_('Order is not on hold!'))
        self.state = 'in_progress'
        self.message_post(body=_('Order resumed from hold'))

    def action_complete(self):
        """Mark order as completed"""
        if self.state != 'reported':
            raise UserError(_('Order must be reported before completion!'))
        self.state = 'completed'
        self._action_on_complete()

    # ===================== VIEW ACTIONS =====================

    def action_view_invoice(self):
        """View the invoice for this order"""
        self.ensure_one()
        if not self.invoice_id:
            raise UserError(_('No invoice found for this order!'))

        return {
            'type': 'ir.actions.act_window',
            'name': _('Invoice'),
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': self.invoice_id.id,
        }

    def action_view_samples(self):
        """View samples for this order"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Samples - %s') % self.order_id,
            'res_model': 'lims.sample',
            'view_mode': 'tree,form',
            'domain': [('test_order_id', '=', self.id)],
            'context': {'default_test_order_id': self.id},
        }

    def action_view_reports(self):
        """View reports for this order"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Reports - %s') % self.order_id,
            'res_model': 'lims.report',
            'view_mode': 'tree,form',
            'domain': [('test_order_id', '=', self.id)],
            'context': {'default_test_order_id': self.id},
        }

    def action_view_qc(self):
        """View quality control records for this order"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Quality Control - %s') % self.order_id,
            'res_model': 'lims.quality_control',
            'view_mode': 'tree,form',
            'domain': [('test_order_id', '=', self.id)],
            'context': {'default_test_order_id': self.id},
        }

    def action_send_reminder(self):
        """Send reminder to doctor/patient"""
        self.ensure_one()
        template = self.env.ref('hospital_lims.email_template_order_reminder', raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=True)
            self.message_post(body=_('Reminder email sent'))
        else:
            raise UserError(_('Email template not found!'))

    # ===================== UTILITY METHODS =====================

    def get_order_summary(self):
        """Get a summary of the order"""
        self.ensure_one()
        return {
            'order_id': self.order_id,
            'patient': self.patient_name,
            'doctor': self.doctor_name,
            'state': self.state,
            'total_tests': self.total_tests,
            'completed_tests': self.completed_tests,
            'abnormal_tests': self.abnormal_line_count,
            'total_amount': self.amount_total,
            'days_since_order': (datetime.now() - self.date_ordered).days if self.date_ordered else 0,
        }

    def get_test_statuses(self):
        """Get status distribution of tests"""
        self.ensure_one()
        statuses = self.order_line_ids.mapped('state')
        return {
            'draft': statuses.count('draft'),
            'assigned': statuses.count('assigned'),
            'in_progress': statuses.count('in_progress'),
            'completed': statuses.count('completed'),
            'verified': statuses.count('verified'),
            'reported': statuses.count('reported'),
        }

    def get_invoice_status_details(self):
        """Get detailed invoice status"""
        self.ensure_one()
        if not self.invoice_id:
            return {
                'has_invoice': False,
                'invoice_number': '',
                'invoice_date': '',
                'payment_status': 'unpaid',
                'total': 0,
                'paid': 0,
                'balance': 0,
            }

        invoice = self.invoice_id
        return {
            'has_invoice': True,
            'invoice_number': invoice.name,
            'invoice_date': invoice.invoice_date,
            'payment_status': self.payment_status,
            'total': invoice.amount_total,
            'paid': invoice.amount_residual,
            'balance': invoice.amount_residual,
        }

    # ===================== STATISTICAL METHODS =====================

    @api.model
    def get_dashboard_stats(self, period='month'):
        """Get dashboard statistics for orders"""
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

        orders = self.search([
            ('date_ordered', '>=', start_date),
            ('state', '!=', 'cancelled')
        ])

        return {
            'total_orders': len(orders),
            'total_revenue': sum(orders.mapped('amount_total')),
            'avg_turnaround': sum(orders.mapped('actual_turnaround_hours')) / max(len(orders), 1),
            'abnormal_rate': sum(1 for o in orders if o.has_abnormal_results) / max(len(orders), 1) * 100,
            'completion_rate': sum(1 for o in orders if o.state == 'completed') / max(len(orders), 1) * 100,
        }

    @api.model
    def get_pending_summary(self):
        """Get summary of pending orders"""
        pending = self.search([
            ('state', 'in', ['draft', 'pending_approval', 'approved', 'confirmed', 'sample_collection', 'in_progress'])
        ])

        return {
            'draft': len(pending.filtered(lambda o: o.state == 'draft')),
            'pending_approval': len(pending.filtered(lambda o: o.state == 'pending_approval')),
            'approved': len(pending.filtered(lambda o: o.state == 'approved')),
            'confirmed': len(pending.filtered(lambda o: o.state == 'confirmed')),
            'sample_collection': len(pending.filtered(lambda o: o.state == 'sample_collection')),
            'in_progress': len(pending.filtered(lambda o: o.state == 'in_progress')),
            'overdue': len(pending.filtered(lambda o: o.is_overdue)),
            'high_priority': len(pending.filtered(lambda o: o.is_high_priority)),
        }


class LimsTestOrderLine(models.Model):
    """
    Individual test line within a test order
    Contains test-specific details, results, and status
    """
    _name = 'lims.test_order_line'
    _description = 'LIMS Test Order Line'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'test_type_id'
    _order = 'test_order_id, id'

    # ===================== BASIC FIELDS =====================
    test_order_id = fields.Many2one(
        'lims.test_order',
        string='Test Order',
        required=True,
        ondelete='cascade'
    )

    test_type_id = fields.Many2one(
        'lims.test_type',
        string='Test Type',
        required=True,
        domain="[('active', '=', True)]"
    )

    sample_id = fields.Many2one(
        'lims.sample',
        string='Sample',
        help='Sample used for this test'
    )

    # ===================== PRICING =====================
    price = fields.Monetary(
        related='test_type_id.price',
        store=True,
        readonly=True,
        currency_field='currency_id'
    )

    subtotal = fields.Monetary(
        compute='_compute_subtotal',
        store=True,
        currency_field='currency_id'
    )

    currency_id = fields.Many2one(
        'res.currency',
        related='test_order_id.currency_id',
        store=True,
        readonly=True
    )

    # ===================== RESULT FIELDS =====================
    result_value = fields.Float(
        string='Result Value',
        help='Numerical result value'
    )

    result_text = fields.Char(
        string='Result Text',
        help='Textual result (for qualitative tests)'
    )

    result_unit = fields.Char(
        string='Result Unit',
        help='Unit of measurement for the result'
    )

    result_date = fields.Datetime(
        string='Result Date',
        help='Date when results were entered'
    )

    technician_id = fields.Many2one(
        'hr.employee',
        string='Technician',
        help='Technician who performed the test'
    )

    # ===================== STATUS =====================
    state = fields.Selection([
        ('draft', 'Draft'),
        ('assigned', 'Assigned'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('verified', 'Verified'),
        ('reported', 'Reported'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', tracking=True)

    # ===================== VALIDATION =====================
    is_abnormal = fields.Boolean(
        compute='_compute_abnormal',
        store=True,
        help='Whether the result is outside normal range'
    )

    is_critical = fields.Boolean(
        compute='_compute_critical',
        store=True,
        help='Whether the result is critically abnormal'
    )

    interpretation = fields.Text(
        string='Interpretation',
        help='Clinical interpretation of the results'
    )

    notes = fields.Text(
        string='Notes',
        help='Additional notes about the test'
    )

    # ===================== QUALITY CONTROL =====================
    qc_passed = fields.Boolean(
        string='QC Passed',
        default=False,
        help='Whether the test passed quality control'
    )

    qc_notes = fields.Text(
        string='QC Notes',
        help='Quality control notes'
    )

    # ===================== COMPUTED FIELDS =====================
    test_name = fields.Char(
        related='test_type_id.name',
        store=True,
        readonly=True
    )

    normal_range = fields.Text(
        related='test_type_id.normal_range',
        store=True,
        readonly=True
    )

    patient_id = fields.Many2one(
        'lims.patient',
        related='test_order_id.patient_id',
        store=True,
        readonly=True
    )

    patient_name = fields.Char(
        related='test_order_id.patient_name',
        store=True,
        readonly=True
    )

    # ===================== COMPUTE METHODS =====================

    @api.depends('price')
    def _compute_subtotal(self):
        """Compute subtotal for the line"""
        for record in self:
            record.subtotal = record.price or 0.0

    @api.depends('result_value', 'test_type_id.abnormal_low', 'test_type_id.abnormal_high')
    def _compute_abnormal(self):
        """Determine if result is abnormal based on reference ranges"""
        for record in self:
            record.is_abnormal = False
            if record.result_value and record.test_type_id:
                if record.test_type_id.abnormal_low and record.result_value < record.test_type_id.abnormal_low:
                    record.is_abnormal = True
                if record.test_type_id.abnormal_high and record.result_value > record.test_type_id.abnormal_high:
                    record.is_abnormal = True

    @api.depends('result_value', 'test_type_id.abnormal_low', 'test_type_id.abnormal_high')
    def _compute_critical(self):
        """Determine if result is critically abnormal"""
        for record in self:
            record.is_critical = False
            if record.result_value and record.test_type_id:
                # Critical ranges are wider than abnormal ranges
                if record.test_type_id.abnormal_low:
                    critical_low = record.test_type_id.abnormal_low * 0.7
                    if record.result_value < critical_low:
                        record.is_critical = True
                if record.test_type_id.abnormal_high:
                    critical_high = record.test_type_id.abnormal_high * 1.3
                    if record.result_value > critical_high:
                        record.is_critical = True

    # ===================== CONSTRAINTS =====================

    @api.constrains('result_value')
    def _check_result_value(self):
        """Validate result value is reasonable"""
        for record in self:
            if record.result_value and record.result_value < 0:
                raise ValidationError(_('Result value cannot be negative!'))

    @api.constrains('state')
    def _check_state_transition(self):
        """Validate state transitions"""
        for record in self:
            if record.state == 'completed' and record.result_value is False and not record.result_text:
                raise ValidationError(_('Please enter test results before completing!'))

    # ===================== WORKFLOW ACTIONS =====================

    def action_assign(self):
        """Assign the test to a technician"""
        if not self.technician_id:
            self.technician_id = self.env.user.employee_id.id
        self.state = 'assigned'
        self.message_post(body=_('Test assigned to %s') % self.technician_id.name)

    def action_start_test(self):
        """Start processing the test"""
        self.state = 'in_progress'
        self.message_post(body=_('Test processing started'))

    def action_complete_test(self):
        """Complete the test with results"""
        if self.result_value is False and not self.result_text:
            raise ValidationError(_('Please enter test results before completing!'))
        self.state = 'completed'
        self.result_date = fields.Datetime.now()
        self.message_post(body=_('Test completed with results'))

    def action_verify(self):
        """Verify the test results"""
        if self.state != 'completed':
            raise ValidationError(_('Test must be completed before verification!'))
        self.state = 'verified'
        self.message_post(body=_('Test results verified'))

    def action_report(self):
        """Mark test as reported"""
        self.state = 'reported'
        self.message_post(body=_('Test results reported'))

    def action_cancel(self):
        """Cancel the test"""
        self.state = 'cancelled'
        self.message_post(body=_('Test cancelled'))

    def action_set_abnormal_flag(self):
        """Manually set abnormal flag"""
        self.is_abnormal = True
        self.message_post(body=_('Results marked as abnormal manually'))

    def action_clear_abnormal_flag(self):
        """Clear abnormal flag"""
        self.is_abnormal = False
        self.message_post(body=_('Abnormal flag cleared'))

    # ===================== UTILITY METHODS =====================

    def get_result_display(self):
        """Get formatted result display"""
        self.ensure_one()
        if self.result_text:
            return self.result_text
        elif self.result_value is not False:
            unit = f" {self.result_unit}" if self.result_unit else ""
            return f"{self.result_value}{unit}"
        return 'N/A'

    def get_result_status(self):
        """Get result status with color coding"""
        self.ensure_one()
        if self.is_critical:
            return {'status': 'Critical', 'color': 'red', 'icon': 'fa-exclamation-triangle'}
        elif self.is_abnormal:
            return {'status': 'Abnormal', 'color': 'orange', 'icon': 'fa-exclamation-circle'}
        elif self.state == 'completed':
            return {'status': 'Normal', 'color': 'green', 'icon': 'fa-check-circle'}
        elif self.state == 'in_progress':
            return {'status': 'In Progress', 'color': 'blue', 'icon': 'fa-spinner'}
        elif self.state == 'draft':
            return {'status': 'Pending', 'color': 'gray', 'icon': 'fa-clock-o'}
        return {'status': 'Unknown', 'color': 'gray', 'icon': 'fa-question-circle'}
