# -*- coding: utf-8 -*-
"""
Result Template Module for LIMS
Manages standard result interpretations, reference ranges, and validation rules
"""
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class LimsResultTemplate(models.Model):
    """
    Comprehensive Result Template Model
    Manages standard interpretations, reference ranges, and validation for test results
    """
    _name = 'lims.result_template'
    _description = 'LIMS Result Template'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'name'

    # ===================== BASIC IDENTIFICATION =====================
    name = fields.Char(
        string='Template Name',
        required=True,
        tracking=True,
        help='Name of the result template'
    )

    code = fields.Char(
        string='Template Code',
        required=True,
        tracking=True,
        help='Unique code for the template'
    )

    test_type_id = fields.Many2one(
        'lims.test_type',
        string='Test Type',
        required=True,
        help='Test type this template applies to'
    )

    version = fields.Char(
        string='Version',
        default='1.0',
        help='Template version number'
    )

    # ===================== REFERENCE RANGES =====================
    normal_range = fields.Text(
        string='Normal Range',
        required=True,
        help='Normal reference range for the test'
    )

    normal_range_min = fields.Float(
        string='Normal Range Minimum',
        help='Lower limit of normal range'
    )

    normal_range_max = fields.Float(
        string='Normal Range Maximum',
        help='Upper limit of normal range'
    )

    abnormal_low = fields.Float(
        string='Abnormal Low Limit',
        help='Value below this is considered abnormally low'
    )

    abnormal_high = fields.Float(
        string='Abnormal High Limit',
        help='Value above this is considered abnormally high'
    )

    critical_low = fields.Float(
        string='Critical Low Limit',
        help='Critical low value requiring immediate attention'
    )

    critical_high = fields.Float(
        string='Critical High Limit',
        help='Critical high value requiring immediate attention'
    )

    # ===================== INTERPRETATION =====================
    normal_interpretation = fields.Html(
        string='Normal Interpretation',
        help='Interpretation for normal results'
    )

    abnormal_interpretation = fields.Html(
        string='Abnormal Interpretation',
        help='Interpretation for abnormal results'
    )

    critical_interpretation = fields.Html(
        string='Critical Interpretation',
        help='Interpretation for critical results'
    )

    default_interpretation = fields.Html(
        string='Default Interpretation',
        help='Default interpretation for all results'
    )

    # ===================== CLINICAL GUIDANCE =====================
    clinical_significance = fields.Html(
        string='Clinical Significance',
        help='Clinical significance of the test'
    )

    follow_up_advice = fields.Html(
        string='Follow-up Advice',
        help='Recommended follow-up actions'
    )

    limitations = fields.Html(
        string='Test Limitations',
        help='Limitations of the test'
    )

    # ===================== VALIDATION RULES =====================
    validate_age = fields.Boolean(
        string='Validate Age',
        default=False,
        help='Apply age-specific validation'
    )

    validate_gender = fields.Boolean(
        string='Validate Gender',
        default=False,
        help='Apply gender-specific validation'
    )

    validate_medications = fields.Boolean(
        string='Validate Medications',
        default=False,
        help='Validate against current medications'
    )

    # ===================== AGE-SPECIFIC RANGES =====================
    age_range_min = fields.Integer(
        string='Age Range Minimum',
        help='Minimum age for this template (in years)'
    )

    age_range_max = fields.Integer(
        string='Age Range Maximum',
        help='Maximum age for this template (in years)'
    )

    age_specific_ranges = fields.One2many(
        'lims.age_specific_range',
        'template_id',
        string='Age-Specific Ranges',
        help='Age-specific reference ranges'
    )

    # ===================== GENDER-SPECIFIC RANGES =====================
    gender_specific_ranges = fields.One2many(
        'lims.gender_specific_range',
        'template_id',
        string='Gender-Specific Ranges',
        help='Gender-specific reference ranges'
    )

    # ===================== UNIT CONVERSIONS =====================
    unit = fields.Char(
        string='Unit',
        help='Unit of measurement for the test'
    )

    alternate_units = fields.Text(
        string='Alternate Units',
        help='Alternate units for conversion'
    )

    conversion_factor = fields.Float(
        string='Conversion Factor',
        help='Factor to convert between units'
    )

    # ===================== ACTIVE STATUS =====================
    active = fields.Boolean(
        string='Active',
        default=True,
        help='Active templates are available for use'
    )

    is_default = fields.Boolean(
        string='Is Default',
        default=False,
        help='Default template for this test type'
    )

    # ===================== NOTES =====================
    notes = fields.Text(
        string='Notes',
        help='Additional notes about the template'
    )

    references = fields.Text(
        string='References',
        help='References and sources for the reference ranges'
    )

    # ===================== COMPUTED FIELDS =====================
    test_type_name = fields.Char(
        related='test_type_id.name',
        store=True,
        readonly=True
    )

    test_type_code = fields.Char(
        related='test_type_id.code',
        store=True,
        readonly=True
    )

    range_display = fields.Char(
        compute='_compute_range_display',
        store=True,
        help='Formatted range display'
    )

    # ===================== COMPUTE METHODS =====================

    @api.depends('normal_range_min', 'normal_range_max', 'unit')
    def _compute_range_display(self):
        """Compute formatted range display"""
        for record in self:
            if record.normal_range_min and record.normal_range_max:
                record.range_display = f"{record.normal_range_min} - {record.normal_range_max} {record.unit or ''}"
            elif record.normal_range_min:
                record.range_display = f">= {record.normal_range_min} {record.unit or ''}"
            elif record.normal_range_max:
                record.range_display = f"<= {record.normal_range_max} {record.unit or ''}"
            else:
                record.range_display = record.normal_range or 'Not specified'

    # ===================== CONSTRAINTS =====================

    _sql_constraints = [
        ('unique_code', 'unique(code)', 'The template code must be unique!'),
        ('unique_name_test_type', 'unique(name, test_type_id)', 'Template name must be unique per test type!'),
    ]

    @api.constrains('normal_range_min', 'normal_range_max', 'abnormal_low', 'abnormal_high', 'critical_low',
                    'critical_high')
    def _check_ranges(self):
        """Validate reference ranges are logical"""
        for record in self:
            # Check normal range
            if record.normal_range_min and record.normal_range_max:
                if record.normal_range_min >= record.normal_range_max:
                    raise ValidationError(_('Normal range minimum must be less than maximum!'))

            # Check abnormal ranges
            if record.abnormal_low and record.abnormal_high:
                if record.abnormal_low >= record.abnormal_high:
                    raise ValidationError(_('Abnormal low limit must be less than abnormal high limit!'))

            # Check critical ranges
            if record.critical_low and record.critical_high:
                if record.critical_low >= record.critical_high:
                    raise ValidationError(_('Critical low limit must be less than critical high limit!'))

            # Check hierarchy: critical < abnormal < normal
            if record.abnormal_low and record.normal_range_min:
                if record.abnormal_low >= record.normal_range_min:
                    raise ValidationError(_('Abnormal low limit must be less than normal range minimum!'))

            if record.abnormal_high and record.normal_range_max:
                if record.abnormal_high <= record.normal_range_max:
                    raise ValidationError(_('Abnormal high limit must be greater than normal range maximum!'))

            if record.critical_low and record.abnormal_low:
                if record.critical_low >= record.abnormal_low:
                    raise ValidationError(_('Critical low limit must be less than abnormal low limit!'))

            if record.critical_high and record.abnormal_high:
                if record.critical_high <= record.abnormal_high:
                    raise ValidationError(_('Critical high limit must be greater than abnormal high limit!'))

    @api.constrains('age_range_min', 'age_range_max')
    def _check_age_ranges(self):
        """Validate age ranges"""
        for record in self:
            if record.age_range_min and record.age_range_max:
                if record.age_range_min >= record.age_range_max:
                    raise ValidationError(_('Age range minimum must be less than age range maximum!'))

    # ===================== CRUD OVERRIDES =====================

    @api.model
    def create(self, vals):
        """Override create to set default flag"""
        if not vals.get('code'):
            vals['code'] = self.env['ir.sequence'].next_by_code('lims.result.template') or 'RT-00001'

        # If setting as default, clear other defaults for this test type
        if vals.get('is_default'):
            self.search([('test_type_id', '=', vals.get('test_type_id')), ('is_default', '=', True)]).write(
                {'is_default': False})

        template = super(LimsResultTemplate, self).create(vals)

        template.message_post(
            body=_('Result template created: %s for test type: %s') % (template.name, template.test_type_name),
            message_type='notification'
        )

        return template

    def write(self, vals):
        """Override write to handle default flag"""
        if vals.get('is_default'):
            for record in self:
                self.search([('test_type_id', '=', record.test_type_id.id), ('id', '!=', record.id),
                             ('is_default', '=', True)]).write({'is_default': False})

        return super(LimsResultTemplate, self).write(vals)

    # ===================== VALIDATION METHODS =====================

    def validate_result(self, result_value, patient_age=None, patient_gender=None):
        """
        Validate a result against the template ranges
        Returns: dict with validation results
        """
        self.ensure_one()

        validation = {
            'valid': True,
            'is_abnormal': False,
            'is_critical': False,
            'message': '',
            'status': 'normal',
            'interpretation': '',
        }

        if result_value is None:
            validation['valid'] = False
            validation['message'] = 'No result value provided'
            return validation

        # Check normal range
        in_normal_range = True
        if self.normal_range_min and result_value < self.normal_range_min:
            in_normal_range = False
        if self.normal_range_max and result_value > self.normal_range_max:
            in_normal_range = False

        if in_normal_range:
            validation['status'] = 'normal'
            validation['interpretation'] = self.normal_interpretation or self.default_interpretation or 'Normal result'
        else:
            validation['is_abnormal'] = True

            # Check if critical
            if self.critical_low and result_value < self.critical_low:
                validation['is_critical'] = True
                validation['status'] = 'critical_low'
                validation[
                    'interpretation'] = self.critical_interpretation or 'Critical low value - immediate attention required!'
            elif self.critical_high and result_value > self.critical_high:
                validation['is_critical'] = True
                validation['status'] = 'critical_high'
                validation[
                    'interpretation'] = self.critical_interpretation or 'Critical high value - immediate attention required!'
            elif self.abnormal_low and result_value < self.abnormal_low:
                validation['status'] = 'abnormal_low'
                validation['interpretation'] = self.abnormal_interpretation or 'Abnormally low result'
            elif self.abnormal_high and result_value > self.abnormal_high:
                validation['status'] = 'abnormal_high'
                validation['interpretation'] = self.abnormal_interpretation or 'Abnormally high result'
            else:
                validation['status'] = 'borderline'
                validation['interpretation'] = 'Borderline result - requires clinical correlation'

        # Age-specific validation
        if self.validate_age and patient_age is not None:
            age_range = self.age_specific_ranges.filtered(
                lambda r: r.age_min <= patient_age <= r.age_max
            )
            if age_range:
                age_validation = age_range[0].validate_result(result_value)
                if age_validation['is_abnormal']:
                    validation['is_abnormal'] = True
                    validation['status'] = f"age_specific_{age_validation['status']}"
                    validation['interpretation'] = age_validation['interpretation']

        # Gender-specific validation
        if self.validate_gender and patient_gender:
            gender_range = self.gender_specific_ranges.filtered(
                lambda r: r.gender == patient_gender
            )
            if gender_range:
                gender_validation = gender_range[0].validate_result(result_value)
                if gender_validation['is_abnormal']:
                    validation['is_abnormal'] = True
                    validation['status'] = f"gender_specific_{gender_validation['status']}"
                    validation['interpretation'] = gender_validation['interpretation']

        if validation['is_abnormal']:
            validation['valid'] = False
            validation[
                'message'] = f"Result {result_value} is {'critical' if validation['is_critical'] else 'abnormal'}"
        else:
            validation['message'] = 'Result is within normal range'

        return validation

    def get_interpretation(self, result_value, patient_age=None, patient_gender=None):
        """
        Get interpretation for a result
        Returns: HTML-formatted interpretation
        """
        self.ensure_one()
        validation = self.validate_result(result_value, patient_age, patient_gender)
        return validation['interpretation']

    def get_status_for_value(self, result_value):
        """Get status for a specific value"""
        self.ensure_one()
        validation = self.validate_result(result_value)
        return {
            'status': validation['status'],
            'is_abnormal': validation['is_abnormal'],
            'is_critical': validation['is_critical'],
            'color': self._get_color_for_status(validation['status']),
        }

    def _get_color_for_status(self, status):
        """Get color code for status"""
        colors = {
            'normal': '#27ae60',
            'borderline': '#f39c12',
            'abnormal_low': '#e67e22',
            'abnormal_high': '#e67e22',
            'critical_low': '#e74c3c',
            'critical_high': '#e74c3c',
            'age_specific_abnormal_low': '#e67e22',
            'age_specific_abnormal_high': '#e67e22',
            'gender_specific_abnormal_low': '#e67e22',
            'gender_specific_abnormal_high': '#e67e22',
        }
        return colors.get(status, '#95a5a6')


class LimsAgeSpecificRange(models.Model):
    """
    Age-specific reference ranges for result templates
    """
    _name = 'lims.age_specific_range'
    _description = 'Age-Specific Reference Range'
    _order = 'age_min'

    template_id = fields.Many2one(
        'lims.result_template',
        string='Template',
        required=True,
        ondelete='cascade'
    )

    age_min = fields.Integer(
        string='Age Range Minimum',
        required=True,
        help='Minimum age in years'
    )

    age_max = fields.Integer(
        string='Age Range Maximum',
        required=True,
        help='Maximum age in years'
    )

    normal_range = fields.Text(
        string='Normal Range',
        required=True,
        help='Age-specific normal range'
    )

    normal_range_min = fields.Float(
        string='Normal Range Minimum',
        help='Lower limit of normal range for this age group'
    )

    normal_range_max = fields.Float(
        string='Normal Range Maximum',
        help='Upper limit of normal range for this age group'
    )

    interpretation = fields.Html(
        string='Age-Specific Interpretation',
        help='Interpretation for this age group'
    )

    @api.constrains('age_min', 'age_max')
    def _check_age_range(self):
        """Validate age range"""
        for record in self:
            if record.age_min >= record.age_max:
                raise ValidationError(_('Age range minimum must be less than age range maximum!'))

    def validate_result(self, result_value):
        """Validate result against age-specific range"""
        self.ensure_one()
        validation = {
            'is_abnormal': False,
            'status': 'normal',
            'interpretation': '',
        }

        if self.normal_range_min is not None and result_value < self.normal_range_min:
            validation['is_abnormal'] = True
            validation['status'] = 'abnormal_low'
            validation['interpretation'] = self.interpretation or f'Result {result_value} is below age-specific range'
        elif self.normal_range_max is not None and result_value > self.normal_range_max:
            validation['is_abnormal'] = True
            validation['status'] = 'abnormal_high'
            validation['interpretation'] = self.interpretation or f'Result {result_value} is above age-specific range'
        else:
            validation['interpretation'] = self.interpretation or 'Within age-specific normal range'

        return validation


class LimsGenderSpecificRange(models.Model):
    """
    Gender-specific reference ranges for result templates
    """
    _name = 'lims.gender_specific_range'
    _description = 'Gender-Specific Reference Range'

    template_id = fields.Many2one(
        'lims.result_template',
        string='Template',
        required=True,
        ondelete='cascade'
    )

    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
    ], string='Gender', required=True)

    normal_range = fields.Text(
        string='Normal Range',
        required=True,
        help='Gender-specific normal range'
    )

    normal_range_min = fields.Float(
        string='Normal Range Minimum',
        help='Lower limit of normal range for this gender'
    )

    normal_range_max = fields.Float(
        string='Normal Range Maximum',
        help='Upper limit of normal range for this gender'
    )

    interpretation = fields.Html(
        string='Gender-Specific Interpretation',
        help='Interpretation for this gender'
    )

    def validate_result(self, result_value):
        """Validate result against gender-specific range"""
        self.ensure_one()
        validation = {
            'is_abnormal': False,
            'status': 'normal',
            'interpretation': '',
        }

        if self.normal_range_min is not None and result_value < self.normal_range_min:
            validation['is_abnormal'] = True
            validation['status'] = 'abnormal_low'
            validation[
                'interpretation'] = self.interpretation or f'Result {result_value} is below gender-specific range'
        elif self.normal_range_max is not None and result_value > self.normal_range_max:
            validation['is_abnormal'] = True
            validation['status'] = 'abnormal_high'
            validation[
                'interpretation'] = self.interpretation or f'Result {result_value} is above gender-specific range'
        else:
            validation['interpretation'] = self.interpretation or 'Within gender-specific normal range'

        return validation
