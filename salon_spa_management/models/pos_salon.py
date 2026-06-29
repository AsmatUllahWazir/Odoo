# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.addons.point_of_sale.models.pos_order import PosOrder

class PosOrder(models.Model):
    _inherit = 'pos.order'

    salon_appointment_id = fields.Many2one('salon.appointment', string='Salon Appointment')
    salon_customer_checkin = fields.Boolean(string='Checked In', default=False)


class PosSession(models.Model):
    _inherit = 'pos.session'

    salon_current_appointments = fields.One2many('salon.appointment',
                                                 compute='_compute_salon_appointments')

    @api.depends('config_id', 'state')
    def _compute_salon_appointments(self):
        for session in self:
            session.salon_current_appointments = self.env['salon.appointment'].search([
                ('company_id', '=', session.company_id.id),
                ('state', 'in', ['confirmed', 'checked_in', 'in_progress']),
                ('appointment_date', '>=', fields.Datetime.now())
            ])


class PosConfig(models.Model):
    _inherit = 'pos.config'

    salon_enabled = fields.Boolean(string='Enable Salon Features', default=False)
    default_employee_id = fields.Many2one('hr.employee', string='Default Staff')
    show_chair_management = fields.Boolean(string='Show Chair Management', default=True)
