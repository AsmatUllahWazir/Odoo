# -*- coding: utf-8 -*-
"""
Quality Control Module for LIMS
Ensures test accuracy, instrument calibration, and reagent quality
"""
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta
import statistics
import logging

_logger = logging.getLogger(__name__)


class LimsQualityControl(models.Model):
    """
    Comprehensive Quality Control Model
    Manages all quality control processes including instrument calibration,
    reagent validation, and test accuracy verification
    """
    _name = 'lims.quality_control'
    _description = 'LIMS Quality Control'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'date desc'

    # ===================== BASIC IDENTIFICATION =====================
    name = fields.Char(
        string='QC Reference',
        required=True,
        copy=False,
        default=lambda self: _('New'),
        help='Quality control reference number'
    )

    test_type_id = fields.Many2one(
        'lims.test_type',
        string='Test Type',
        required=True,
        help='Test type being quality controlled'
    )

    instrument_id = fields.Many2one(
        'lims.instrument',
        string='Instrument',
        help='Instrument used for the QC'
    )

    # ===================== QC TIMING =====================
    date = fields.Datetime(
        string='QC Date',
        required=True,
        default=fields.Datetime.now,
        help='Date and time of quality control'
    )

    technician_id = fields.Many2one(
        'hr.employee',
        string='Technician',
        required=True,
        help='Technician performing quality control'
    )

    supervisor_id = fields.Many2one(
        'hr.employee',
        string='Supervisor',
        help='Supervisor who reviewed the QC'
    )

    # ===================== QC TYPE =====================
    qc_type = fields.Selection([
        ('instrument_calibration', 'Instrument Calibration'),
        ('reagent_validation', 'Reagent Validation'),
        ('internal_control', 'Internal Control'),
        ('external_proficiency', 'External Proficiency Test'),
        ('daily_control', 'Daily Control'),
        ('weekly_control', 'Weekly Control'),
        ('monthly_control', 'Monthly Control'),
        ('quality_audit', 'Quality Audit'),
        ('method_validation', 'Method Validation'),
        ('adhoc', 'Ad-hoc Control')
    ], string='QC Type', required=True, default='daily')

    # ===================== QC RESULTS =====================
    result_value = fields.Float(
        string='QC Result',
        help='Quality control result value'
    )

    target_value = fields.Float(
        string='Target Value',
        required=True,
        help='Expected or target value'
    )

    tolerance = fields.Float(
        string='Tolerance (+/-)',
        required=True,
        default=5.0,
        help='Acceptable tolerance range'
    )

    lower_limit = fields.Float(
        compute='_compute_limits',
        store=True,
        help='Lower acceptable limit'
    )

    upper_limit = fields.Float(
        compute='_compute_limits',
        store=True,
        help='Upper acceptable limit'
    )

    is_passed = fields.Boolean(
        compute='_compute_qc_result',
        store=True,
        help='Whether the quality control passed'
    )

    deviation = fields.Float(
        compute='_compute_deviation',
        store=True,
        help='Deviation from target value'
    )

    deviation_percentage = fields.Float(
        compute='_compute_deviation',
        store=True,
        help='Percentage deviation from target value'
    )

    # ===================== CONTROL MATERIALS =====================
    control_material = fields.Char(
        string='Control Material',
        help='Name or lot number of control material used'
    )

    lot_number = fields.Char(
        string='Lot Number',
        help='Lot number of control material'
    )

    expiry_date = fields.Date(
        string='Expiry Date',
        help='Expiry date of control material'
    )

    control_level = fields.Selection([
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('critical', 'Critical')
    ], string='Control Level')

    # ===================== STATISTICAL ANALYSIS =====================
    mean_value = fields.Float(
        compute='_compute_statistics',
        store=True,
        help='Mean of all QC results for this test type'
    )

    standard_deviation = fields.Float(
        compute='_compute_statistics',
        store=True,
        help='Standard deviation of QC results'
    )

    coefficient_variation = fields.Float(
        compute='_compute_statistics',
        store=True,
        help='Coefficient of variation (CV) percentage'
    )

    z_score = fields.Float(
        compute='_compute_statistics',
        store=True,
        help='Z-score for this QC result'
    )

    # ===================== STATUS =====================
    state = fields.Selection([
        ('draft', 'Draft'),
        ('review', 'Under Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('corrective', 'Corrective Action Required')
    ], string='Status', required=True, default='draft', tracking=True)

    # ===================== NOTES AND ACTIONS =====================
    notes = fields.Text(
        string='QC Notes',
        help='Additional notes about quality control'
    )

    corrective_action = fields.Text(
        string='Corrective Action',
        help='Corrective actions taken if QC failed'
    )

    preventive_action = fields.Text(
        string='Preventive Action',
        help='Preventive measures to avoid future issues'
    )

    review_notes = fields.Text(
        string='Review Notes',
        help='Notes from supervisor review'
    )

    # ===================== RELATIONSHIPS =====================
    test_line_id = fields.Many2one(
        'lims.test_order_line',
        string='Test Line',
        help='Associated test line (if any)'
    )

    test_order_id = fields.Many2one(
        'lims.test_order',
        string='Test Order',
        related='test_line_id.test_order_id',
        store=True,
        readonly=True
    )

    patient_id = fields.Many2one(
        'lims.patient',
        string='Patient',
        related='test_order_id.patient_id',
        store=True,
        readonly=True
    )

    sample_id = fields.Many2one(
        'lims.sample',
        string='Sample',
        related='test_line_id.sample_id',
        store=True,
        readonly=True
    )

    # ===================== COMPUTED FIELDS =====================
    test_type_name = fields.Char(
        related='test_type_id.name',
        store=True,
        readonly=True
    )

    instrument_name = fields.Char(
        store=True,
        readonly=True
    )

    # instrument_name = fields.Char(
    #     related='instrument_id.name',
    #     store=True,
    #     readonly=True
    # )

    is_valid = fields.Boolean(
        compute='_compute_valid',
        store=True,
        help='Whether the QC is still valid (not expired)'
    )

    # ===================== COMPUTE METHODS =====================

    @api.depends('target_value', 'tolerance')
    def _compute_limits(self):
        """Compute acceptable limits"""
        for record in self:
            record.lower_limit = record.target_value - record.tolerance
            record.upper_limit = record.target_value + record.tolerance

    @api.depends('result_value', 'lower_limit', 'upper_limit')
    def _compute_qc_result(self):
        """Determine if QC passed"""
        for record in self:
            if record.result_value:
                record.is_passed = record.lower_limit <= record.result_value <= record.upper_limit
            else:
                record.is_passed = False

    @api.depends('result_value', 'target_value')
    def _compute_deviation(self):
        """Compute deviation from target"""
        for record in self:
            if record.result_value and record.target_value:
                record.deviation = record.result_value - record.target_value
                if record.target_value != 0:
                    record.deviation_percentage = (record.deviation / record.target_value) * 100
                else:
                    record.deviation_percentage = 0.0
            else:
                record.deviation = 0.0
                record.deviation_percentage = 0.0

    @api.depends('test_type_id', 'result_value')
    def _compute_statistics(self):
        """Compute statistical analysis of QC results"""
        for record in record:
            # Get all QC results for this test type
            qcs = self.search([
                ('test_type_id', '=', record.test_type_id.id),
                ('state', 'in', ['approved', 'review']),
                ('id', '!=', record.id)
            ])

            values = qcs.mapped('result_value') + ([record.result_value] if record.result_value else [])
            values = [v for v in values if v is not None]

            if values:
                record.mean_value = statistics.mean(values)
                record.standard_deviation = statistics.stdev(values) if len(values) > 1 else 0
                if record.mean_value != 0:
                    record.coefficient_variation = (record.standard_deviation / record.mean_value) * 100
                else:
                    record.coefficient_variation = 0

                if record.result_value and record.mean_value and record.standard_deviation != 0:
                    record.z_score = (record.result_value - record.mean_value) / record.standard_deviation
                else:
                    record.z_score = 0
            else:
                record.mean_value = 0
                record.standard_deviation = 0
                record.coefficient_variation = 0
                record.z_score = 0

    @api.depends('expiry_date')
    def _compute_valid(self):
        """Check if QC is still valid"""
        for record in record:
            if record.expiry_date:
                record.is_valid = record.expiry_date >= fields.Date.today()
            else:
                record.is_valid = True

    # ===================== CONSTRAINTS =====================

    @api.constrains('target_value', 'tolerance')
    def _check_qc_values(self):
        """Validate QC values"""
        for record in record:
            if record.tolerance < 0:
                raise ValidationError(_('Tolerance cannot be negative!'))
            if record.target_value < 0:
                raise ValidationError(_('Target value cannot be negative!'))
            if record.result_value and record.result_value < 0:
                raise ValidationError(_('Result value cannot be negative!'))

    @api.constrains('expiry_date')
    def _check_expiry_date(self):
        """Validate expiry date"""
        for record in record:
            if record.expiry_date and record.expiry_date < fields.Date.today():
                raise ValidationError(_('Control material has expired!'))

    # ===================== CRUD OVERRIDES =====================

    @api.model
    def create(self, vals):
        """Override create to generate name sequence"""
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('lims.quality.control') or _('New')

        qc = super(LimsQualityControl, self).create(vals)

        # Log creation
        qc.message_post(
            body=_('QC record created for test type: %s') % qc.test_type_name,
            message_type='notification'
        )

        return qc

    # ===================== WORKFLOW ACTIONS =====================

    def action_review(self):
        """Submit QC for review"""
        if not self.result_value:
            raise ValidationError(_('Please enter QC result before submitting for review!'))

        self.state = 'review'
        self.message_post(body=_('QC submitted for review by %s') % self.technician_id.name)

    def action_approve(self):
        """Approve QC"""
        if self.state != 'review':
            raise UserError(_('QC must be in review state for approval!'))

        self.state = 'approved'
        self.supervisor_id = self.env.user.employee_id.id
        self.review_notes = self.review_notes or 'Approved'
        self.message_post(body=_('QC approved by %s') % self.supervisor_id.name)

    def action_reject(self):
        """Reject QC"""
        if self.state != 'review':
            raise UserError(_('QC must be in review state for rejection!'))

        if not self.corrective_action:
            raise ValidationError(_('Please specify corrective action for rejection!'))

        self.state = 'rejected'
        self.supervisor_id = self.env.user.employee_id.id
        self.message_post(body=_('QC rejected by %s. Corrective action required.') % self.supervisor_id.name)

    def action_require_corrective(self):
        """Flag QC for corrective action"""
        if self.state not in ['draft', 'review']:
            raise UserError(_('QC cannot be flagged for corrective action in current state!'))

        if not self.corrective_action:
            raise ValidationError(_('Please specify corrective action!'))

        self.state = 'corrective'
        self.message_post(body=_('Corrective action required: %s') % self.corrective_action)

    def action_reset_to_draft(self):
        """Reset QC to draft state"""
        self.state = 'draft'
        self.message_post(body=_('QC reset to draft'))

    def action_validate(self):
        """Validate QC without review"""
        if not self.result_value:
            raise ValidationError(_('Please enter QC result before validation!'))

        self.state = 'approved'
        self.supervisor_id = self.env.user.employee_id.id
        self.message_post(body=_('QC validated by %s') % self.supervisor_id.name)

    # ===================== REPORTING ACTIONS =====================

    def action_print_qc_report(self):
        """Print QC report"""
        self.ensure_one()
        return self.env.ref('hospital_lims.action_report_lims_qc').report_action(self)

    def action_generate_qc_chart(self):
        """Generate QC chart (Levey-Jennings)"""
        self.ensure_one()
        # This would generate a chart for QC results
        return {
            'type': 'ir.actions.act_window',
            'name': _('QC Chart'),
            'res_model': 'lims.qc.chart.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_test_type_id': self.test_type_id.id},
        }

    # ===================== UTILITY METHODS =====================

    def get_qc_status(self):
        """Get detailed QC status"""
        self.ensure_one()
        return {
            'passed': self.is_passed,
            'deviation': self.deviation_percentage,
            'within_tolerance': abs(self.deviation_percentage) <= self.tolerance,
            'z_score': self.z_score,
            'trend': 'in_control' if self.is_passed else 'out_of_control',
        }

    def get_statistical_summary(self):
        """Get statistical summary of QC results"""
        self.ensure_one()
        return {
            'mean': self.mean_value,
            'std_dev': self.standard_deviation,
            'cv': self.coefficient_variation,
            'z_score': self.z_score,
            'target': self.target_value,
            'result': self.result_value,
        }

    @api.model
    def get_test_type_qc_stats(self, test_type_id):
        """Get comprehensive QC statistics for a test type"""
        qcs = self.search([
            ('test_type_id', '=', test_type_id),
            ('state', '=', 'approved')
        ])

        if not qcs:
            return None

        values = qcs.mapped('result_value')
        values = [v for v in values if v is not None]

        if not values:
            return None

        return {
            'count': len(values),
            'mean': statistics.mean(values),
            'median': statistics.median(values),
            'std_dev': statistics.stdev(values) if len(values) > 1 else 0,
            'min': min(values),
            'max': max(values),
            'range': max(values) - min(values),
            'cv': (statistics.stdev(values) / statistics.mean(values) * 100) if len(values) > 1 and statistics.mean(
                values) != 0 else 0,
            'pass_rate': (len(qcs.filtered(lambda q: q.is_passed)) / len(qcs)) * 100,
            'last_approved': max(qcs.mapped('date')),
        }


class LimsQCChartWizard(models.TransientModel):
    """
    Wizard for generating QC charts
    """
    _name = 'lims.qc.chart.wizard'
    _description = 'QC Chart Wizard'

    test_type_id = fields.Many2one(
        'lims.test_type',
        string='Test Type',
        required=True
    )

    start_date = fields.Date(
        string='Start Date',
        required=True,
        default=lambda self: fields.Date.today() - timedelta(days=30)
    )

    end_date = fields.Date(
        string='End Date',
        required=True,
        default=fields.Date.today
    )

    chart_type = fields.Selection([
        ('levey_jennings', 'Levey-Jennings'),
        ('westgard', 'Westgard Rules'),
        ('control_chart', 'Control Chart'),
        ('histogram', 'Histogram')
    ], string='Chart Type', default='levey_jennings')

    def action_generate_chart(self):
        """Generate the QC chart"""
        self.ensure_one()
        # This would generate the chart using the selected parameters
        return {
            'type': 'ir.actions.act_window',
            'name': _('QC Chart - %s') % self.test_type_id.name,
            'res_model': 'lims.qc.chart.result',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_test_type_id': self.test_type_id.id,
                'default_start_date': self.start_date,
                'default_end_date': self.end_date,
                'default_chart_type': self.chart_type,
            },
        }
    