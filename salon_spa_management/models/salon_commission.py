# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class SalonCommissionRule(models.Model):
    _name = 'salon.commission.rule'
    _description = 'Commission Rule'
    _order = 'employee_id, min_amount'

    employee_id = fields.Many2one('hr.employee', string='Staff', required=True)

    method = fields.Selection([
        ('fixed', 'Fixed Percentage'),
        ('section', 'Section Based'),
    ], string='Commission Method', required=True, default='fixed')

    fixed_percentage = fields.Float(string='Fixed Commission %', default=0,
                                    help='Applied to all services')

    min_amount = fields.Monetary(string='Min Revenue', default=0.0)
    max_amount = fields.Monetary(string='Max Revenue')
    section_percentage = fields.Float(string='Section Commission %')

    currency_id = fields.Many2one('res.currency', string='Currency',
                                  default=lambda self: self.env.company.currency_id)
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)

    @api.constrains('fixed_percentage')
    def _check_fixed_percentage(self):
        for rule in self:
            if rule.fixed_percentage < 0 or rule.fixed_percentage > 100:
                raise ValidationError(_('Commission percentage must be between 0 and 100.'))


class SalonEmployeeCommission(models.Model):
    _name = 'salon.employee.commission'
    _description = 'Employee Commission'
    _order = 'date desc'

    employee_id = fields.Many2one('hr.employee', string='Staff', required=True)
    name = fields.Char(string='Commission Name')

    date = fields.Date(string='Commission Date', default=fields.Date.today, required=True)
    order_date = fields.Date(string='Order Date', default=fields.Date.today, required=True)
    total_amount = fields.Monetary(string='Total Commission', compute='_compute_amounts')

    order_ids = fields.Many2many('salon.order', string='Orders')

    total_revenue = fields.Monetary(string='Total Revenue', compute='_compute_amounts')
    total_commission = fields.Monetary(string='Total Commission', compute='_compute_amounts')

    currency_id = fields.Many2one('res.currency', string='Currency',
                                  default=lambda self: self.env.company.currency_id)
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)
    partner_id = fields.Many2one('res.partner', string='Partner',)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('paid', 'Paid'),
    ], string='Status', default='draft')

    @api.depends('order_ids', 'order_ids.total_amount', 'order_ids.total_commission')
    def _compute_amounts(self):
        for record in self:
            revenue = sum(record.order_ids.mapped('total_amount'))
            commission = sum(record.order_ids.mapped('total_commission'))
            record.total_revenue = revenue
            record.total_commission = commission

    def action_confirm(self):
        for record in self:
            record.state = 'confirmed'

    def action_pay(self):
        for record in self:
            record.state = 'paid'
            