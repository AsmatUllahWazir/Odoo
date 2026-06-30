# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta
import pytz


class SalonAppointment(models.Model):
    _name = 'salon.appointment'
    _description = 'Salon Appointment'
    _order = 'appointment_date desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    STATES = [
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('checked_in', 'Checked In'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('no_show', 'No Show'),
    ]

    name = fields.Char(string='Appointment Number', required=True, copy=False, default='/')

    customer_id = fields.Many2one('res.partner', string='Customer', required=True,
                                  domain="[('customer_rank', '>', 0)]")
    customer_phone = fields.Char(string='Customer Phone', related='customer_id.phone')
    customer_email = fields.Char(string='Customer Email', related='customer_id.email')

    employee_id = fields.Many2one('hr.employee', string='Staff', required=True)
    service_ids = fields.Many2many('salon.service', string='Services', required=True)

    appointment_date = fields.Datetime(string='Appointment Date', required=True)
    end_datetime = fields.Datetime(string='End Time', compute='_compute_end_datetime', store=True)

    duration = fields.Float(string='Total Duration (Minutes)', compute='_compute_duration', store=True)

    chair_id = fields.Many2one('salon.chair', string='Chair/Station',
                               domain="[('company_id', '=', company_id)]")

    state = fields.Selection(STATES, string='Status', default='draft', tracking=True)

    notes = fields.Text(string='Notes')
    internal_notes = fields.Text(string='Internal Notes')

    is_member = fields.Boolean(string='Is Member', related='customer_id.is_member')
    membership_id = fields.Many2one('salon.membership', string='Membership',
                                    related='customer_id.membership_id')

    order_id = fields.Many2one('salon.order', string='Order', ondelete='set null')

    is_online_booking = fields.Boolean(string='Online Booking', default=False)

    reminder_sent = fields.Boolean(string='Reminder Sent', default=False)
    confirmation_sent = fields.Boolean(string='Confirmation Sent', default=False)

    cancellation_reason = fields.Text(string='Cancellation Reason')

    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)

    @api.depends('service_ids', 'service_ids.duration')
    def _compute_duration(self):
        for appointment in self:
            total_duration = sum(service.duration for service in appointment.service_ids)
            # Add buffer time between services
            buffer_time = sum(service.buffer_time for service in appointment.service_ids)
            appointment.duration = total_duration + (buffer_time if len(appointment.service_ids) > 1 else 0)

    @api.depends('appointment_date', 'duration')
    def _compute_end_datetime(self):
        for appointment in self:
            if appointment.appointment_date and appointment.duration:
                appointment.end_datetime = appointment.appointment_date + timedelta(minutes=appointment.duration)
            else:
                appointment.end_datetime = False

    @api.constrains('appointment_date')
    def _check_appointment_date(self):
        for appointment in self:
            if appointment.appointment_date and appointment.appointment_date < datetime.now():
                raise ValidationError(_('Appointment cannot be scheduled in the past.'))

    @api.constrains('employee_id', 'appointment_date', 'duration')
    def _check_employee_availability(self):
        for appointment in self:
            if appointment.employee_id and appointment.appointment_date:
                # Check for overlapping appointments
                domain = [
                    ('employee_id', '=', appointment.employee_id.id),
                    ('appointment_date', '<', appointment.end_datetime),
                    ('end_datetime', '>', appointment.appointment_date),
                    ('state', 'not in', ['cancelled', 'no_show']),
                    ('id', '!=', appointment.id)
                ]
                overlapping = self.search_count(domain)
                if overlapping > 0:
                    raise ValidationError(_('Staff member is already booked at this time.'))

    @api.model
    def create(self, vals):
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].next_by_code('salon.appointment') or '/'
        return super(SalonAppointment, self).create(vals)

    def action_confirm(self):
        """Confirm the appointment"""
        for record in self:
            if record.state != 'draft':
                continue
            record.state = 'confirmed'
            # Create order if not exists
            if not record.order_id:
                order_vals = self._prepare_order_vals()
                order = self.env['salon.order'].create(order_vals)
                record.order_id = order.id
            # Send confirmation
            self._send_confirmation_email()

    def action_check_in(self):
        """Check in customer"""
        for record in self:
            if record.state == 'confirmed':
                record.state = 'checked_in'
                # Update chair status if assigned
                if record.chair_id:
                    record.chair_id.write({
                        'state': 'occupied',
                        'current_appointment_id': record.id
                    })

    def action_start_service(self):
        """Start the service"""
        for record in self:
            if record.state == 'checked_in':
                record.state = 'in_progress'

    def action_complete(self):
        """Complete the service"""
        for record in self:
            if record.state == 'in_progress':
                record.state = 'completed'
                if record.chair_id:
                    record.chair_id.write({
                        'state': 'available',
                        'current_appointment_id': False
                    })
                # Update order status
                if record.order_id:
                    record.order_id.action_done()

    def action_cancel(self):
        """Cancel the appointment"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Cancel Appointment'),
            'res_model': 'salon.cancel.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_appointment_id': self.id}
        }

    def action_no_show(self):
        """Mark as no show"""
        for record in self:
            record.state = 'no_show'
            if record.chair_id:
                record.chair_id.write({
                    'state': 'available',
                    'current_appointment_id': False
                })

    def _prepare_order_vals(self):
        """Prepare values for order creation"""
        return {
            'partner_id': self.customer_id.id,
            'appointment_id': self.id,
            'employee_id': self.employee_id.id,
            'company_id': self.company_id.id,
        }

    def _send_confirmation_email(self):
        """Send appointment confirmation email"""
        template = self.env.ref('salon_spa_management.email_template_appointment_confirmation', False)
        if template:
            for record in self:
                template.send_mail(record.id, force_send=True)

    def _send_reminder_email(self):
        """Send appointment reminder email"""
        template = self.env.ref('salon_spa_management.email_template_appointment_reminder', False)
        if template:
            for record in self:
                template.send_mail(record.id, force_send=True)


class SalonCancelWizard(models.TransientModel):
    _name = 'salon.cancel.wizard'
    _description = 'Cancel Appointment Wizard'

    appointment_id = fields.Many2one('salon.appointment', string='Appointment', required=True)
    cancellation_reason = fields.Text(string='Reason', required=True)

    def action_confirm_cancel(self):
        """Confirm cancellation"""
        if self.appointment_id:
            self.appointment_id.write({
                'state': 'cancelled',
                'cancellation_reason': self.cancellation_reason
            })
            if self.appointment_id.chair_id:
                self.appointment_id.chair_id.write({
                    'state': 'available',
                    'current_appointment_id': False
                })
                