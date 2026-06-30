# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_member = fields.Boolean(string='Is Member', default=False)
    membership_id = fields.Many2one('salon.membership', string='Membership Plan')
    membership_card_id = fields.Many2one('salon.membership.card', string='Membership Card')

    membership_start_date = fields.Date(string='Membership Start Date')
    membership_expiry_date = fields.Date(string='Membership Expiry Date')

    preferred_staff_id = fields.Many2one('hr.employee', string='Preferred Staff')
    preferred_service_ids = fields.Many2many('salon.service', string='Preferred Services')

    appointment_ids = fields.One2many('salon.appointment', 'customer_id', string='Appointments')
    order_ids = fields.One2many('salon.order', 'partner_id', string='Orders')

    total_visits = fields.Integer(string='Total Visits', compute='_compute_statistics')
    total_spent = fields.Monetary(string='Total Spent', compute='_compute_statistics')
    last_visit_date = fields.Datetime(string='Last Visit Date', compute='_compute_statistics')

    birthday = fields.Date(string='Birthday')
    allergies = fields.Text(string='Allergies/Notes')

    loyalty_points = fields.Integer(string='Loyalty Points', default=0)

    @api.depends('appointment_ids.state', 'order_ids.total_amount')
    def _compute_statistics(self):
        for partner in self:
            completed_appointments = partner.appointment_ids.filtered(
                lambda a: a.state == 'completed'
            )
            partner.total_visits = len(completed_appointments)

            completed_orders = partner.order_ids.filtered(
                lambda o: o.state == 'done'
            )
            partner.total_spent = sum(completed_orders.mapped('total_amount'))

            last_appointment = completed_appointments.sorted('appointment_date', reverse=True)
            partner.last_visit_date = last_appointment[0].appointment_date if last_appointment else False

    def action_view_appointments(self):
        """View customer appointments"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Appointments'),
            'res_model': 'salon.appointment',
            'domain': [('customer_id', '=', self.id)],
            'view_mode': 'tree,form',
            'context': {'default_customer_id': self.id}
        }

    def action_view_orders(self):
        """View customer orders"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Orders'),
            'res_model': 'salon.order',
            'domain': [('partner_id', '=', self.id)],
            'view_mode': 'tree,form',
            'context': {'default_partner_id': self.id}
        }
    