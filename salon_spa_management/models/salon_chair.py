# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class SalonChair(models.Model):
    _name = 'salon.chair'
    _description = 'Salon Chair/Station'
    _order = 'name'

    STATES = [
        ('available', 'Available'),
        ('occupied', 'Occupied'),
        ('maintenance', 'Under Maintenance'),
        ('reserved', 'Reserved'),
    ]

    name = fields.Char(string='Chair/Station Name', required=True)
    code = fields.Char(string='Code', required=True)

    location = fields.Char(string='Location')
    description = fields.Text(string='Description')

    state = fields.Selection(STATES, string='Status', default='available', tracking=True)

    current_appointment_id = fields.Many2one('salon.appointment', string='Current Appointment')

    employee_ids = fields.Many2many('hr.employee', string='Assigned Staff')

    daily_revenue = fields.Monetary(string='Today\'s Revenue', compute='_compute_daily_revenue')
    daily_orders = fields.Integer(string='Today\'s Orders', compute='_compute_daily_orders')

    active = fields.Boolean(string='Active', default=True)

    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  related='company_id.currency_id')

    @api.depends('current_appointment_id')
    def _compute_daily_revenue(self):
        today = fields.Date.today()
        for chair in self:
            orders = self.env['salon.order'].search([
                ('appointment_id.chair_id', '=', chair.id),
                ('order_date', '>=', today),
                ('state', '=', 'done')
            ])
            chair.daily_revenue = sum(orders.mapped('total_amount'))

    @api.depends('current_appointment_id')
    def _compute_daily_orders(self):
        today = fields.Date.today()
        for chair in self:
            orders = self.env['salon.order'].search_count([
                ('appointment_id.chair_id', '=', chair.id),
                ('order_date', '>=', today),
                ('state', '=', 'done')
            ])
            chair.daily_orders = orders

    @api.constrains('code')
    def _check_code(self):
        for chair in self:
            if self.search_count([('code', '=', chair.code), ('id', '!=', chair.id)]) > 0:
                raise ValidationError(_('Chair code must be unique.'))

    def action_occupy(self):
        """Mark chair as occupied"""
        for chair in self:
            chair.state = 'occupied'

    def action_available(self):
        """Mark chair as available"""
        for chair in self:
            chair.state = 'available'
            chair.current_appointment_id = False

    def action_maintenance(self):
        """Mark chair as under maintenance"""
        for chair in self:
            chair.state = 'maintenance'

    def get_occupancy_report(self, start_date, end_date):
        """Get chair occupancy report for date range"""
        self.ensure_one()
        # Implementation for occupancy report
        pass
    