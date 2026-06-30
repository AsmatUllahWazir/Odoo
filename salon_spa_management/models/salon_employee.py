# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    service_ids = fields.Many2many('salon.service', string='Qualified Services')
    commission_rule_ids = fields.One2many('salon.commission.rule', 'employee_id',
                                          string='Commission Rules')

    max_appointments_per_day = fields.Integer(string='Max Appointments per Day', default=10)
    working_hours_start = fields.Float(string='Working Hours Start', default=9.0)
    working_hours_end = fields.Float(string='Working Hours End', default=18.0)
    break_duration = fields.Float(string='Break Duration (Minutes)', default=30)

    salon_skill_level = fields.Selection([
        ('junior', 'Junior'),
        ('senior', 'Senior'),
        ('expert', 'Expert'),
    ], string='Skill Level', default='junior')

    current_chair_id = fields.Many2one('salon.chair', string='Current Chair')

    def action_view_appointments(self):
        """View staff appointments"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Appointments'),
            'res_model': 'salon.appointment',
            'domain': [('employee_id', '=', self.id)],
            'view_mode': 'tree,form',
        }

    def action_view_commission(self):
        """View staff commission"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Commission'),
            'res_model': 'salon.employee.commission',
            'domain': [('employee_id', '=', self.id)],
            'view_mode': 'tree,form',
        }
    