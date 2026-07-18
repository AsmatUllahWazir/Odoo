# -*- coding: utf-8 -*-
"""
Patient Management Module for LIMS
Handles complete patient demographics, medical history, and tracking
"""
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from datetime import date, datetime, timedelta
import re
import logging

_logger = logging.getLogger(__name__)


class LimsPatient(models.Model):
    """
    Comprehensive Patient Model for Laboratory Information Management System
    Tracks all patient demographics, medical history, and laboratory interactions
    """
    _name = 'lims.patient'
    _description = 'LIMS Patient'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'patient_id desc'

    # ===================== BASIC IDENTIFICATION =====================
    patient_id = fields.Char(
        string='Patient ID',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
        help='Unique identifier for the patient. Auto-generated using sequence.'
    )

    name = fields.Char(
        string='Full Name',
        required=True,
        tracking=True,
        help='Patient\'s full legal name'
    )

    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True,
        help='Formatted display name with patient ID'
    )

    # ===================== DEMOGRAPHIC INFORMATION =====================
    date_of_birth = fields.Date(
        string='Date of Birth',
        required=True,
        tracking=True,
        help='Patient\'s date of birth'
    )

    age = fields.Integer(
        string='Age',
        compute='_compute_age',
        store=True,
        help='Calculated age based on date of birth'
    )

    age_group = fields.Selection([
        ('infant', 'Infant (0-1)'),
        ('toddler', 'Toddler (1-3)'),
        ('child', 'Child (4-12)'),
        ('teen', 'Teen (13-19)'),
        ('adult', 'Adult (20-59)'),
        ('senior', 'Senior (60+)')
    ], string='Age Group', compute='_compute_age_group', store=True)

    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
        ('not_specified', 'Not Specified')
    ], string='Gender', required=True, default='not_specified')

    blood_type = fields.Selection([
        ('A+', 'A+'), ('A-', 'A-'),
        ('B+', 'B+'), ('B-', 'B-'),
        ('AB+', 'AB+'), ('AB-', 'AB-'),
        ('O+', 'O+'), ('O-', 'O-'),
    ], string='Blood Type', help='Patient\'s blood group for transfusion compatibility')

    rh_factor = fields.Selection([
        ('positive', 'Positive (+)'),
        ('negative', 'Negative (-)')
    ], string='Rh Factor', compute='_compute_rh_factor', store=True)

    # ===================== CONTACT INFORMATION =====================
    phone = fields.Char(
        string='Phone',
        help='Primary contact number'
    )

    mobile = fields.Char(
        string='Mobile',
        help='Mobile phone number for SMS notifications'
    )

    email = fields.Char(
        string='Email',
        help='Email address for electronic communication'
    )

    street = fields.Char(string='Street')
    street2 = fields.Char(string='Street2')
    city = fields.Char(string='City')
    state_id = fields.Many2one('res.country.state', string='State')
    country_id = fields.Many2one('res.country', string='Country', default=lambda self: self.env.ref('base.us'))
    zip = fields.Char(string='ZIP')

    # ===================== MEDICAL INFORMATION =====================
    allergies = fields.Text(
        string='Allergies',
        help='List of all known allergies (medication, food, environmental)'
    )

    medical_history = fields.Html(
        string='Medical History',
        help='Comprehensive medical history including past diagnoses, surgeries, chronic conditions'
    )

    current_medications = fields.Text(
        string='Current Medications',
        help='List of medications currently being taken'
    )

    chronic_conditions = fields.Text(
        string='Chronic Conditions',
        help='Long-term health conditions'
    )

    emergency_contact_name = fields.Char(string='Emergency Contact Name')
    emergency_contact_phone = fields.Char(string='Emergency Contact Phone')
    emergency_contact_relation = fields.Char(string='Emergency Contact Relation')

    # ===================== MEDICAL STAFF RELATIONS =====================
    responsible_doctor_id = fields.Many2one(
        'hr.employee',
        string='Responsible Doctor',
        help='Primary doctor responsible for this patient\'s care'
    )

    referring_doctor_id = fields.Many2one(
        'hr.employee',
        string='Referring Doctor',
        help='Doctor who referred this patient for laboratory tests'
    )

    primary_care_physician = fields.Many2one(
        'hr.employee',
        string='Primary Care Physician',
        help='Patient\'s regular doctor'
    )

    # ===================== INSURANCE INFORMATION =====================
    insurance_provider = fields.Char(string='Insurance Provider')
    insurance_policy_number = fields.Char(string='Policy Number')
    insurance_group_number = fields.Char(string='Group Number')
    insurance_effective_date = fields.Date(string='Insurance Effective Date')
    insurance_expiry_date = fields.Date(string='Insurance Expiry Date')
    is_insurance_valid = fields.Boolean(string='Insurance Valid', compute='_compute_insurance_valid', store=True)

    # ===================== STATUS AND TRACKING =====================
    active = fields.Boolean(
        string='Active',
        default=True,
        help='Inactive patients are archived and not visible in most views'
    )

    is_deceased = fields.Boolean(string='Deceased', default=False)
    date_of_death = fields.Date(string='Date of Death')

    registration_date = fields.Date(
        string='Registration Date',
        default=fields.Date.today,
        readonly=True,
        help='Date when patient was registered in the system'
    )

    last_visit_date = fields.Date(
        compute='_compute_statistics',
        store=True,
        help='Date of the most recent test order'
    )

    # ===================== RELATIONSHIPS =====================
    test_order_ids = fields.One2many(
        'lims.test_order',
        'patient_id',
        string='Test Orders',
        help='All test orders for this patient'
    )

    sample_ids = fields.One2many(
        'lims.sample',
        'patient_id',
        string='Samples',
        help='All samples collected from this patient'
    )

    report_ids = fields.One2many(
        'lims.report',
        'patient_id',
        string='Reports',
        help='All generated reports for this patient'
    )

    # ===================== STATISTICS AND COMPUTED FIELDS =====================
    total_orders = fields.Integer(
        compute='_compute_statistics',
        store=True,
        help='Total number of test orders'
    )

    total_samples = fields.Integer(
        compute='_compute_statistics',
        store=True,
        help='Total number of samples collected'
    )

    pending_orders = fields.Integer(
        compute='_compute_statistics',
        store=True,
        help='Number of pending test orders'
    )

    completed_orders = fields.Integer(
        compute='_compute_statistics',
        store=True,
        help='Number of completed test orders'
    )

    abnormal_results_count = fields.Integer(
        compute='_compute_statistics',
        store=True,
        help='Number of abnormal test results'
    )

    total_spent = fields.Monetary(
        compute='_compute_statistics',
        store=True,
        currency_field='currency_id',
        help='Total amount spent on laboratory tests'
    )

    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id.id
    )

    # ===================== COMPUTE METHODS =====================

    @api.depends('name', 'patient_id')
    def _compute_display_name(self):
        """Compute formatted display name"""
        for record in self:
            record.display_name = f"{record.patient_id} - {record.name}" if record.patient_id else record.name

    @api.depends('date_of_birth')
    def _compute_age(self):
        """Compute patient's age from date of birth"""
        for record in self:
            if record.date_of_birth:
                today = date.today()
                dob = record.date_of_birth
                age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
                record.age = age
            else:
                record.age = 0

    @api.depends('age')
    def _compute_age_group(self):
        """Determine age group based on age"""
        for record in self:
            if record.age <= 1:
                record.age_group = 'infant'
            elif record.age <= 3:
                record.age_group = 'toddler'
            elif record.age <= 12:
                record.age_group = 'child'
            elif record.age <= 19:
                record.age_group = 'teen'
            elif record.age <= 59:
                record.age_group = 'adult'
            else:
                record.age_group = 'senior'

    @api.depends('blood_type')
    def _compute_rh_factor(self):
        """Extract Rh factor from blood type"""
        for record in self:
            if record.blood_type:
                record.rh_factor = 'positive' if '+' in record.blood_type else 'negative'
            else:
                record.rh_factor = False

    @api.depends('insurance_expiry_date')
    def _compute_insurance_valid(self):
        """Check if insurance is still valid"""
        for record in self:
            if record.insurance_expiry_date:
                record.is_insurance_valid = record.insurance_expiry_date >= date.today()
            else:
                record.is_insurance_valid = False

    @api.depends('test_order_ids', 'sample_ids', 'test_order_ids.amount_total')
    def _compute_statistics(self):
        """Compute comprehensive patient statistics"""
        for record in self:
            orders = record.test_order_ids
            samples = record.sample_ids

            record.total_orders = len(orders)
            record.total_samples = len(samples)
            record.pending_orders = len(orders.filtered(lambda o: o.state not in ['reported', 'invoiced', 'cancelled']))
            record.completed_orders = len(orders.filtered(lambda o: o.state in ['reported', 'invoiced']))

            # Abnormal results
            abnormal = self.env['lims.test_order_line'].search([
                ('test_order_id', 'in', orders.ids),
                ('is_abnormal', '=', True)
            ])
            record.abnormal_results_count = len(abnormal)

            # Total spent
            record.total_spent = sum(orders.mapped('amount_total'))

            # Last visit
            if orders:
                record.last_visit_date = max(orders.mapped('date_ordered') or [False])

    # ===================== CONSTRAINTS AND VALIDATIONS =====================

    @api.constrains('date_of_birth')
    def _check_date_of_birth(self):
        """Validate date of birth"""
        for record in self:
            if record.date_of_birth and record.date_of_birth > date.today():
                raise ValidationError(_('Date of birth cannot be in the future!'))
            if record.date_of_birth and record.date_of_birth < date.today() - timedelta(days=365 * 120):
                raise ValidationError(_('Date of birth seems too old. Please verify.'))

    @api.constrains('email')
    def _check_email(self):
        """Validate email format"""
        for record in self:
            if record.email and not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', record.email):
                raise ValidationError(_('Invalid email format!'))

    @api.constrains('phone', 'mobile')
    def _check_phone_numbers(self):
        """Validate phone numbers"""
        for record in self:
            if record.phone and not re.match(r'^\+?[0-9\s\-()]{10,20}$', record.phone):
                raise ValidationError(_('Invalid phone number format!'))
            if record.mobile and not re.match(r'^\+?[0-9\s\-()]{10,20}$', record.mobile):
                raise ValidationError(_('Invalid mobile number format!'))

    @api.constrains('date_of_death')
    def _check_date_of_death(self):
        """Validate date of death"""
        for record in self:
            if record.date_of_death:
                if record.date_of_death > date.today():
                    raise ValidationError(_('Date of death cannot be in the future!'))
                if record.date_of_birth and record.date_of_death < record.date_of_birth:
                    raise ValidationError(_('Date of death cannot be before date of birth!'))

    @api.constrains('insurance_effective_date', 'insurance_expiry_date')
    def _check_insurance_dates(self):
        """Validate insurance dates"""
        for record in self:
            if record.insurance_effective_date and record.insurance_expiry_date:
                if record.insurance_expiry_date < record.insurance_effective_date:
                    raise ValidationError(_('Insurance expiry date cannot be before effective date!'))

    # ===================== OVERRIDES =====================

    @api.model
    def create(self, vals):
        """Override create to generate patient_id sequence"""
        if vals.get('patient_id', _('New')) == _('New'):
            vals['patient_id'] = self.env['ir.sequence'].next_by_code('lims.patient') or _('New')

        # Set registration date if not provided
        if not vals.get('registration_date'):
            vals['registration_date'] = fields.Date.today()

        patient = super(LimsPatient, self).create(vals)

        # Log creation
        patient.message_post(
            body=_('Patient created: %s') % patient.display_name,
            message_type='notification'
        )

        return patient

    def write(self, vals):
        """Override write to track changes"""
        if 'active' in vals and not vals.get('active'):
            for record in self:
                record.message_post(body=_('Patient archived'))
        return super(LimsPatient, self).write(vals)

    def name_get(self):
        """Override name_get to show patient_id and name together"""
        result = []
        for patient in self:
            display_name = f"{patient.patient_id} - {patient.name}"
            result.append((patient.id, display_name))
        return result

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        """Override name_search to search by patient_id or name"""
        args = args or []
        domain = []
        if name:
            domain = ['|', ('patient_id', operator, name), ('name', operator, name)]
        records = self.search(domain + args, limit=limit)
        return records.name_get()

    # ===================== ACTION METHODS =====================

    def action_view_orders(self):
        """Action to view all orders for this patient"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Test Orders - %s') % self.name,
            'res_model': 'lims.test_order',
            'view_mode': 'tree,form,kanban',
            'domain': [('patient_id', '=', self.id)],
            'context': {'default_patient_id': self.id},
        }

    def action_view_samples(self):
        """Action to view all samples for this patient"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Samples - %s') % self.name,
            'res_model': 'lims.sample',
            'view_mode': 'tree,form',
            'domain': [('patient_id', '=', self.id)],
            'context': {'default_patient_id': self.id},
        }

    def action_view_reports(self):
        """Action to view all reports for this patient"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Reports - %s') % self.name,
            'res_model': 'lims.report',
            'view_mode': 'tree,form',
            'domain': [('patient_id', '=', self.id)],
            'context': {'default_patient_id': self.id},
        }

    def action_create_new_order(self):
        """Action to create a new test order for this patient"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('New Test Order'),
            'res_model': 'lims.test_order',
            'view_mode': 'form',
            'context': {
                'default_patient_id': self.id,
                'default_doctor_id': self.responsible_doctor_id.id,
            },
        }

    def action_send_patient_email(self):
        """Action to send email to patient"""
        self.ensure_one()
        template = self.env.ref('hospital_lims.email_template_patient_reminder', raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=True)
            self.message_post(body=_('Email sent to patient: %s') % self.email)
        else:
            raise UserError(_('Email template not found!'))

    def action_generate_id_card(self):
        """Action to generate patient ID card"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': f'/lims/patient/id_card/{self.id}',
            'target': 'new',
        }

    def action_merge_patients(self):
        """Action to merge duplicate patient records"""
        # This would open a wizard for merging
        return {
            'type': 'ir.actions.act_window',
            'name': _('Merge Patients'),
            'res_model': 'lims.patient.merge.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'active_ids': self.ids},
        }

    def action_archive(self):
        """Archive patient"""
        self.active = False
        self.message_post(body=_('Patient archived'))

    def action_unarchive(self):
        """Unarchive patient"""
        self.active = True
        self.message_post(body=_('Patient unarchived'))

    # ===================== UTILITY METHODS =====================

    def get_full_address(self):
        """Get formatted full address"""
        self.ensure_one()
        parts = []
        if self.street:
            parts.append(self.street)
        if self.street2:
            parts.append(self.street2)
        if self.city:
            parts.append(self.city)
        if self.state_id:
            parts.append(self.state_id.name)
        if self.zip:
            parts.append(self.zip)
        return ', '.join(parts)

    def get_latest_test_order(self):
        """Get the most recent test order"""
        self.ensure_one()
        return self.test_order_ids.sorted('date_ordered', reverse=True)[:1]

    def get_pending_tests(self):
        """Get all pending tests for this patient"""
        self.ensure_one()
        return self.env['lims.test_order_line'].search([
            ('test_order_id', 'in', self.test_order_ids.ids),
            ('state', 'in', ['draft', 'assigned', 'in_progress'])
        ])

    def get_completed_tests(self):
        """Get all completed tests for this patient"""
        self.ensure_one()
        return self.env['lims.test_order_line'].search([
            ('test_order_id', 'in', self.test_order_ids.ids),
            ('state', 'in', ['completed', 'verified', 'reported'])
        ])


class LimsPatientMergeWizard(models.TransientModel):
    """
    Wizard for merging duplicate patient records
    """
    _name = 'lims.patient.merge.wizard'
    _description = 'Patient Merge Wizard'

    primary_patient_id = fields.Many2one(
        'lims.patient',
        string='Primary Patient',
        required=True,
        help='The patient record that will remain after merging'
    )

    secondary_patient_ids = fields.Many2many(
        'lims.patient',
        string='Patients to Merge',
        help='Patient records to merge into the primary'
    )

    merge_orders = fields.Boolean(string='Merge Test Orders', default=True)
    merge_samples = fields.Boolean(string='Merge Samples', default=True)
    merge_reports = fields.Boolean(string='Merge Reports', default=True)

    def action_merge(self):
        """Execute the merge operation"""
        self.ensure_one()
        primary = self.primary_patient_id
        secondary = self.secondary_patient_ids - primary

        if not secondary:
            raise UserError(_('No secondary patients selected for merging!'))

        # Merge test orders
        if self.merge_orders:
            orders = self.env['lims.test_order'].search([('patient_id', 'in', secondary.ids)])
            orders.write({'patient_id': primary.id})

        # Merge samples
        if self.merge_samples:
            samples = self.env['lims.sample'].search([('patient_id', 'in', secondary.ids)])
            samples.write({'patient_id': primary.id})

        # Merge reports
        if self.merge_reports:
            reports = self.env['lims.report'].search([('patient_id', 'in', secondary.ids)])
            reports.write({'patient_id': primary.id})

        # Archive secondary patients
        secondary.write({'active': False})

        primary.message_post(
            body=_('Merged patients: %s') % ', '.join(secondary.mapped('display_name'))
        )

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'lims.patient',
            'res_id': primary.id,
            'view_mode': 'form',
        }
    