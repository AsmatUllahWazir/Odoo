# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class SalonOrder(models.Model):
    _name = 'salon.order'
    _description = 'Salon Order'
    _order = 'order_date desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    STATES = [
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('in_progress', 'In Progress'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled'),
    ]

    name = fields.Char(string='Order Number', required=True, copy=False, default='/')

    partner_id = fields.Many2one('res.partner', string='Customer', required=True)
    employee_id = fields.Many2one('hr.employee', string='Staff')
    appointment_id = fields.Many2one('salon.appointment', string='Appointment')

    order_date = fields.Datetime(string='Order Date', default=fields.Datetime.now)

    order_line_ids = fields.One2many('salon.order.line', 'order_id', string='Order Lines')

    total_amount = fields.Float(string='Total', compute='_compute_total', store=True)
    total_discount = fields.Float(string='Total Discount', compute='_compute_total', store=True)
    total_commission = fields.Float(string='Total Commission', compute='_compute_commission')

    state = fields.Selection(STATES, string='Status', default='draft', tracking=True)

    payment_ids = fields.Many2many('account.payment', string='Payments')
    payment_status = fields.Selection([
        ('unpaid', 'Unpaid'),
        ('partial', 'Partial'),
        ('paid', 'Paid'),
    ], string='Payment Status', compute='_compute_payment_status', store=True)

    membership_id = fields.Many2one('salon.membership', string='Membership',
                                    related='partner_id.membership_id')
    is_member = fields.Boolean(string='Is Member', related='partner_id.is_member')

    notes = fields.Text(string='Notes')
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company)

    @api.depends('order_line_ids', 'order_line_ids.price_subtotal',
                 'order_line_ids.discount_amount')
    def _compute_total(self):
        for order in self:
            total = 0
            discount = 0
            for line in order.order_line_ids:
                total += line.price_subtotal
                discount += line.discount_amount
            order.total_amount = total
            order.total_discount = discount

    @api.depends('order_line_ids', 'order_line_ids.commission_amount')
    def _compute_commission(self):
        for order in self:
            order.total_commission = sum(line.commission_amount for line in order.order_line_ids)

    @api.depends('payment_ids', 'payment_ids.state', 'total_amount')
    def _compute_payment_status(self):
        for order in self:
            paid_amount = sum(p.amount for p in order.payment_ids if p.state == 'posted')
            if paid_amount == 0:
                order.payment_status = 'unpaid'
            elif paid_amount >= order.total_amount:
                order.payment_status = 'paid'
            else:
                order.payment_status = 'partial'

    @api.model
    def create(self, vals):
        if vals.get('name', '/') == '/':
            vals['name'] = self.env['ir.sequence'].next_by_code('salon.order') or '/'
        return super(SalonOrder, self).create(vals)

    def action_confirm(self):
        for record in self:
            record.state = 'confirmed'

    def action_start(self):
        for record in self:
            record.state = 'in_progress'

    def action_done(self):
        for record in self:
            record.state = 'done'

    def action_cancel(self):
        for record in self:
            record.state = 'cancelled'

    def action_create_invoice(self):
        """Create invoice from order"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Create Invoice'),
            'res_model': 'salon.invoice.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_order_id': self.id}
        }


class SalonOrderLine(models.Model):
    _name = 'salon.order.line'
    _description = 'Salon Order Line'

    order_id = fields.Many2one('salon.order', string='Order', required=True, ondelete='cascade')

    service_id = fields.Many2one('salon.service', string='Service', required=True)
    employee_id = fields.Many2one('hr.employee', string='Staff')

    quantity = fields.Float(string='Quantity', default=1.0)
    price_unit = fields.Monetary(string='Unit Price', required=True)

    discount = fields.Float(string='Discount %', default=0.0)
    discount_amount = fields.Monetary(string='Discount Amount', compute='_compute_amounts', store=True)

    price_subtotal = fields.Monetary(string='Subtotal', compute='_compute_amounts', store=True)
    commission_amount = fields.Monetary(string='Commission', compute='_compute_amounts', store=True)

    currency_id = fields.Many2one('res.currency', string='Currency',
                                  related='order_id.company_id.currency_id')

    is_member_price = fields.Boolean(string='Member Price Applied', default=False)

    @api.depends('price_unit', 'quantity', 'discount', 'service_id')
    def _compute_amounts(self):
        for line in self:
            # Calculate discount amount
            discount_amount = (line.price_unit * line.discount / 100) * line.quantity
            line.discount_amount = discount_amount

            # Calculate subtotal
            subtotal = (line.price_unit * line.quantity) - discount_amount
            line.price_subtotal = subtotal

            # Calculate commission
            if line.service_id and line.service_id.commission_percentage:
                commission = (subtotal * line.service_id.commission_percentage) / 100
                line.commission_amount = commission
            else:
                line.commission_amount = 0.0


class SalonInvoiceWizard(models.TransientModel):
    _name = 'salon.invoice.wizard'
    _description = 'Create Invoice Wizard'

    order_id = fields.Many2one('salon.order', string='Order', required=True)

    def action_create_invoice(self):
        """Create invoice from order"""
        order = self.order_id
        invoice_vals = {
            'partner_id': order.partner_id.id,
            'move_type': 'out_invoice',
            'invoice_date': fields.Date.today(),
            'invoice_line_ids': [],
            'ref': order.name,
        }

        for line in order.order_line_ids:
            invoice_line_vals = {
                'name': line.service_id.name,
                'quantity': line.quantity,
                'price_unit': line.price_unit,
                'discount': line.discount,
            }
            invoice_vals['invoice_line_ids'].append((0, 0, invoice_line_vals))

        invoice = self.env['account.move'].create(invoice_vals)

        return {
            'type': 'ir.actions.act_window',
            'name': _('Invoice'),
            'res_model': 'account.move',
            'res_id': invoice.id,
            'view_mode': 'form',
        }
    