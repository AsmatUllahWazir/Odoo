# -*- coding: utf-8 -*-
"""
Instrument Management Module for LIMS
Manages laboratory instruments, maintenance, calibration, and validation
"""
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class LimsInstrument(models.Model):
    """
    Comprehensive Instrument Model
    Manages all laboratory equipment with maintenance and calibration tracking
    """
    _name = 'lims.instrument'
    _description = 'LIMS Instrument'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'name'

    # ===================== BASIC IDENTIFICATION =====================
    name = fields.Char(
        string='Instrument Name',
        required=True,
        tracking=True,
        help='Full name of the laboratory instrument'
    )

    code = fields.Char(
        string='Instrument Code',
        required=True,
        copy=False,
        tracking=True,
        help='Unique code for the instrument'
    )

    model = fields.Char(
        string='Model',
        tracking=True,
        help='Instrument model number'
    )

    serial_number = fields.Char(
        string='Serial Number',
        copy=False,
        help='Instrument serial number'
    )

    manufacturer = fields.Char(
        string='Manufacturer',
        tracking=True,
        help='Manufacturer of the instrument'
    )

    # ===================== CATEGORY AND TYPE =====================
    category = fields.Selection([
        ('analyzer', 'Analyzer'),
        ('centrifuge', 'Centrifuge'),
        ('microscope', 'Microscope'),
        ('incubator', 'Incubator'),
        ('refrigerator', 'Refrigerator'),
        ('freezer', 'Freezer'),
        ('water_bath', 'Water Bath'),
        ('autoclave', 'Autoclave'),
        ('balance', 'Balance'),
        ('ph_meter', 'pH Meter'),
        ('spectrophotometer', 'Spectrophotometer'),
        ('chromatograph', 'Chromatograph'),
        ('mass_spec', 'Mass Spectrometer'),
        ('pcr', 'PCR Machine'),
        ('sequencer', 'Sequencer'),
        ('other', 'Other')
    ], string='Instrument Category', required=True, default='other')

    instrument_type = fields.Selection([
        ('analytical', 'Analytical'),
        ('diagnostic', 'Diagnostic'),
        ('preparative', 'Preparative'),
        ('storage', 'Storage'),
        ('safety', 'Safety'),
        ('other', 'Other')
    ], string='Instrument Type', default='analytical')

    # ===================== ACQUISITION INFORMATION =====================
    purchase_date = fields.Date(
        string='Purchase Date',
        tracking=True,
        help='Date of purchase'
    )

    warranty_expiry = fields.Date(
        string='Warranty Expiry',
        help='Warranty expiry date'
    )

    purchase_price = fields.Monetary(
        string='Purchase Price',
        currency_field='currency_id',
        help='Purchase price of the instrument'
    )

    current_value = fields.Monetary(
        compute='_compute_depreciation',
        store=True,
        currency_field='currency_id',
        help='Current depreciated value'
    )

    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id.id
    )

    # ===================== CALIBRATION INFORMATION =====================
    calibration_date = fields.Date(
        string='Last Calibration Date',
        tracking=True,
        help='Date of last calibration'
    )

    next_calibration_date = fields.Date(
        compute='_compute_calibration_dates',
        store=True,
        help='Date of next scheduled calibration'
    )

    calibration_frequency = fields.Integer(
        string='Calibration Frequency (days)',
        default=180,
        help='Number of days between calibrations'
    )

    calibration_due = fields.Boolean(
        compute='_compute_calibration_status',
        store=True,
        help='Whether calibration is due'
    )

    calibration_provider = fields.Char(
        string='Calibration Provider',
        help='Name of the calibration service provider'
    )

    calibration_certificate = fields.Binary(
        string='Calibration Certificate',
        help='Calibration certificate file'
    )

    certificate_filename = fields.Char(
        string='Certificate Filename',
        help='Name of the uploaded certificate'
    )

    # ===================== MAINTENANCE INFORMATION =====================
    maintenance_date = fields.Date(
        string='Last Maintenance Date',
        tracking=True,
        help='Date of last maintenance'
    )

    next_maintenance_date = fields.Date(
        compute='_compute_maintenance_dates',
        store=True,
        help='Date of next scheduled maintenance'
    )

    maintenance_frequency = fields.Integer(
        string='Maintenance Frequency (days)',
        default=90,
        help='Number of days between maintenance'
    )

    maintenance_due = fields.Boolean(
        compute='_compute_maintenance_status',
        store=True,
        help='Whether maintenance is due'
    )

    maintenance_notes = fields.Text(
        string='Maintenance Notes',
        help='Notes about maintenance activities'
    )

    # ===================== STATUS AND OPERATIONAL =====================
    status = fields.Selection([
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('maintenance', 'Under Maintenance'),
        ('calibration_due', 'Calibration Due'),
        ('repair', 'Needs Repair'),
        ('obsolete', 'Obsolete'),
        ('decommissioned', 'Decommissioned')
    ], string='Status', required=True, default='active', tracking=True)

    operational_hours = fields.Float(
        string='Operational Hours',
        help='Total operational hours',
        tracking=True
    )

    last_used_date = fields.Datetime(
        string='Last Used',
        help='Date and time the instrument was last used'
    )

    # ===================== RELATIONSHIPS =====================
    qc_ids = fields.One2many(
        'lims.quality_control',
        'instrument_id',
        string='QC Records',
        help='Quality control records for this instrument'
    )

    test_type_ids = fields.Many2many(
        'lims.test_type',
        string='Supported Test Types',
        help='Test types that can be performed on this instrument'
    )

    # ===================== COMPUTED FIELDS =====================
    last_qc_date = fields.Datetime(
        compute='_compute_qc_info',
        store=True,
        help='Date of the last quality control'
    )

    last_qc_result = fields.Boolean(
        compute='_compute_qc_info',
        store=True,
        help='Result of the last quality control'
    )

    qc_pass_rate = fields.Float(
        compute='_compute_qc_info',
        store=True,
        help='Percentage of QC passes'
    )

    total_qc_count = fields.Integer(
        compute='_compute_qc_info',
        store=True,
        help='Total number of QC records'
    )

    failed_qc_count = fields.Integer(
        compute='_compute_qc_info',
        store=True,
        help='Number of failed QC records'
    )

    age_days = fields.Integer(
        compute='_compute_age',
        store=True,
        help='Age of the instrument in days'
    )

    is_under_warranty = fields.Boolean(
        compute='_compute_warranty_status',
        store=True,
        help='Whether the instrument is under warranty'
    )

    active = fields.Boolean(
        string='Active',
        default=True,
        help='Inactive instruments are archived'
    )

    # ===================== COMPUTE METHODS =====================

    @api.depends('calibration_date', 'calibration_frequency')
    def _compute_calibration_dates(self):
        """Compute next calibration date"""
        for record in self:
            if record.calibration_date:
                record.next_calibration_date = record.calibration_date + timedelta(days=record.calibration_frequency)
            else:
                record.next_calibration_date = False

    @api.depends('next_calibration_date')
    def _compute_calibration_status(self):
        """Check if calibration is due"""
        for record in self:
            if record.next_calibration_date:
                record.calibration_due = record.next_calibration_date <= fields.Date.today()
            else:
                record.calibration_due = False

    @api.depends('maintenance_date', 'maintenance_frequency')
    def _compute_maintenance_dates(self):
        """Compute next maintenance date"""
        for record in self:
            if record.maintenance_date:
                record.next_maintenance_date = record.maintenance_date + timedelta(days=record.maintenance_frequency)
            else:
                record.next_maintenance_date = False

    @api.depends('next_maintenance_date')
    def _compute_maintenance_status(self):
        """Check if maintenance is due"""
        for record in self:
            if record.next_maintenance_date:
                record.maintenance_due = record.next_maintenance_date <= fields.Date.today()
            else:
                record.maintenance_due = False

    @api.depends('qc_ids', 'qc_ids.is_passed')
    def _compute_qc_info(self):
        """Compute QC statistics for the instrument"""
        for record in self:
            qcs = record.qc_ids
            record.total_qc_count = len(qcs)
            record.failed_qc_count = len(qcs.filtered(lambda q: not q.is_passed))

            if qcs:
                record.last_qc_date = max(qcs.mapped('date'))
                record.last_qc_result = qcs.sorted('date', reverse=True)[0].is_passed
                passed = len(qcs.filtered(lambda q: q.is_passed))
                record.qc_pass_rate = (passed / len(qcs)) * 100
            else:
                record.last_qc_date = False
                record.last_qc_result = False
                record.qc_pass_rate = 0

    @api.depends('purchase_date')
    def _compute_age(self):
        """Compute age of instrument in days"""
        for record in self:
            if record.purchase_date:
                record.age_days = (fields.Date.today() - record.purchase_date).days
            else:
                record.age_days = 0

    @api.depends('purchase_price', 'purchase_date')
    def _compute_depreciation(self):
        """Compute current depreciated value (straight-line method)"""
        for record in self:
            if record.purchase_price and record.purchase_date:
                # Assume 5-year depreciation (1825 days)
                total_days = 1825
                age_days = record.age_days
                if age_days >= total_days:
                    record.current_value = 0
                else:
                    depreciation_per_day = record.purchase_price / total_days
                    record.current_value = record.purchase_price - (depreciation_per_day * age_days)
            else:
                record.current_value = record.purchase_price or 0

    @api.depends('warranty_expiry')
    def _compute_warranty_status(self):
        """Check warranty status"""
        for record in self:
            if record.warranty_expiry:
                record.is_under_warranty = record.warranty_expiry >= fields.Date.today()
            else:
                record.is_under_warranty = False

    # ===================== CONSTRAINTS =====================

    @api.constrains('code')
    def _check_code_unique(self):
        """Ensure instrument code is unique"""
        for record in self:
            existing = self.search([('code', '=', record.code), ('id', '!=', record.id)])
            if existing:
                raise ValidationError(_('Instrument code must be unique!'))

    @api.constrains('calibration_frequency')
    def _check_calibration_frequency(self):
        """Validate calibration frequency"""
        for record in self:
            if record.calibration_frequency <= 0:
                raise ValidationError(_('Calibration frequency must be positive!'))

    @api.constrains('maintenance_frequency')
    def _check_maintenance_frequency(self):
        """Validate maintenance frequency"""
        for record in self:
            if record.maintenance_frequency <= 0:
                raise ValidationError(_('Maintenance frequency must be positive!'))

    # ===================== CRUD OVERRIDES =====================

    @api.model
    def create(self, vals):
        """Override create to generate code if not provided"""
        if not vals.get('code'):
            vals['code'] = self.env['ir.sequence'].next_by_code('lims.instrument') or 'INS-00001'

        instrument = super(LimsInstrument, self).create(vals)

        instrument.message_post(
            body=_('Instrument created: %s') % instrument.name,
            message_type='notification'
        )

        return instrument

    # ===================== WORKFLOW ACTIONS =====================

    def action_calibrate(self):
        """Record a new calibration"""
        self.ensure_one()
        self.calibration_date = fields.Date.today()
        self.status = 'active'
        self.message_post(body=_('Instrument calibrated successfully!'))

    def action_calibrate_with_provider(self):
        """Calibrate with external provider"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Record Calibration'),
            'res_model': 'lims.calibration.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_instrument_id': self.id},
        }

    def action_perform_maintenance(self):
        """Record maintenance activity"""
        self.ensure_one()
        self.maintenance_date = fields.Date.today()
        self.message_post(body=_('Maintenance performed on instrument!'))

    def action_check_status(self):
        """Check instrument status and update"""
        self.ensure_one()
        if self.calibration_due:
            self.status = 'calibration_due'
            self.message_post(body=_('Calibration is due for this instrument!'))
        if self.maintenance_due:
            self.status = 'maintenance'
            self.message_post(body=_('Maintenance is due for this instrument!'))

    def action_mark_repair(self):
        """Mark instrument for repair"""
        self.ensure_one()
        self.status = 'repair'
        self.message_post(body=_('Instrument marked for repair!'))

    def action_mark_decommission(self):
        """Decommission the instrument"""
        self.ensure_one()
        if not self.notes:
            raise ValidationError(_('Please provide reason for decommissioning!'))
        self.status = 'decommissioned'
        self.active = False
        self.message_post(body=_('Instrument decommissioned!'))

    def action_activate(self):
        """Activate the instrument"""
        self.ensure_one()
        self.status = 'active'
        self.active = True
        self.message_post(body=_('Instrument activated!'))

    def action_record_usage(self):
        """Record instrument usage"""
        self.ensure_one()
        self.last_used_date = fields.Datetime.now()
        self.operational_hours += 1  # Assuming 1 hour usage
        self.message_post(body=_('Instrument usage recorded!'))

    # ===================== VIEW ACTIONS =====================

    def action_view_qc_records(self):
        """View QC records for this instrument"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('QC Records - %s') % self.name,
            'res_model': 'lims.quality_control',
            'view_mode': 'tree,form',
            'domain': [('instrument_id', '=', self.id)],
            'context': {'default_instrument_id': self.id},
        }

    def action_view_test_types(self):
        """View test types supported by this instrument"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Supported Tests - %s') % self.name,
            'res_model': 'lims.test_type',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.test_type_ids.ids)],
        }

    # ===================== UTILITY METHODS =====================

    def get_instrument_summary(self):
        """Get a summary of the instrument"""
        self.ensure_one()
        return {
            'name': self.name,
            'code': self.code,
            'status': self.status,
            'category': self.category,
            'age_days': self.age_days,
            'calibration_due': self.calibration_due,
            'maintenance_due': self.maintenance_due,
            'qc_pass_rate': self.qc_pass_rate,
            'is_under_warranty': self.is_under_warranty,
            'last_used': self.last_used_date,
        }

    def get_calibration_history(self):
        """Get calibration history"""
        self.ensure_one()
        qcs = self.qc_ids.filtered(lambda q: q.qc_type == 'instrument_calibration')
        return {
            'total_calibrations': len(qcs),
            'last_calibration': self.calibration_date,
            'next_calibration': self.next_calibration_date,
            'calibration_provider': self.calibration_provider,
            'history': qcs.mapped('date'),
        }

    def get_maintenance_history(self):
        """Get maintenance history"""
        self.ensure_one()
        return {
            'last_maintenance': self.maintenance_date,
            'next_maintenance': self.next_maintenance_date,
            'notes': self.maintenance_notes,
        }

    # ===================== STATISTICAL METHODS =====================

    @api.model
    def get_instrument_stats(self):
        """Get comprehensive instrument statistics"""
        instruments = self.search([])
        return {
            'total': len(instruments),
            'active': len(instruments.filtered(lambda i: i.status == 'active')),
            'maintenance': len(instruments.filtered(lambda i: i.status == 'maintenance')),
            'calibration_due': len(instruments.filtered(lambda i: i.calibration_due)),
            'repair': len(instruments.filtered(lambda i: i.status == 'repair')),
            'decommissioned': len(instruments.filtered(lambda i: i.status == 'decommissioned')),
            'under_warranty': len(instruments.filtered(lambda i: i.is_under_warranty)),
            'avg_qc_pass_rate': sum(instruments.mapped('qc_pass_rate')) / max(len(instruments), 1),
        }


class LimsCalibrationWizard(models.TransientModel):
    """
    Wizard for recording instrument calibration
    """
    _name = 'lims.calibration.wizard'
    _description = 'Calibration Wizard'

    instrument_id = fields.Many2one(
        'lims.instrument',
        string='Instrument',
        required=True
    )

    calibration_date = fields.Date(
        string='Calibration Date',
        required=True,
        default=fields.Date.today
    )

    calibration_provider = fields.Char(
        string='Calibration Provider',
        required=True
    )

    calibration_certificate = fields.Binary(
        string='Calibration Certificate'
    )

    certificate_filename = fields.Char(
        string='Certificate Filename'
    )

    notes = fields.Text(
        string='Notes',
        help='Additional notes about calibration'
    )

    def action_record_calibration(self):
        """Record the calibration"""
        self.ensure_one()

        self.instrument_id.write({
            'calibration_date': self.calibration_date,
            'calibration_provider': self.calibration_provider,
            'calibration_certificate': self.calibration_certificate,
            'certificate_filename': self.certificate_filename,
            'status': 'active',
        })

        self.instrument_id.message_post(
            body=_('Calibration recorded. Provider: %s') % self.calibration_provider,
            message_type='notification'
        )

        return {'type': 'ir.actions.act_window_close'}
