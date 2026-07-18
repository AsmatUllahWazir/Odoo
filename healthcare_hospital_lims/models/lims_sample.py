# -*- coding: utf-8 -*-
"""
Sample Management Module for LIMS
Handles complete sample lifecycle from collection to disposal
"""
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta
import io
import base64
import logging

# Try to import barcode, fallback if not available
try:
    import barcode
    from barcode.writer import ImageWriter
    BARCODE_AVAILABLE = True
except ImportError:
    BARCODE_AVAILABLE = False
    barcode = None
    ImageWriter = None

_logger = logging.getLogger(__name__)


class LimsSample(models.Model):
    """
    Comprehensive Sample Model
    Tracks biological samples through the entire laboratory workflow
    """
    _name = 'lims.sample'
    _description = 'LIMS Sample'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'sample_id'
    _order = 'sample_id desc'

    # ===================== BASIC IDENTIFICATION =====================
    sample_id = fields.Char(
        string='Sample ID',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
        help='Unique identifier for the sample'
    )

    patient_id = fields.Many2one(
        'lims.patient',
        string='Patient',
        required=True,
        tracking=True,
        help='Patient from whom the sample was collected'
    )

    test_order_id = fields.Many2one(
        'lims.test_order',
        string='Test Order',
        required=True,
        tracking=True,
        help='Test order this sample belongs to'
    )

    # ===================== SAMPLE TYPE =====================
    sample_type = fields.Selection([
        ('blood', 'Blood'),
        ('blood_arterial', 'Arterial Blood'),
        ('blood_venous', 'Venous Blood'),
        ('blood_capillary', 'Capillary Blood'),
        ('serum', 'Serum'),
        ('plasma', 'Plasma'),
        ('urine', 'Urine'),
        ('urine_24h', '24-Hour Urine'),
        ('stool', 'Stool'),
        ('sputum', 'Sputum'),
        ('saliva', 'Saliva'),
        ('csf', 'Cerebrospinal Fluid'),
        ('pleural', 'Pleural Fluid'),
        ('peritoneal', 'Peritoneal Fluid'),
        ('synovial', 'Synovial Fluid'),
        ('tissue', 'Tissue'),
        ('biopsy', 'Biopsy'),
        ('swab', 'Swab'),
        ('throat_swab', 'Throat Swab'),
        ('nasal_swab', 'Nasal Swab'),
        ('rectal_swab', 'Rectal Swab'),
        ('wound_swab', 'Wound Swab'),
        ('other', 'Other')
    ], string='Sample Type', required=True, tracking=True)

    # ===================== COLLECTION INFORMATION =====================
    collection_date = fields.Datetime(
        string='Collection Date',
        required=True,
        default=fields.Datetime.now,
        tracking=True,
        help='Date and time of sample collection'
    )

    collector_id = fields.Many2one(
        'hr.employee',
        string='Collected By',
        tracking=True,
        help='Person who collected the sample'
    )

    collection_location = fields.Char(
        string='Collection Location',
        help='Location where the sample was collected (e.g., Ward 3B, OP Room 5)'
    )

    collection_notes = fields.Text(
        string='Collection Notes',
        help='Additional notes about sample collection'
    )

    collection_method = fields.Selection([
        ('venipuncture', 'Venipuncture'),
        ('fingerstick', 'Fingerstick'),
        ('catheter', 'Catheter'),
        ('midstream', 'Midstream Clean Catch'),
        ('catheterization', 'Catheterization'),
        ('aspiration', 'Aspiration'),
        ('biopsy', 'Biopsy'),
        ('swab', 'Swab'),
        ('other', 'Other')
    ], string='Collection Method')

    # ===================== SAMPLE STATUS =====================
    status = fields.Selection([
        ('registered', 'Registered'),
        ('collected', 'Collected'),
        ('received', 'Received in Lab'),
        ('processing', 'Processing'),
        ('analyzed', 'Analyzed'),
        ('reported', 'Reported'),
        ('rejected', 'Rejected'),
        ('discarded', 'Discarded')
    ], string='Status', required=True, default='registered', tracking=True)

    # ===================== BARCODE AND TRACKING =====================
    barcode = fields.Char(
        string='Barcode',
        copy=False,
        help='Barcode for sample tracking'
    )

    barcode_image = fields.Binary(
        string='Barcode Image',
        compute='_compute_barcode_image',
        help='Generated barcode image'
    )

    container_id = fields.Char(
        string='Container ID',
        help='Container or tube identifier'
    )

    storage_location = fields.Char(
        string='Storage Location',
        help='Physical location where the sample is stored'
    )

    storage_temperature = fields.Selection([
        ('room_temp', 'Room Temperature'),
        ('refrigerated', 'Refrigerated (2-8°C)'),
        ('frozen', 'Frozen (-20°C)'),
        ('deep_frozen', 'Deep Frozen (-80°C)'),
        ('liquid_nitrogen', 'Liquid Nitrogen')
    ], string='Storage Temperature')

    # ===================== SAMPLE QUANTITY =====================
    volume = fields.Float(
        string='Volume (ml)',
        help='Volume of sample collected in milliliters'
    )

    quantity = fields.Float(
        string='Quantity',
        help='Quantity of sample (for non-liquid samples)'
    )

    quantity_unit = fields.Selection([
        ('ml', 'Milliliters'),
        ('l', 'Liters'),
        ('g', 'Grams'),
        ('mg', 'Milligrams'),
        ('unit', 'Units'),
        ('other', 'Other')
    ], string='Quantity Unit', default='ml')

    # ===================== QUALITY INDICATORS =====================
    quality_ok = fields.Boolean(
        string='Quality OK',
        default=False,
        help='Whether the sample passed quality check'
    )

    quality_notes = fields.Text(
        string='Quality Notes',
        help='Notes about sample quality'
    )

    hemolysis = fields.Boolean(
        string='Hemolysis Present',
        help='Whether hemolysis is present in the sample'
    )

    lipemia = fields.Boolean(
        string='Lipemia Present',
        help='Whether lipemia is present in the sample'
    )

    icterus = fields.Boolean(
        string='Icterus Present',
        help='Whether icterus is present in the sample'
    )

    clot_present = fields.Boolean(
        string='Clot Present',
        help='Whether a clot is present in the sample'
    )

    # ===================== EXPIRY AND STORAGE =====================
    expiry_date = fields.Date(
        compute='_compute_expiry_date',
        store=True,
        help='Sample expiration date'
    )

    discard_date = fields.Date(
        string='Discard Date',
        help='Date when sample was discarded'
    )

    discard_reason = fields.Text(
        string='Discard Reason',
        help='Reason for discarding the sample'
    )

    # ===================== RELATED FIELDS =====================
    test_line_ids = fields.One2many(
        'lims.test_order_line',
        'sample_id',
        string='Test Lines',
        help='Test lines associated with this sample'
    )

    qc_ids = fields.One2many(
        'lims.quality_control',
        'sample_id',
        string='Quality Controls',
        help='Quality control records for this sample'
    )

    # ===================== COMPUTED FIELDS =====================
    patient_name = fields.Char(
        string='Patient Name',
        compute='_compute_patient_info',
        store=True
    )

    patient_age = fields.Integer(
        string='Patient Age',
        compute='_compute_patient_info',
        store=True
    )

    test_order_name = fields.Char(
        string='Order Name',
        compute='_compute_order_info',
        store=True
    )

    days_old = fields.Integer(
        compute='_compute_age_days',
        store=True,
        help='Age of sample in days'
    )

    is_expired = fields.Boolean(
        compute='_compute_expiry_status',
        store=True,
        help='Whether the sample has expired'
    )

    test_count = fields.Integer(
        compute='_compute_test_count',
        store=True,
        help='Number of tests associated with this sample'
    )

    # ===================== COMPUTE METHODS =====================

    @api.depends('patient_id')
    def _compute_patient_info(self):
        """Compute patient information"""
        for record in self:
            if record.patient_id:
                record.patient_name = record.patient_id.name
                record.patient_age = record.patient_id.age
            else:
                record.patient_name = ''
                record.patient_age = 0

    @api.depends('test_order_id')
    def _compute_order_info(self):
        """Compute order information"""
        for record in self:
            record.test_order_name = record.test_order_id.order_id if record.test_order_id else ''

    @api.depends('collection_date')
    def _compute_age_days(self):
        """Compute age of sample in days"""
        for record in self:
            if record.collection_date:
                delta = fields.Datetime.now() - record.collection_date
                record.days_old = delta.days
            else:
                record.days_old = 0

    @api.depends('collection_date', 'sample_type')
    def _compute_expiry_date(self):
        """Compute sample expiry date based on sample type"""
        expiry_days = {
            'blood': 1,
            'blood_arterial': 1,
            'blood_venous': 1,
            'blood_capillary': 1,
            'serum': 7,
            'plasma': 30,
            'urine': 1,
            'urine_24h': 1,
            'stool': 1,
            'sputum': 2,
            'saliva': 2,
            'csf': 1,
            'pleural': 1,
            'peritoneal': 1,
            'synovial': 1,
            'tissue': 30,
            'biopsy': 30,
            'swab': 2,
            'throat_swab': 2,
            'nasal_swab': 2,
            'rectal_swab': 2,
            'wound_swab': 2,
            'other': 7
        }
        for record in self:
            if record.collection_date:
                days = expiry_days.get(record.sample_type, 7)
                record.expiry_date = (record.collection_date + timedelta(days=days)).date()
            else:
                record.expiry_date = False

    @api.depends('expiry_date')
    def _compute_expiry_status(self):
        """Check if sample has expired"""
        for record in self:
            if record.expiry_date:
                record.is_expired = record.expiry_date < fields.Date.today()
            else:
                record.is_expired = False

    @api.depends('test_line_ids')
    def _compute_test_count(self):
        """Count associated tests"""
        for record in self:
            record.test_count = len(record.test_line_ids)

    @api.depends('sample_id', 'patient_name')
    def _compute_barcode_image(self):
        """Generate barcode image"""
        for record in self:
            if record.barcode and BARCODE_AVAILABLE:
                try:
                    code = barcode.get_barcode_class('code128')
                    barcode_instance = code(record.barcode, writer=ImageWriter())
                    buffer = io.BytesIO()
                    barcode_instance.write(buffer, {'format': 'PNG'})
                    record.barcode_image = base64.b64encode(buffer.getvalue())
                except Exception as e:
                    _logger.warning(f'Could not generate barcode: {str(e)}')
                    record.barcode_image = False
            else:
                record.barcode_image = False

    # ===================== CONSTRAINTS =====================

    @api.constrains('collection_date')
    def _check_collection_date(self):
        """Validate collection date"""
        for record in self:
            if record.collection_date and record.collection_date > fields.Datetime.now():
                raise ValidationError(_('Collection date cannot be in the future!'))
            if record.collection_date and record.collection_date < fields.Datetime.now() - timedelta(days=365):
                raise ValidationError(_('Collection date is more than one year ago!'))

    @api.constrains('volume')
    def _check_volume(self):
        """Validate volume is positive"""
        for record in self:
            if record.volume and record.volume <= 0:
                raise ValidationError(_('Volume must be greater than 0!'))

    @api.constrains('barcode')
    def _check_barcode_unique(self):
        """Ensure barcode is unique"""
        for record in self:
            if record.barcode:
                existing = self.search([('barcode', '=', record.barcode), ('id', '!=', record.id)])
                if existing:
                    raise ValidationError(_('Barcode already exists for sample %s!') % existing[0].sample_id)

    # ===================== CRUD OVERRIDES =====================

    @api.model
    def create(self, vals):
        """Override create to generate sample_id sequence and barcode"""
        if vals.get('sample_id', _('New')) == _('New'):
            vals['sample_id'] = self.env['ir.sequence'].next_by_code('lims.sample') or _('New')

        # Generate barcode if not provided
        if not vals.get('barcode'):
            vals['barcode'] = f"SMP{datetime.now().strftime('%Y%m%d')}{vals['sample_id']}"

        sample = super(LimsSample, self).create(vals)

        # Log creation
        sample.message_post(
            body=_('Sample created: %s for patient %s') % (sample.sample_id, sample.patient_name),
            message_type='notification'
        )

        return sample

    def write(self, vals):
        """Override write to track status changes"""
        for record in self:
            if 'status' in vals:
                old_status = record.status
                new_status = vals['status']
                if old_status != new_status:
                    record._handle_status_change(old_status, new_status)

            result = super(LimsSample, record).write(vals)

        return result

    def _handle_status_change(self, old_status, new_status):
        """Handle status change actions"""
        self.ensure_one()

        status_actions = {
            'collected': self._action_on_collect,
            'received': self._action_on_receive,
            'processing': self._action_on_process,
            'analyzed': self._action_on_analyze,
            'reported': self._action_on_report,
            'rejected': self._action_on_reject,
            'discarded': self._action_on_discard,
        }

        if new_status in status_actions:
            status_actions[new_status]()

    def _action_on_collect(self):
        """Actions when sample is collected"""
        self.collection_date = fields.Datetime.now()
        if not self.collector_id:
            self.collector_id = self.env.user.employee_id.id
        self.message_post(body=_('Sample collected by %s') % self.collector_id.name)

    def _action_on_receive(self):
        """Actions when sample is received in lab"""
        self.message_post(body=_('Sample received in laboratory'))

    def _action_on_process(self):
        """Actions when sample processing starts"""
        self.message_post(body=_('Sample processing started'))

    def _action_on_analyze(self):
        """Actions when sample analysis is complete"""
        self.message_post(body=_('Sample analysis completed'))

    def _action_on_report(self):
        """Actions when sample is reported"""
        self.message_post(body=_('Sample results reported'))

    def _action_on_reject(self):
        """Actions when sample is rejected"""
        if not self.quality_notes:
            raise ValidationError(_('Please provide reason for rejection!'))
        self.message_post(body=_('Sample rejected: %s') % self.quality_notes)

    def _action_on_discard(self):
        """Actions when sample is discarded"""
        self.discard_date = fields.Date.today()
        self.message_post(body=_('Sample discarded'))

    # ===================== WORKFLOW ACTIONS =====================

    def action_collect(self):
        """Mark sample as collected"""
        if self.status != 'registered':
            raise UserError(_('Sample is not in registered state!'))
        self.status = 'collected'
        self._action_on_collect()

    def action_receive(self):
        """Mark sample as received in lab"""
        if self.status != 'collected':
            raise UserError(_('Sample must be collected first!'))
        self.status = 'received'
        self._action_on_receive()

    def action_process(self):
        """Mark sample as processing"""
        if self.status not in ['received', 'processing']:
            raise UserError(_('Sample must be received before processing!'))
        self.status = 'processing'
        self._action_on_process()

    def action_analyze(self):
        """Mark sample as analyzed"""
        if self.status != 'processing':
            raise UserError(_('Sample must be processing before analysis!'))
        self.status = 'analyzed'
        self._action_on_analyze()

    def action_report(self):
        """Mark sample as reported"""
        if self.status != 'analyzed':
            raise UserError(_('Sample must be analyzed before reporting!'))
        self.status = 'reported'
        self._action_on_report()

    def action_reject(self):
        """Reject sample"""
        if self.status in ['rejected', 'discarded']:
            raise UserError(_('Sample is already rejected/discarded!'))
        if not self.quality_notes:
            raise ValidationError(_('Please provide reason for rejection in quality notes!'))
        self.status = 'rejected'
        self._action_on_reject()

    def action_discard(self):
        """Discard sample"""
        if self.status == 'discarded':
            raise UserError(_('Sample is already discarded!'))
        if not self.discard_reason:
            raise ValidationError(_('Please provide reason for discarding!'))
        self.status = 'discarded'
        self._action_on_discard()

    def action_restore(self):
        """Restore a rejected/discarded sample"""
        if self.status not in ['rejected', 'discarded']:
            raise UserError(_('Sample is not in rejected/discarded state!'))
        self.status = 'collected'  # Restore to collected state
        self.message_post(body=_('Sample restored from %s') % ('rejection' if self.status == 'rejected' else 'discard'))

    def action_print_barcode(self):
        """Print sample barcode"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Sample Barcode'),
            'res_model': 'lims.barcode.print.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_sample_id': self.id},
        }

    def action_generate_barcode(self):
        """Generate new barcode for sample"""
        self.ensure_one()
        self.barcode = f"SMP{datetime.now().strftime('%Y%m%d')}{self.id}"
        self.message_post(body=_('New barcode generated: %s') % self.barcode)

    # ===================== QUALITY CONTROL ACTIONS =====================

    def action_check_quality(self):
        """Perform quality check on sample"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Sample Quality Check'),
            'res_model': 'lims.sample.quality.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_sample_id': self.id},
        }

    def action_mark_quality_ok(self):
        """Mark sample quality as OK"""
        self.quality_ok = True
        self.quality_notes = 'Quality check passed'
        self.message_post(body=_('Sample quality check passed'))

    def action_mark_quality_not_ok(self):
        """Mark sample quality as NOT OK"""
        self.quality_ok = False
        self.message_post(body=_('Sample quality check failed'))

    # ===================== VIEW ACTIONS =====================

    def action_view_tests(self):
        """View tests associated with this sample"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Tests - %s') % self.sample_id,
            'res_model': 'lims.test_order_line',
            'view_mode': 'tree,form',
            'domain': [('sample_id', '=', self.id)],
            'context': {'default_sample_id': self.id},
        }

    def action_view_patient(self):
        """View patient for this sample"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Patient'),
            'res_model': 'lims.patient',
            'view_mode': 'form',
            'res_id': self.patient_id.id,
        }

    def action_view_order(self):
        """View test order for this sample"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Test Order'),
            'res_model': 'lims.test_order',
            'view_mode': 'form',
            'res_id': self.test_order_id.id,
        }

    # ===================== UTILITY METHODS =====================

    def get_sample_summary(self):
        """Get a summary of the sample"""
        self.ensure_one()
        return {
            'sample_id': self.sample_id,
            'patient': self.patient_name,
            'type': self.sample_type,
            'status': self.status,
            'collection_date': self.collection_date,
            'days_old': self.days_old,
            'test_count': self.test_count,
            'quality_ok': self.quality_ok,
            'is_expired': self.is_expired,
        }

    def get_quality_status(self):
        """Get quality status details"""
        self.ensure_one()
        statuses = []
        if self.hemolysis:
            statuses.append('Hemolysis')
        if self.lipemia:
            statuses.append('Lipemia')
        if self.icterus:
            statuses.append('Icterus')
        if self.clot_present:
            statuses.append('Clot')

        return {
            'quality_ok': self.quality_ok,
            'issues': statuses,
            'notes': self.quality_notes,
        }

    def get_storage_info(self):
        """Get storage information"""
        self.ensure_one()
        return {
            'location': self.storage_location,
            'temperature': self.storage_temperature,
            'container': self.container_id,
            'expiry_date': self.expiry_date,
            'days_until_expiry': (self.expiry_date - fields.Date.today()).days if self.expiry_date else None,
        }

    # ===================== STATISTICAL METHODS =====================

    @api.model
    def get_sample_stats(self, period='month'):
        """Get sample statistics"""
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

        samples = self.search([
            ('collection_date', '>=', start_date),
            ('status', '!=', 'discarded')
        ])

        return {
            'total_samples': len(samples),
            'collected': len(samples.filtered(lambda s: s.status == 'collected')),
            'received': len(samples.filtered(lambda s: s.status == 'received')),
            'processing': len(samples.filtered(lambda s: s.status == 'processing')),
            'analyzed': len(samples.filtered(lambda s: s.status == 'analyzed')),
            'reported': len(samples.filtered(lambda s: s.status == 'reported')),
            'rejected': len(samples.filtered(lambda s: s.status == 'rejected')),
            'quality_issues': len(samples.filtered(lambda s: not s.quality_ok)),
            'expired': len(samples.filtered(lambda s: s.is_expired)),
        }


class LimsSampleQualityWizard(models.TransientModel):
    """
    Wizard for performing sample quality checks
    """
    _name = 'lims.sample.quality.wizard'
    _description = 'Sample Quality Check Wizard'

    sample_id = fields.Many2one(
        'lims.sample',
        string='Sample',
        required=True
    )

    quality_ok = fields.Boolean(
        string='Quality OK',
        default=True
    )

    hemolysis = fields.Boolean(string='Hemolysis Present')
    lipemia = fields.Boolean(string='Lipemia Present')
    icterus = fields.Boolean(string='Icterus Present')
    clot_present = fields.Boolean(string='Clot Present')

    quality_notes = fields.Text(
        string='Quality Notes',
        help='Detailed notes about sample quality'
    )

    def action_submit_quality_check(self):
        """Submit the quality check results"""
        self.ensure_one()

        sample = self.sample_id
        sample.write({
            'quality_ok': self.quality_ok,
            'hemolysis': self.hemolysis,
            'lipemia': self.lipemia,
            'icterus': self.icterus,
            'clot_present': self.clot_present,
            'quality_notes': self.quality_notes or 'Quality check completed',
        })

        sample.message_post(
            body=_('Quality check completed. Status: %s') % ('Passed' if self.quality_ok else 'Failed'),
            message_type='notification'
        )

        return {'type': 'ir.actions.act_window_close'}


class LimsBarcodePrintWizard(models.TransientModel):
    """
    Wizard for printing sample barcodes
    """
    _name = 'lims.barcode.print.wizard'
    _description = 'Barcode Print Wizard'

    sample_id = fields.Many2one(
        'lims.sample',
        string='Sample',
        required=True
    )

    barcode_format = fields.Selection([
        ('code128', 'Code 128'),
        ('code39', 'Code 39'),
        ('ean13', 'EAN-13'),
        ('upc', 'UPC-A')
    ], string='Barcode Format', default='code128')

    print_quantity = fields.Integer(
        string='Print Quantity',
        default=2,
        help='Number of labels to print'
    )

    include_patient = fields.Boolean(
        string='Include Patient Name',
        default=True
    )

    include_order = fields.Boolean(
        string='Include Order ID',
        default=True
    )

    def action_print_barcode(self):
        """Generate and print barcode labels"""
        self.ensure_one()
        sample = self.sample_id

        # Generate barcode data
        barcode_data = {
            'sample_id': sample.sample_id,
            'patient_name': sample.patient_name if self.include_patient else '',
            'order_id': sample.test_order_id.order_id if self.include_order else '',
            'barcode': sample.barcode,
        }

        # This would trigger a report for barcode printing
        return {
            'type': 'ir.actions.act_window',
            'name': _('Print Barcode'),
            'res_model': 'lims.barcode.print.report',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_sample_id': sample.id,
                'default_barcode_data': barcode_data,
                'default_quantity': self.print_quantity,
            },
        }
