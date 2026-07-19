# -*- coding: utf-8 -*-
"""
Property HOA/Condo Association Model - Manage HOA/condo associations
"""

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import datetime


class PropertyHOAAssociation(models.Model):
    """
    Property HOA/Condo Association - Manage community associations
    """
    _name = 'property.hoa.association'
    _description = 'Property HOA/Condo Association'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'
    _rec_name = 'display_name'

    # ==========================================================================
    # Basic Information
    # ==========================================================================

    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True
    )

    name = fields.Char(
        string='Association Name',
        required=True,
        tracking=True
    )

    association_type = fields.Selection([
        ('hoa', 'HOA (Homeowners Association)'),
        ('condo', 'Condo Association'),
        ('coop', 'Cooperative'),
        ('townhome', 'Townhome Association'),
    ], string='Association Type', required=True, default='hoa')

    active = fields.Boolean(
        string='Active',
        default=True,
        help='Whether this association is active'
    )

    # ==========================================================================
    # Address
    # ==========================================================================

    partner_id = fields.Many2one(
        'res.partner',
        string='Association Partner',
        help='Partner record for this association'
    )

    street = fields.Char(string='Street')
    city = fields.Char(string='City')
    state_id = fields.Many2one('res.country.state', string='State')
    country_id = fields.Many2one('res.country', string='Country')
    zip = fields.Char(string='ZIP')

    # ==========================================================================
    # Financial
    # ==========================================================================

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id
    )

    monthly_fee = fields.Monetary(
        string='Monthly Fee',
        currency_field='currency_id',
        help='Standard monthly association fee'
    )

    annual_budget = fields.Monetary(
        string='Annual Budget',
        currency_field='currency_id',
        help='Association annual budget'
    )

    reserve_fund = fields.Monetary(
        string='Reserve Fund',
        currency_field='currency_id',
        help='Association reserve fund balance'
    )

    # ==========================================================================
    # Relationships
    # ==========================================================================

    property_ids = fields.Many2many(
        'property.property',
        string='Properties',
        help='Properties in this association'
    )

    board_member_ids = fields.Many2many(
        'res.partner',
        string='Board Members',
        help='Association board members'
    )

    meeting_ids = fields.One2many(
        'property.hoa.meeting',
        'association_id',
        string='Meetings',
        help='Association meetings'
    )

    fee_ids = fields.One2many(
        'property.hoa.fee',
        'association_id',
        string='Fees',
        help='Association fees'
    )

    # ==========================================================================
    # Management
    # ==========================================================================

    management_company_id = fields.Many2one(
        'res.partner',
        string='Management Company',
        domain="[('is_company', '=', True)]",
        help='Property management company'
    )

    contact_person = fields.Char(
        string='Contact Person',
        help='Primary contact person'
    )

    phone = fields.Char(
        string='Phone',
        help='Association phone number'
    )

    email = fields.Char(
        string='Email',
        help='Association email address'
    )

    website = fields.Char(
        string='Website',
        help='Association website'
    )

    # ==========================================================================
    # Rules and Documents
    # ==========================================================================

    cc_rules = fields.Html(
        string='CC&R Rules',
        help='Covenants, Conditions & Restrictions'
    )

    bylaws = fields.Text(
        string='Bylaws',
        help='Association bylaws'
    )

    document_ids = fields.One2many(
        'ir.attachment',
        'res_id',
        domain=[('res_model', '=', 'property.hoa.association')],
        string='Documents',
        help='Association documents'
    )

    # ==========================================================================
    # Computed Fields
    # ==========================================================================

    @api.depends('name', 'association_type')
    def _compute_display_name(self):
        """Compute display name"""
        for record in self:
            type_label = dict(self._fields['association_type'].selection).get(record.association_type, '')
            record.display_name = f"{record.name} ({type_label})"

    property_count = fields.Integer(
        string='Property Count',
        compute='_compute_property_count',
        help='Number of properties in association'
    )

    board_member_count = fields.Integer(
        string='Board Member Count',
        compute='_compute_board_member_count',
        help='Number of board members'
    )

    @api.depends('property_ids')
    def _compute_property_count(self):
        """Compute number of properties"""
        for record in self:
            record.property_count = len(record.property_ids)

    @api.depends('board_member_ids')
    def _compute_board_member_count(self):
        """Compute number of board members"""
        for record in self:
            record.board_member_count = len(record.board_member_ids)

    # ==========================================================================
    # Constraints
    # ==========================================================================

    _sql_constraints = [
        ('name_unique', 'unique(name)',
         'Association name must be unique!'),
        ('check_monthly_fee_positive', 'CHECK(monthly_fee >= 0)',
         'Monthly fee cannot be negative'),
    ]

    @api.constrains('email')
    def _check_email(self):
        """Validate email format"""
        import re
        for record in self:
            if record.email and not re.match(r'^[^@]+@[^@]+\.[^@]+$', record.email):
                raise ValidationError(
                    _("Please enter a valid email address.")
                )

    # ==========================================================================
    # Business Methods
    # ==========================================================================

    def action_view_properties(self):
        """View all properties in association"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Properties'),
            'res_model': 'property.property',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.property_ids.ids)],
        }

    def action_view_board_members(self):
        """View board members"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Board Members'),
            'res_model': 'res.partner',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.board_member_ids.ids)],
        }

    def action_schedule_meeting(self):
        """Schedule an association meeting"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Schedule Meeting'),
            'res_model': 'property.hoa.meeting',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_association_id': self.id,
            }
        }


class PropertyHOAFee(models.Model):
    """
    Property HOA Fee - Individual fees for properties
    """
    _name = 'property.hoa.fee'
    _description = 'HOA Fee'
    _order = 'create_date desc'

    association_id = fields.Many2one(
        'property.hoa.association',
        string='Association',
        required=True,
        ondelete='cascade'
    )

    property_id = fields.Many2one(
        'property.property',
        string='Property',
        required=True,
        ondelete='cascade'
    )

    month = fields.Date(
        string='Month',
        required=True,
        help='Month for this fee'
    )

    amount = fields.Monetary(
        string='Amount',
        currency_field='currency_id',
        required=True,
        help='Fee amount for this month'
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        related='association_id.currency_id',
        store=True,
        readonly=True
    )

    paid = fields.Boolean(
        string='Paid',
        default=False,
        help='Whether this fee has been paid'
    )

    paid_date = fields.Date(
        string='Paid Date',
        help='Date fee was paid'
    )

    notes = fields.Text(
        string='Notes',
        help='Additional notes about this fee'
    )

    _sql_constraints = [
        ('association_property_month_unique',
         'unique(association_id, property_id, month)',
         'Fee already exists for this property and month!'),
        ('check_amount_positive', 'CHECK(amount >= 0)',
         'Amount cannot be negative'),
    ]


class PropertyHOAMeeting(models.Model):
    """
    Property HOA Meeting - Track association meetings
    """
    _name = 'property.hoa.meeting'
    _description = 'HOA/Condo Meeting'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'meeting_date desc'

    association_id = fields.Many2one(
        'property.hoa.association',
        string='Association',
        required=True,
        ondelete='cascade'
    )

    name = fields.Char(
        string='Meeting Title',
        required=True
    )

    meeting_type = fields.Selection([
        ('annual', 'Annual'),
        ('board', 'Board'),
        ('emergency', 'Emergency'),
        ('special', 'Special'),
        ('budget', 'Budget'),
    ], string='Meeting Type', required=True, default='board')

    meeting_date = fields.Datetime(
        string='Meeting Date',
        required=True
    )

    location = fields.Char(
        string='Location',
        help='Meeting location'
    )

    agenda = fields.Html(
        string='Agenda',
        help='Meeting agenda'
    )

    minutes = fields.Html(
        string='Minutes',
        help='Meeting minutes'
    )

    attended_ids = fields.Many2many(
        'res.partner',
        string='Attendees',
        help='Meeting attendees'
    )

    status = fields.Selection([
        ('scheduled', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='scheduled')

    minutes_attachment = fields.Binary(
        string='Minutes Document',
        attachment=True
    )

    minutes_filename = fields.Char(
        string='Minutes Filename'
    )

    @api.constrains('meeting_date')
    def _check_meeting_date(self):
        """Validate meeting date"""
        for record in self:
            if record.meeting_date and record.meeting_date < datetime.now():
                raise ValidationError(
                    _("Meeting date cannot be in the past.")
                )
