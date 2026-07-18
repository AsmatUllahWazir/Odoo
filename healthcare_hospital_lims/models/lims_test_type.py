# -*- coding: utf-8 -*-
"""
Test Type Master Data Module for LIMS
Defines all available laboratory tests with their specifications, pricing, and validation rules
"""
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class LimsTestType(models.Model):
    """
    Comprehensive Test Type Model
    Master data for laboratory tests with full specifications and configurations
    """
    _name = 'lims.test_type'
    _description = 'LIMS Test Type'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'code'

    # ===================== BASIC IDENTIFICATION =====================
    name = fields.Char(
        string='Test Name',
        required=True,
        tracking=True,
        help='Full name of the laboratory test'
    )

    code = fields.Char(
        string='Test Code',
        required=True,
        tracking=True,
        help='Short code or abbreviation for the test'
    )

    short_name = fields.Char(
        string='Short Name',
        help='Abbreviated name for displays'
    )

    description = fields.Html(
        string='Description',
        help='Detailed description of the test'
    )

    # ===================== CATEGORY AND CLASSIFICATION =====================
    category = fields.Selection([
        ('hematology', 'Hematology'),
        ('biochemistry', 'Biochemistry'),
        ('microbiology', 'Microbiology'),
        ('immunology', 'Immunology'),
        ('serology', 'Serology'),
        ('pathology', 'Pathology'),
        ('genetics', 'Genetics'),
        ('molecular', 'Molecular Diagnostics'),
        ('endocrinology', 'Endocrinology'),
        ('toxicology', 'Toxicology'),
        ('histology', 'Histology'),
        ('cytology', 'Cytology'),
        ('urinalysis', 'Urinalysis'),
        ('coagulation', 'Coagulation'),
        ('blood_bank', 'Blood Bank'),
        ('other', 'Other')
    ], string='Category', required=True, default='other', tracking=True)

    sub_category = fields.Char(
        string='Sub-Category',
        help='More specific categorization'
    )

    test_type = fields.Selection([
        ('quantitative', 'Quantitative'),
        ('qualitative', 'Qualitative'),
        ('semi_quantitative', 'Semi-Quantitative'),
        ('morphological', 'Morphological'),
        ('functional', 'Functional'),
        ('molecular', 'Molecular')
    ], string='Test Type', required=True, default='quantitative')

    # ===================== PRICING AND BUSINESS =====================
    price = fields.Monetary(
        string='Price',
        required=True,
        default=0.0,
        currency_field='currency_id',
        tracking=True,
        help='Standard price for this test'
    )

    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id.id
    )

    cost = fields.Monetary(
        string='Cost',
        currency_field='currency_id',
        help='Cost of performing the test'
    )

    margin = fields.Monetary(
        compute='_compute_margin',
        store=True,
        currency_field='currency_id',
        help='Profit margin'
    )

    margin_percentage = fields.Float(
        compute='_compute_margin',
        store=True,
        help='Profit margin percentage'
    )

    product_id = fields.Many2one(
        'product.product',
        string='Product',
        domain="[('type', '=', 'service')]",
        help='Linked product for invoicing'
    )

    product_categ_id = fields.Many2one(
        'product.category',
        string='Product Category',
        help='Product category for reporting'
    )

    # ===================== SAMPLE REQUIREMENTS =====================
    required_sample_type = fields.Selection([
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
        ('wound_swab', 'Wound Swab'),
        ('other', 'Other')
    ], string='Sample Type', required=True, default='blood', tracking=True)

    sample_volume = fields.Char(
        string='Sample Volume',
        help='Required volume of sample (e.g., 5ml, 10ml)'
    )

    sample_container = fields.Char(
        string='Sample Container',
        help='Recommended container type (e.g., Purple top tube, Sterile container)'
    )

    sample_stability = fields.Char(
        string='Sample Stability',
        help='Stability of sample after collection (e.g., 24 hours at room temperature)'
    )

    special_preparation = fields.Text(
        string='Special Preparation',
        help='Patient preparation instructions before sample collection'
    )

    special_handling = fields.Text(
        string='Special Handling',
        help='Special handling instructions for the sample'
    )

    # ===================== TURNAROUND AND RESULTS =====================
    turnaround_time = fields.Integer(
        string='Turnaround Time (hours)',
        required=True,
        default=24,
        tracking=True,
        help='Expected time to deliver results in hours'
    )

    minimum_tat = fields.Integer(
        string='Minimum TAT (hours)',
        help='Minimum possible turnaround time'
    )

    maximum_tat = fields.Integer(
        string='Maximum TAT (hours)',
        help='Maximum acceptable turnaround time'
    )

    normal_range = fields.Text(
        string='Normal Range',
        help='Normal reference range for the test results'
    )

    abnormal_high = fields.Float(
        string='Abnormal High Limit',
        help='Value above this is considered abnormally high'
    )

    abnormal_low = fields.Float(
        string='Abnormal Low Limit',
        help='Value below this is considered abnormally low'
    )

    critical_high = fields.Float(
        string='Critical High Limit',
        help='Critical high value requiring immediate attention'
    )

    critical_low = fields.Float(
        string='Critical Low Limit',
        help='Critical low value requiring immediate attention'
    )

    unit = fields.Char(
        string='Unit',
        help='Unit of measurement for test results'
    )

    decimal_places = fields.Integer(
        string='Decimal Places',
        default=2,
        help='Number of decimal places for results'
    )

    # ===================== QUALITY CONTROL =====================
    requires_qc = fields.Boolean(
        string='Requires Quality Control',
        default=True,
        help='Whether quality control is required for this test'
    )

    qc_frequency = fields.Selection([
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('batch', 'Per Batch'),
        ('shift', 'Per Shift')
    ], string='QC Frequency', default='daily')

    qc_target = fields.Float(
        string='QC Target',
        help='Target value for quality control'
    )

    qc_tolerance = fields.Float(
        string='QC Tolerance',
        default=5.0,
        help='Tolerance for quality control'
    )

    # ===================== METHODOLOGY =====================
    methodology = fields.Text(
        string='Methodology',
        help='Method used to perform the test'
    )

    instrument_type = fields.Char(
        string='Instrument Type',
        help='Type of instrument required'
    )

    reagents = fields.Text(
        string='Reagents Required',
        help='List of required reagents'
    )

    calibrators = fields.Text(
        string='Calibrators',
        help='Calibration requirements'
    )

    # ===================== REFERENCE RANGES =====================
    age_specific = fields.Boolean(
        string='Age-Specific Ranges',
        default=False,
        help='Whether reference ranges are age-specific'
    )

    gender_specific = fields.Boolean(
        string='Gender-Specific Ranges',
        default=False,
        help='Whether reference ranges are gender-specific'
    )

    pregnancy_specific = fields.Boolean(
        string='Pregnancy-Specific Ranges',
        default=False,
        help='Whether reference ranges differ in pregnancy'
    )

    # ===================== STATUS =====================
    active = fields.Boolean(
        string='Active',
        default=True,
        help='Inactive tests are not available for ordering'
    )

    is_stat_available = fields.Boolean(
        string='STAT Available',
        default=True,
        help='Whether this test can be ordered as STAT'
    )

    is_esoteric = fields.Boolean(
        string='Esoteric Test',
        default=False,
        help='Whether this is a specialized/esoteric test'
    )

    requires_specialist = fields.Boolean(
        string='Requires Specialist',
        default=False,
        help='Whether a specialist is required to perform this test'
    )

    # ===================== RELATIONSHIPS =====================
    order_line_ids = fields.One2many(
        'lims.test_order_line',
        'test_type_id',
        string='Order Lines',
        help='Test order lines using this test type'
    )

    qc_ids = fields.One2many(
        'lims.quality_control',
        'test_type_id',
        string='QC Records',
        help='Quality control records for this test type'
    )

    template_ids = fields.One2many(
        'lims.result_template',
        'test_type_id',
        string='Result Templates',
        help='Result templates for this test type'
    )

    instrument_ids = fields.Many2many(
        'lims.instrument',
        string='Compatible Instruments',
        help='Instruments that can perform this test'
    )

    # ===================== COMPUTED FIELDS =====================
    total_orders = fields.Integer(
        compute='_compute_statistics',
        store=True,
        help='Total number of orders for this test'
    )

    average_price = fields.Monetary(
        compute='_compute_statistics',
        store=True,
        currency_field='currency_id',
        help='Average price across all orders'
    )

    total_revenue = fields.Monetary(
        compute='_compute_statistics',
        store=True,
        currency_field='currency_id',
        help='Total revenue from this test'
    )

    abnormal_rate = fields.Float(
        compute='_compute_statistics',
        store=True,
        help='Percentage of abnormal results'
    )

    qc_pass_rate = fields.Float(
        compute='_compute_statistics',
        store=True,
        help='Quality control pass rate'
    )

    # ===================== COMPUTE METHODS =====================

    @api.depends('price', 'cost')
    def _compute_margin(self):
        """Compute profit margin"""
        for record in self:
            if record.cost and record.price:
                record.margin = record.price - record.cost
                record.margin_percentage = (record.margin / record.price) * 100
            else:
                record.margin = 0
                record.margin_percentage = 0

    @api.depends('order_line_ids', 'order_line_ids.test_order_id.amount_total',
                 'order_line_ids.is_abnormal', 'qc_ids', 'qc_ids.is_passed')
    def _compute_statistics(self):
        """Compute comprehensive statistics for the test type"""
        for record in self:
            lines = record.order_line_ids
            record.total_orders = len(lines)

            # Revenue
            record.total_revenue = sum(lines.mapped('subtotal'))

            # Average price
            record.average_price = record.total_revenue / len(lines) if lines else 0

            # Abnormal rate
            abnormal = len(lines.filtered(lambda l: l.is_abnormal))
            record.abnormal_rate = (abnormal / len(lines) * 100) if lines else 0

            # QC pass rate
            qcs = record.qc_ids
            passed = len(qcs.filtered(lambda q: q.is_passed))
            record.qc_pass_rate = (passed / len(qcs) * 100) if qcs else 0

    # ===================== CONSTRAINTS =====================

    _sql_constraints = [
        ('unique_code', 'unique(code)', 'The test code must be unique!'),
        ('unique_name', 'unique(name)', 'The test name must be unique!'),
    ]

    @api.constrains('price', 'cost')
    def _check_prices(self):
        """Validate pricing"""
        for record in self:
            if record.price < 0:
                raise ValidationError(_('Price cannot be negative!'))
            if record.cost and record.cost < 0:
                raise ValidationError(_('Cost cannot be negative!'))
            if record.cost and record.price < record.cost:
                _logger.warning(f'Test {record.name}: Price is less than cost')

    @api.constrains('turnaround_time', 'minimum_tat', 'maximum_tat')
    def _check_tat(self):
        """Validate turnaround times"""
        for record in self:
            if record.turnaround_time <= 0:
                raise ValidationError(_('Turnaround time must be positive!'))
            if record.minimum_tat and record.maximum_tat:
                if record.minimum_tat > record.maximum_tat:
                    raise ValidationError(_('Minimum TAT cannot exceed Maximum TAT!'))

    @api.constrains('abnormal_low', 'abnormal_high', 'critical_low', 'critical_high')
    def _check_ranges(self):
        """Validate reference ranges"""
        for record in self:
            if record.abnormal_low and record.abnormal_high:
                if record.abnormal_low >= record.abnormal_high:
                    raise ValidationError(_('Abnormal low limit must be less than abnormal high limit!'))
            if record.critical_low and record.critical_high:
                if record.critical_low >= record.critical_high:
                    raise ValidationError(_('Critical low limit must be less than critical high limit!'))
            if record.critical_low and record.abnormal_low:
                if record.critical_low >= record.abnormal_low:
                    raise ValidationError(_('Critical low limit must be less than abnormal low limit!'))
            if record.critical_high and record.abnormal_high:
                if record.critical_high <= record.abnormal_high:
                    raise ValidationError(_('Critical high limit must be greater than abnormal high limit!'))

    # ===================== CRUD OVERRIDES =====================

    @api.model
    def create(self, vals):
        """Override create to ensure code format"""
        if vals.get('code'):
            vals['code'] = vals['code'].upper().strip()

        test_type = super(LimsTestType, self).create(vals)

        test_type.message_post(
            body=_('Test type created: %s (%s)') % (test_type.name, test_type.code),
            message_type='notification'
        )

        return test_type

    def write(self, vals):
        """Override write to track changes"""
        if vals.get('code'):
            vals['code'] = vals['code'].upper().strip()

        result = super(LimsTestType, self).write(vals)

        if result and vals.get('active', True) is False:
            for record in self:
                record.message_post(body=_('Test type deactivated'))

        return result

    # ===================== ACTION METHODS =====================

    def action_activate(self):
        """Activate the test type"""
        self.active = True
        self.message_post(body=_('Test type activated'))

    def action_deactivate(self):
        """Deactivate the test type"""
        self.active = False
        self.message_post(body=_('Test type deactivated'))

    def action_view_orders(self):
        """View all orders for this test type"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Orders for %s') % self.name,
            'res_model': 'lims.test_order_line',
            'view_mode': 'tree,form',
            'domain': [('test_type_id', '=', self.id)],
            'context': {'default_test_type_id': self.id},
        }

    def action_view_qc_records(self):
        """View QC records for this test type"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('QC Records for %s') % self.name,
            'res_model': 'lims.quality_control',
            'view_mode': 'tree,form',
            'domain': [('test_type_id', '=', self.id)],
            'context': {'default_test_type_id': self.id},
        }

    def action_create_template(self):
        """Create a result template for this test type"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Create Result Template'),
            'res_model': 'lims.result_template',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_test_type_id': self.id,
                'default_name': f"{self.name} Template",
                'default_unit': self.unit,
                'default_normal_range': self.normal_range,
                'default_abnormal_low': self.abnormal_low,
                'default_abnormal_high': self.abnormal_high,
            },
        }

    def action_export_csv(self):
        """Export test type data as CSV"""
        self.ensure_one()
        # This would generate a CSV export
        return {
            'type': 'ir.actions.act_url',
            'url': f'/lims/test_type/export/{self.id}',
            'target': 'new',
        }

    # ===================== UTILITY METHODS =====================

    def get_sample_requirements(self):
        """Get sample requirements as a dictionary"""
        self.ensure_one()
        return {
            'sample_type': dict(self._fields['required_sample_type'].selection).get(self.required_sample_type),
            'volume': self.sample_volume,
            'container': self.sample_container,
            'stability': self.sample_stability,
            'preparation': self.special_preparation,
            'handling': self.special_handling,
        }

    def get_reference_ranges(self):
        """Get reference ranges as a dictionary"""
        self.ensure_one()
        return {
            'normal_range': self.normal_range,
            'abnormal_low': self.abnormal_low,
            'abnormal_high': self.abnormal_high,
            'critical_low': self.critical_low,
            'critical_high': self.critical_high,
            'unit': self.unit,
        }

    def get_qc_requirements(self):
        """Get QC requirements as a dictionary"""
        self.ensure_one()
        return {
            'requires_qc': self.requires_qc,
            'frequency': dict(self._fields['qc_frequency'].selection).get(self.qc_frequency),
            'target': self.qc_target,
            'tolerance': self.qc_tolerance,
        }

    def get_statistics_summary(self):
        """Get statistics summary for this test type"""
        self.ensure_one()
        return {
            'total_orders': self.total_orders,
            'total_revenue': self.total_revenue,
            'average_price': self.average_price,
            'abnormal_rate': self.abnormal_rate,
            'qc_pass_rate': self.qc_pass_rate,
            'margin': self.margin,
            'margin_percentage': self.margin_percentage,
        }

    def validate_result(self, value):
        """
        Validate a result value against this test type's ranges
        Returns: dict with validation result
        """
        self.ensure_one()
        result = {
            'value': value,
            'valid': True,
            'is_abnormal': False,
            'is_critical': False,
            'status': 'normal',
        }

        if value is None:
            result['valid'] = False
            result['status'] = 'no_value'
            return result

        # Check normal range
        if self.abnormal_low and value < self.abnormal_low:
            result['is_abnormal'] = True
            if self.critical_low and value < self.critical_low:
                result['is_critical'] = True
                result['status'] = 'critical_low'
            else:
                result['status'] = 'abnormal_low'
        elif self.abnormal_high and value > self.abnormal_high:
            result['is_abnormal'] = True
            if self.critical_high and value > self.critical_high:
                result['is_critical'] = True
                result['status'] = 'critical_high'
            else:
                result['status'] = 'abnormal_high'
        else:
            result['status'] = 'normal'

        return result

    # ===================== STATISTICAL METHODS =====================

    @api.model
    def get_category_stats(self):
        """Get statistics by category"""
        categories = dict(self._fields['category'].selection)
        stats = {}

        for cat_code, cat_name in categories.items():
            tests = self.search([('category', '=', cat_code), ('active', '=', True)])
            stats[cat_name] = {
                'total_tests': len(tests),
                'total_revenue': sum(tests.mapped('total_revenue')),
                'avg_price': sum(tests.mapped('price')) / len(tests) if tests else 0,
                'total_orders': sum(tests.mapped('total_orders')),
            }

        return stats

    @api.model
    def get_popular_tests(self, limit=10):
        """Get most popular tests"""
        tests = self.search([('active', '=', True)])
        sorted_tests = sorted(tests, key=lambda t: t.total_orders, reverse=True)
        result = []

        for test in sorted_tests[:limit]:
            result.append({
                'id': test.id,
                'name': test.name,
                'code': test.code,
                'total_orders': test.total_orders,
                'total_revenue': test.total_revenue,
            })

        return result
