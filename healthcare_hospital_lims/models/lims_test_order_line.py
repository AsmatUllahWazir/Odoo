# -*- coding: utf-8 -*-
"""
Test Order Line Module for LIMS
Manages individual test lines within a test order with results and validation
"""
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)


class LimsTestOrderLine(models.Model):
    """
    Comprehensive Test Order Line Model
    Manages individual test items with results, validation, and workflow
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
        ondelete='cascade',
        tracking=True
    )

    test_type_id = fields.Many2one(
        'lims.test_type',
        string='Test Type',
        required=True,
        domain="[('active', '=', True)]",
        tracking=True
    )

    sample_id = fields.Many2one(
        'lims.sample',
        string='Sample',
        help='Sample used for this test',
        tracking=True
    )

    # ===================== PRICING =====================
    price = fields.Monetary(
        related='test_type_id.price',
        store=True,
        readonly=True,
        currency_field='currency_id',
        help='Price of the test'
    )

    subtotal = fields.Monetary(
        compute='_compute_subtotal',
        store=True,
        currency_field='currency_id',
        help='Subtotal for this test line'
    )

    currency_id = fields.Many2one(
        'res.currency',
        related='test_order_id.currency_id',
        store=True,
        readonly=True
    )

    discount = fields.Float(
        string='Line Discount (%)',
        default=0.0,
        help='Discount applied to this specific test'
    )

    discount_amount = fields.Monetary(
        compute='_compute_subtotal',
        store=True,
        currency_field='currency_id',
        help='Discount amount for this line'
    )

    # ===================== RESULT FIELDS =====================
    result_value = fields.Float(
        string='Result Value',
        help='Numerical result value',
        tracking=True
    )

    result_text = fields.Char(
        string='Result Text',
        help='Textual result (for qualitative tests)',
        tracking=True
    )

    result_unit = fields.Char(
        string='Result Unit',
        related='test_type_id.unit',
        store=True,
        readonly=True
    )

    result_date = fields.Datetime(
        string='Result Date',
        help='Date when results were entered'
    )

    technician_id = fields.Many2one(
        'hr.employee',
        string='Technician',
        tracking=True,
        help='Technician who performed the test'
    )

    supervisor_id = fields.Many2one(
        'hr.employee',
        string='Supervisor',
        help='Supervisor who verified the results'
    )

    # ===================== STATUS =====================
    state = fields.Selection([
        ('draft', 'Draft'),
        ('assigned', 'Assigned'),
        ('in_progress', 'In Progress'),
        ('pending_review', 'Pending Review'),
        ('completed', 'Completed'),
        ('verified', 'Verified'),
        ('reported', 'Reported'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', tracking=True)

    # ===================== VALIDATION =====================
    is_abnormal = fields.Boolean(
        compute='_compute_validation',
        store=True,
        help='Whether the result is outside normal range'
    )

    is_critical = fields.Boolean(
        compute='_compute_validation',
        store=True,
        help='Whether the result is critically abnormal'
    )

    validation_status = fields.Selection([
        ('normal', 'Normal'),
        ('abnormal_low', 'Abnormal Low'),
        ('abnormal_high', 'Abnormal High'),
        ('critical_low', 'Critical Low'),
        ('critical_high', 'Critical High'),
        ('borderline', 'Borderline'),
        ('no_result', 'No Result')
    ], compute='_compute_validation', store=True)

    validation_message = fields.Text(
        compute='_compute_validation',
        store=True,
        help='Validation message'
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

    run_number = fields.Char(
        string='Run Number',
        help='Batch or run number for this test'
    )

    # ===================== TIMELINE TRACKING =====================
    assigned_date = fields.Datetime(
        string='Assigned Date',
        help='Date when test was assigned'
    )

    started_date = fields.Datetime(
        string='Started Date',
        help='Date when test processing started'
    )

    completed_date = fields.Datetime(
        string='Completed Date',
        help='Date when test was completed'
    )

    verified_date = fields.Datetime(
        string='Verified Date',
        help='Date when test was verified'
    )

    # ===================== COMPUTED FIELDS =====================
    test_name = fields.Char(
        related='test_type_id.name',
        store=True,
        readonly=True
    )

    test_code = fields.Char(
        related='test_type_id.code',
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

    patient_age = fields.Integer(
        related='test_order_id.patient_age',
        store=True,
        readonly=True
    )

    result_display = fields.Char(
        compute='_compute_result_display',
        store=True,
        help='Formatted result for display'
    )

    is_ready_for_review = fields.Boolean(
        compute='_compute_ready_for_review',
        store=True,
        help='Whether the test is ready for review'
    )

    # ===================== COMPUTE METHODS =====================

    @api.depends('price', 'discount')
    def _compute_subtotal(self):
        """Compute subtotal with discount"""
        for record in self:
            if record.discount > 0:
                record.discount_amount = record.price * (record.discount / 100)
                record.subtotal = record.price - record.discount_amount
            else:
                record.discount_amount = 0
                record.subtotal = record.price or 0.0

    @api.depends('result_value', 'test_type_id.abnormal_low', 'test_type_id.abnormal_high',
                 'test_type_id.critical_low', 'test_type_id.critical_high')
    def _compute_validation(self):
        """Validate results against reference ranges"""
        for record in self:
            record.is_abnormal = False
            record.is_critical = False
            record.validation_status = 'no_result'
            record.validation_message = ''

            if record.result_value is None:
                record.validation_status = 'no_result'
                record.validation_message = 'No result entered'
                continue

            # Check ranges
            if record.test_type_id.abnormal_low and record.result_value < record.test_type_id.abnormal_low:
                record.is_abnormal = True
                if record.test_type_id.critical_low and record.result_value < record.test_type_id.critical_low:
                    record.is_critical = True
                    record.validation_status = 'critical_low'
                    record.validation_message = f'CRITICAL: Value {record.result_value} is critically low'
                else:
                    record.validation_status = 'abnormal_low'
                    record.validation_message = f'Abnormal: Value {record.result_value} is below normal range'

            elif record.test_type_id.abnormal_high and record.result_value > record.test_type_id.abnormal_high:
                record.is_abnormal = True
                if record.test_type_id.critical_high and record.result_value > record.test_type_id.critical_high:
                    record.is_critical = True
                    record.validation_status = 'critical_high'
                    record.validation_message = f'CRITICAL: Value {record.result_value} is critically high'
                else:
                    record.validation_status = 'abnormal_high'
                    record.validation_message = f'Abnormal: Value {record.result_value} is above normal range'
            else:
                record.validation_status = 'normal'
                record.validation_message = 'Result is within normal range'

    @api.depends('result_value', 'result_text', 'result_unit')
    def _compute_result_display(self):
        """Format result for display"""
        for record in self:
            if record.result_text:
                record.result_display = record.result_text
            elif record.result_value is not None:
                unit = f" {record.result_unit}" if record.result_unit else ""
                record.result_display = f"{record.result_value}{unit}"
            else:
                record.result_display = 'N/A'

    @api.depends('state', 'is_abnormal', 'result_value')
    def _compute_ready_for_review(self):
        """Determine if test is ready for review"""
        for record in self:
            record.is_ready_for_review = (
                    record.state == 'completed' and
                    (record.result_value is not None or record.result_text)
            )

    # ===================== CONSTRAINTS =====================

    @api.constrains('result_value')
    def _check_result_value(self):
        """Validate result value is reasonable"""
        for record in self:
            if record.result_value is not None and record.result_value < 0:
                raise ValidationError(_('Result value cannot be negative!'))

    @api.constrains('discount')
    def _check_discount(self):
        """Validate discount percentage"""
        for record in self:
            if record.discount < 0:
                raise ValidationError(_('Discount cannot be negative!'))
            if record.discount > 100:
                raise ValidationError(_('Discount cannot exceed 100%!'))

    @api.constrains('sample_id', 'test_type_id')
    def _check_sample_compatibility(self):
        """Check if sample is compatible with test type"""
        for record in self:
            if record.sample_id and record.test_type_id:
                if record.sample_id.sample_type != record.test_type_id.required_sample_type:
                    raise ValidationError(_(
                        'Sample type %s is not compatible with test %s which requires %s!'
                    ) % (
                                              dict(record.sample_id._fields['sample_type'].selection).get(
                                                  record.sample_id.sample_type),
                                              record.test_type_id.name,
                                              dict(record.test_type_id._fields['required_sample_type'].selection).get(
                                                  record.test_type_id.required_sample_type)
                                          ))

    # ===================== CRUD OVERRIDES =====================

    @api.model
    def create(self, vals):
        """Override create to set default technician"""
        if not vals.get('technician_id'):
            vals['technician_id'] = self.env.user.employee_id.id

        line = super(LimsTestOrderLine, self).create(vals)

        # Update test order total
        line.test_order_id._compute_amounts()

        line.message_post(
            body=_('Test line created: %s for order %s') % (line.test_type_id.name, line.test_order_id.order_id),
            message_type='notification'
        )

        return line

    def write(self, vals):
        """Override write to handle state changes and updates"""
        for record in self:
            if 'state' in vals:
                old_state = record.state
                new_state = vals['state']
                if old_state != new_state:
                    record._handle_state_change(old_state, new_state)

            if 'result_value' in vals or 'result_text' in vals:
                vals['result_date'] = datetime.now()

        result = super(LimsTestOrderLine, self).write(vals)

        # Update test order total and statistics
        for record in self:
            record.test_order_id._compute_amounts()
            record.test_order_id._compute_test_info()

        return result

    def _handle_state_change(self, old_state, new_state):
        """Handle state change actions"""
        self.ensure_one()

        if new_state == 'assigned':
            self.assigned_date = datetime.now()
            self.message_post(body=_('Test assigned to %s') % self.technician_id.name)

        elif new_state == 'in_progress':
            self.started_date = datetime.now()
            self.message_post(body=_('Test processing started'))

        elif new_state == 'completed':
            self.completed_date = datetime.now()
            if self.result_value is None and not self.result_text:
                raise ValidationError(_('Please enter test results before completing!'))
            self.message_post(body=_('Test completed with results'))
            self._check_critical_result()

        elif new_state == 'verified':
            self.verified_date = datetime.now()
            self.supervisor_id = self.env.user.employee_id.id
            self.message_post(body=_('Test verified by %s') % self.supervisor_id.name)

        elif new_state == 'reported':
            self.message_post(body=_('Test results reported'))

        elif new_state == 'cancelled':
            self.message_post(body=_('Test cancelled'))

    def _check_critical_result(self):
        """Send notification for critical results"""
        self.ensure_one()
        if self.is_critical:
            # Create activity for supervisor
            self.activity_schedule(
                'mail.mail_activity_data_todo',
                summary=f'Critical Result: {self.test_type_id.name}',
                note=f'Patient: {self.patient_name}, Value: {self.result_display}',
                user_id=self.env.user.id,
            )
            self.message_post(
                body=_('⚠️ CRITICAL RESULT: %s = %s') % (self.test_type_id.name, self.result_display),
                message_type='notification'
            )

    # ===================== WORKFLOW ACTIONS =====================

    def action_assign(self):
        """Assign the test to a technician"""
        if not self.technician_id:
            self.technician_id = self.env.user.employee_id.id
        self.state = 'assigned'
        self._handle_state_change('draft', 'assigned')

    def action_start_test(self):
        """Start processing the test"""
        if self.state not in ['assigned', 'draft']:
            raise ValidationError(_('Test must be assigned before starting!'))
        self.state = 'in_progress'
        self._handle_state_change(self.state, 'in_progress')

    def action_enter_result(self):
        """Enter test results"""
        if self.state != 'in_progress':
            raise ValidationError(_('Test must be in progress to enter results!'))
        self.state = 'pending_review'
        self.result_date = datetime.now()
        self.message_post(body=_('Results entered, pending review'))

    def action_complete_test(self):
        """Complete the test"""
        if self.state not in ['pending_review', 'in_progress']:
            raise ValidationError(_('Test must be in progress or pending review!'))
        if self.result_value is None and not self.result_text:
            raise ValidationError(_('Please enter test results before completing!'))

        self.state = 'completed'
        self._handle_state_change('pending_review', 'completed')

    def action_verify(self):
        """Verify the test results"""
        if self.state != 'completed':
            raise ValidationError(_('Test must be completed before verification!'))
        if not self.interpretation:
            _logger.warning(f'Test {self.test_type_id.name} verified without interpretation')
        self.state = 'verified'
        self._handle_state_change('completed', 'verified')

    def action_report(self):
        """Mark test as reported"""
        if self.state not in ['completed', 'verified']:
            raise ValidationError(_('Test must be completed or verified before reporting!'))
        self.state = 'reported'
        self._handle_state_change(self.state, 'reported')

    def action_cancel(self):
        """Cancel the test"""
        if self.state in ['reported', 'verified']:
            raise ValidationError(_('Cannot cancel a reported or verified test!'))
        self.state = 'cancelled'
        self._handle_state_change(self.state, 'cancelled')

    def action_reset_to_draft(self):
        """Reset test to draft state"""
        self.state = 'draft'
        self.message_post(body=_('Test reset to draft'))

    def action_set_abnormal_flag(self):
        """Manually set abnormal flag"""
        self.is_abnormal = True
        self.message_post(body=_('Results marked as abnormal manually'))

    def action_clear_abnormal_flag(self):
        """Clear abnormal flag"""
        self.is_abnormal = False
        self.message_post(body=_('Abnormal flag cleared'))

    def action_add_interpretation(self):
        """Open wizard to add interpretation"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Add Interpretation'),
            'res_model': 'lims.interpretation.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_test_line_id': self.id,
                'default_interpretation': self.interpretation,
            },
        }

    def action_add_notes(self):
        """Open wizard to add notes"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Add Notes'),
            'res_model': 'lims.notes.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_test_line_id': self.id,
                'default_notes': self.notes,
            },
        }

    # ===================== VIEW ACTIONS =====================

    def action_view_order(self):
        """View parent test order"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Test Order'),
            'res_model': 'lims.test_order',
            'view_mode': 'form',
            'res_id': self.test_order_id.id,
        }

    def action_view_patient(self):
        """View patient"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Patient'),
            'res_model': 'lims.patient',
            'view_mode': 'form',
            'res_id': self.patient_id.id,
        }

    def action_view_sample(self):
        """View sample"""
        self.ensure_one()
        if not self.sample_id:
            raise ValidationError(_('No sample associated with this test!'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Sample'),
            'res_model': 'lims.sample',
            'view_mode': 'form',
            'res_id': self.sample_id.id,
        }

    def action_view_qc(self):
        """View QC records for this test"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Quality Control'),
            'res_model': 'lims.quality_control',
            'view_mode': 'tree,form',
            'domain': [('test_line_id', '=', self.id)],
        }

    # ===================== UTILITY METHODS =====================

    def get_result_summary(self):
        """Get a summary of the test result"""
        self.ensure_one()
        return {
            'test_name': self.test_type_id.name,
            'result': self.result_display,
            'normal_range': self.normal_range,
            'status': self.validation_status,
            'is_abnormal': self.is_abnormal,
            'is_critical': self.is_critical,
            'interpretation': self.interpretation,
            'technician': self.technician_id.name,
            'completed_date': self.completed_date,
        }

    def get_validation_details(self):
        """Get detailed validation information"""
        self.ensure_one()
        return {
            'status': self.validation_status,
            'message': self.validation_message,
            'is_abnormal': self.is_abnormal,
            'is_critical': self.is_critical,
            'abnormal_low': self.test_type_id.abnormal_low,
            'abnormal_high': self.test_type_id.abnormal_high,
            'critical_low': self.test_type_id.critical_low,
            'critical_high': self.test_type_id.critical_high,
            'normal_range': self.normal_range,
            'result_value': self.result_value,
        }

    def get_result_formatted(self):
        """Get formatted result with unit and status"""
        self.ensure_one()
        status_icons = {
            'normal': '✅',
            'abnormal_low': '⬇️',
            'abnormal_high': '⬆️',
            'critical_low': '🔴',
            'critical_high': '🔴',
            'borderline': '⚠️',
            'no_result': '⏳'
        }
        icon = status_icons.get(self.validation_status, '')
        return f"{icon} {self.result_display}"


class LimsInterpretationWizard(models.TransientModel):
    """
    Wizard for adding interpretation to a test line
    """
    _name = 'lims.interpretation.wizard'
    _description = 'Interpretation Wizard'

    test_line_id = fields.Many2one(
        'lims.test_order_line',
        string='Test Line',
        required=True
    )

    interpretation = fields.Text(
        string='Interpretation',
        required=True,
        help='Clinical interpretation of the results'
    )

    def action_save_interpretation(self):
        """Save the interpretation"""
        self.ensure_one()
        self.test_line_id.write({'interpretation': self.interpretation})
        self.test_line_id.message_post(
            body=_('Interpretation added: %s') % self.interpretation,
            message_type='notification'
        )
        return {'type': 'ir.actions.act_window_close'}


class LimsNotesWizard(models.TransientModel):
    """
    Wizard for adding notes to a test line
    """
    _name = 'lims.notes.wizard'
    _description = 'Notes Wizard'

    test_line_id = fields.Many2one(
        'lims.test_order_line',
        string='Test Line',
        required=True
    )

    notes = fields.Text(
        string='Notes',
        required=True,
        help='Additional notes about the test'
    )

    def action_save_notes(self):
        """Save the notes"""
        self.ensure_one()
        self.test_line_id.write({'notes': self.notes})
        self.test_line_id.message_post(
            body=_('Notes added: %s') % self.notes,
            message_type='notification'
        )
        return {'type': 'ir.actions.act_window_close'}
    