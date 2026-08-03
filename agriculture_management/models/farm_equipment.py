# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class FarmEquipment(models.Model):
    _name = 'farm.equipment'
    _description = 'Farm Equipment'
    _inherit = ['mail.thread']
    _order = 'name'

    name = fields.Char(string='Equipment Name', required=True, tracking=True)
    code = fields.Char(string='Asset Code', readonly=True, copy=False, default='New')
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', string='Company', required=True,
                                  default=lambda self: self.env.company)

    # Classification
    equipment_type = fields.Selection([
        ('tractor', 'Tractor'),
        ('harvester', 'Harvester/Combine'),
        ('planter', 'Planter/Seeder'),
        ('sprayer', 'Sprayer'),
        ('irrigation', 'Irrigation System'),
        ('tillage', 'Tillage/Plough'),
        ('transport', 'Transport Vehicle'),
        ('processing', 'Processing Equipment'),
        ('storage', 'Storage/Silo'),
        ('other', 'Other'),
    ], string='Equipment Type', required=True, tracking=True)

    # Details
    brand = fields.Char(string='Brand/Manufacturer')
    model = fields.Char(string='Model')
    serial_number = fields.Char(string='Serial Number')
    year_manufactured = fields.Integer(string='Year Manufactured')
    purchase_date = fields.Date(string='Purchase Date')
    purchase_price = fields.Float(string='Purchase Price')
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', store=True)

    # Linked Maintenance Equipment
    maintenance_equipment_id = fields.Many2one('maintenance.equipment', string='Linked Maintenance Record',
                                                help='Links to Odoo Maintenance module')

    # Usage
    current_hours = fields.Float(string='Current Operating Hours')
    fuel_type = fields.Selection([
        ('diesel', 'Diesel'),
        ('gasoline', 'Gasoline/Petrol'),
        ('electric', 'Electric'),
        ('hybrid', 'Hybrid'),
        ('other', 'Other'),
    ], string='Fuel Type')
    fuel_capacity = fields.Float(string='Fuel Capacity (L)')

    # Status
    state = fields.Selection([
        ('available', 'Available'),
        ('in_use', 'In Use'),
        ('maintenance', 'Under Maintenance'),
        ('broken', 'Broken/Out of Service'),
        ('retired', 'Retired'),
    ], string='Status', default='available', tracking=True)

    # Location
    current_field_id = fields.Many2one('farm.field', string='Current Field')

    # Financial
    depreciation_method = fields.Selection([
        ('straight', 'Straight Line'),
        ('declining', 'Declining Balance'),
    ], string='Depreciation Method')
    useful_life_years = fields.Integer(string='Useful Life (years)')
    residual_value = fields.Float(string='Residual Value')
    book_value = fields.Float(string='Current Book Value', compute='_compute_book_value', store=True)

    # Documents
    attachment_ids = fields.Many2many('ir.attachment', string='Documents/Manuals')
    notes = fields.Html(string='Notes')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('code', 'New') == 'New':
                vals['code'] = self.env['ir.sequence'].next_by_code('farm.equipment') or 'New'
        return super(FarmEquipment, self).create(vals_list)

    @api.depends('purchase_price', 'purchase_date', 'useful_life_years', 'residual_value')
    def _compute_book_value(self):
        for equip in self:
            if equip.purchase_price and equip.useful_life_years and equip.purchase_date:
                years_elapsed = (fields.Date.today() - equip.purchase_date).days / 365.25
                if years_elapsed >= equip.useful_life_years:
                    equip.book_value = equip.residual_value or 0
                else:
                    depreciable = equip.purchase_price - (equip.residual_value or 0)
                    annual_depreciation = depreciable / equip.useful_life_years
                    equip.book_value = max(equip.purchase_price - (annual_depreciation * years_elapsed), 
                                            equip.residual_value or 0)
            else:
                equip.book_value = equip.purchase_price or 0

    def action_create_maintenance_request(self):
        self.ensure_one()
        if not self.maintenance_equipment_id:
            maintenance_equip = self.env['maintenance.equipment'].create({
                'name': self.name,
                'category_id': self.env.ref('maintenance.equipment_category_1').id,
                'model': self.model,
                'serial_no': self.serial_number,
                'purchase_date': self.purchase_date,
            })
            self.maintenance_equipment_id = maintenance_equip.id

        return {
            'type': 'ir.actions.act_window',
            'name': _('Maintenance Request'),
            'res_model': 'maintenance.request',
            'view_mode': 'form',
            'context': {
                'default_equipment_id': self.maintenance_equipment_id.id,
                'default_name': _('Scheduled maintenance for %s') % self.name,
            },
        }
