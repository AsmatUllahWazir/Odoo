# -*- coding: utf-8 -*-
"""
Property Viewing Model - Appointment management for property viewings
"""

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta


class PropertyViewing(models.Model):
    """
    Property Viewing - Schedule and track property viewings
    """
    _name = 'property.viewing'
    _description = 'Property Viewing'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'scheduled_time desc'
    _rec_name = 'display_name'

    # ==========================================================================
    # Basic Information
    # ==========================================================================

    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True
    )

    property_id = fields.Many2one(
        'property.property',
        string='Property',
        required=True,
        tracking=True,
        ondelete='cascade'
    )

    unit_id = fields.Many2one(
        'property.unit',
        string='Unit',
        help='Specific unit to view'
    )

    prospect_id = fields.Many2one(
        'res.partner',
        string='Prospect',
        required=True,
        tracking=True,
        help='Person viewing the property'
    )

    sales_person_id = fields.Many2one(
        'res.users',
        string='Sales Person',
        default=lambda self: self.env.user,
        tracking=True
    )

    # ==========================================================================
    # Scheduling
    # ==========================================================================

    scheduled_time = fields.Datetime(
        string='Scheduled Time',
        required=True,
        tracking=True,
        help='Date and time of viewing'
    )

    duration = fields.Integer(
        string='Duration (Minutes)',
        default=30,
        help='Expected duration of viewing'
    )

    end_time = fields.Datetime(
        string='End Time',
        compute='_compute_end_time',
        store=True,
        help='Expected end time of viewing'
    )

    status = fields.Selection([
        ('scheduled', 'Scheduled'),
        ('confirmed', 'Confirmed'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('no_show', 'No Show'),
    ], string='Status', required=True, default='scheduled', tracking=True)

    # ==========================================================================
    # Outcome
    # ==========================================================================

    outcome = fields.Selection([
        ('interested', 'Interested'),
        ('not_interested', 'Not Interested'),
        ('undecided', 'Undecided'),
        ('will_apply', 'Will Apply'),
        ('will_lease', 'Will Lease'),
        ('will_purchase', 'Will Purchase'),
    ], string='Outcome', tracking=True)

    feedback = fields.Text(
        string='Feedback',
        help='Notes about the viewing'
    )

    rating = fields.Selection([
        ('1', '1 - Poor'),
        ('2', '2 - Fair'),
        ('3', '3 - Good'),
        ('4', '4 - Very Good'),
        ('5', '5 - Excellent'),
    ], string='Rating', help='Prospect rating of property')

    # ==========================================================================
    # Related Leases
    # ==========================================================================

    lease_id = fields.Many2one(
        'property.lease',
        string='Generated Lease',
        help='Lease created from this viewing'
    )

    screening_id = fields.Many2one(
        'property.tenant.screening',
        string='Screening',
        help='Tenant screening created from this viewing'
    )

    # ==========================================================================
    # Computed Fields
    # ==========================================================================

    @api.depends('property_id', 'prospect_id', 'scheduled_time')
    def _compute_display_name(self):
        """Compute display name"""
        for record in self:
            property_name = record.property_id.name if record.property_id else ''
            prospect_name = record.prospect_id.name if record.prospect_id else ''
            time_str = record.scheduled_time.strftime('%Y-%m-%d %H:%M') if record.scheduled_time else ''
            record.display_name = f"{property_name} - {prospect_name} ({time_str})"

    @api.depends('scheduled_time', 'duration')
    def _compute_end_time(self):
        """Compute end time from scheduled time and duration"""
        for record in record:
            if record.scheduled_time and record.duration:
                record.end_time = record.scheduled_time + timedelta(minutes=record.duration)
            else:
                record.end_time = False

    # ==========================================================================
    # Constraints
    # ==========================================================================

    _sql_constraints = [
        ('check_duration_positive', 'CHECK(duration > 0)',
         'Duration must be greater than 0'),
        ('check_scheduled_time_future', 'CHECK(scheduled_time >= NOW())',
         'Scheduled time cannot be in the past'),
    ]

    @api.constrains('scheduled_time')
    def _check_scheduled_time(self):
        """Validate scheduled time is in the future"""
        for record in self:
            if record.scheduled_time and record.scheduled_time < datetime.now() - timedelta(hours=1):
                raise ValidationError(
                    _("Scheduled time cannot be more than 1 hour in the past.")
                )

    @api.constrains('property_id', 'scheduled_time')
    def _check_overlapping_viewings(self):
        """Prevent overlapping viewings for same property"""
        for record in self:
            if record.status in ['cancelled', 'no_show']:
                continue

            domain = [
                ('id', '!=', record.id),
                ('property_id', '=', record.property_id.id),
                ('status', 'in', ['scheduled', 'confirmed', 'in_progress']),
                ('scheduled_time', '>=', record.scheduled_time - timedelta(hours=1)),
                ('scheduled_time', '<=', record.scheduled_time + timedelta(hours=1)),
            ]

            overlapping = self.search(domain)
            if overlapping:
                raise ValidationError(
                    _("There is already a viewing scheduled for this property "
                      "within 1 hour of the specified time.")
                )

    # ==========================================================================
    # Business Methods
    # ==========================================================================

    def action_confirm(self):
        """Confirm the viewing"""
        for record in self:
            if record.status != 'scheduled':
                raise ValidationError(_("Only scheduled viewings can be confirmed."))
            record.status = 'confirmed'
            record.message_post(
                body=_("Viewing confirmed."),
                message_type='notification'
            )

    def action_start(self):
        """Mark viewing as in progress"""
        for record in self:
            if record.status not in ['confirmed', 'scheduled']:
                raise ValidationError(_("Only confirmed or scheduled viewings can be started."))
            record.status = 'in_progress'
            record.message_post(
                body=_("Viewing started."),
                message_type='notification'
            )

    def action_complete(self):
        """Complete the viewing"""
        for record in self:
            if record.status != 'in_progress':
                raise ValidationError(_("Only in-progress viewings can be completed."))
            record.status = 'completed'
            record.message_post(
                body=_("Viewing completed."),
                message_type='notification'
            )

    def action_cancel(self):
        """Cancel the viewing"""
        for record in self:
            if record.status in ['completed', 'cancelled']:
                raise ValidationError(_("This viewing cannot be cancelled."))
            record.status = 'cancelled'
            record.message_post(
                body=_("Viewing cancelled."),
                message_type='notification'
            )

    def action_launch_screening(self):
        """Launch tenant screening wizard"""
        self.ensure_one()
        if self.status != 'completed':
            raise ValidationError(_("Viewing must be completed before screening."))

        return {
            'type': 'ir.actions.act_window',
            'name': _('Tenant Screening'),
            'res_model': 'property.tenant.screening',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_viewing_id': self.id,
                'default_property_id': self.property_id.id,
                'default_applicant_id': self.prospect_id.id,
                'default_sales_person_id': self.sales_person_id.id,
            }
        }

    def action_create_lease(self):
        """Create a lease from this viewing"""
        self.ensure_one()
        if self.outcome not in ['interested', 'will_apply', 'will_lease', 'will_purchase']:
            raise ValidationError(_("Outcome must be positive to create a lease."))

        # Create lease
        lease_vals = {
            'property_id': self.property_id.id,
            'tenant_id': self.prospect_id.id,
            'start_date': fields.Date.today() + timedelta(days=30),
            'end_date': fields.Date.today() + timedelta(days=30 * 12),
            'rent_amount': self.property_id.rental_price,
            'deposit_amount': self.property_id.rental_deposit,
            'term_months': 12,
        }

        lease = self.env['property.lease'].create(lease_vals)
        self.lease_id = lease.id

        return {
            'type': 'ir.actions.act_window',
            'name': _('Lease Created'),
            'res_model': 'property.lease',
            'res_id': lease.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _get_property_manager(self):
        """Get property manager for notifications"""
        if self.property_id.manager_id:
            return self.property_id.manager_id
        return self.env.user
    