# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class FarmHarvest(models.Model):
    _name = 'farm.harvest'
    _description = 'Harvest Record'
    _inherit = ['mail.thread']
    _order = 'harvest_date desc'

    name = fields.Char(string='Harvest Reference', readonly=True, copy=False, default='New')
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', string='Company', required=True,
                                  default=lambda self: self.env.company)

    # Relations
    season_id = fields.Many2one('farm.season', string='Season', required=True)
    cultivation_id = fields.Many2one('farm.cultivation', string='Cultivation', required=True,
                                      domain="[('season_id', '=', season_id)]")
    field_id = fields.Many2one('farm.field', string='Field', related='cultivation_id.field_id', store=True)
    crop_id = fields.Many2one('farm.crop', string='Crop', related='cultivation_id.crop_id', store=True)

    # Harvest Details
    harvest_date = fields.Date(string='Harvest Date', required=True, default=fields.Date.today, tracking=True)
    harvest_method = fields.Selection([
        ('manual', 'Manual'),
        ('mechanical', 'Mechanical'),
        ('semi_mechanical', 'Semi-Mechanical'),
        ('other', 'Other'),
    ], string='Harvest Method', tracking=True)

    # Quantity & Quality
    quantity = fields.Float(string='Quantity Harvested', required=True, tracking=True)
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure', 
                              default=lambda self: self.env.ref('uom.product_uom_kgm'))
    moisture_percent = fields.Float(string='Moisture Content %', digits=(4, 2))
    quality_grade = fields.Selection([
        ('premium', 'Premium / Grade A'),
        ('standard', 'Standard / Grade B'),
        ('economy', 'Economy / Grade C'),
        ('rejected', 'Rejected'),
    ], string='Quality Grade', tracking=True)

    # Lot & Inventory
    lot_id = fields.Many2one('stock.lot', string='Harvest Lot', 
                              help='Stock lot created for this harvest')
    product_id = fields.Many2one('product.product', string='Harvest Product',
                                  domain="[('type', 'in', ['product', 'consu'])]")
    warehouse_id = fields.Many2one('stock.warehouse', string='Storage Warehouse')
    location_id = fields.Many2one('stock.location', string='Storage Location',
                                   domain=[('usage', '=', 'internal')])

    # Financial
    unit_price = fields.Float(string='Sale Price per Unit', tracking=True)
    total_value = fields.Float(string='Total Value', compute='_compute_total_value', store=True)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', store=True)

    # Post-Harvest
    drying_date = fields.Date(string='Drying Date')
    storage_date = fields.Date(string='Storage Date')
    storage_condition = fields.Selection([
        ('ambient', 'Ambient'),
        ('refrigerated', 'Refrigerated'),
        ('controlled', 'Controlled Atmosphere'),
        ('silo', 'Silo'),
        ('barn', 'Barn'),
    ], string='Storage Condition')

    # Traceability
    traceability_code = fields.Char(string='Traceability Code', copy=False,
                                     help='Unique code for end-to-end traceability')

    # Stock Integration
    stock_move_id = fields.Many2one('stock.move', string='Stock Move', readonly=True, copy=False)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('farm.harvest') or 'New'
        return super(FarmHarvest, self).create(vals_list)

    @api.depends('quantity', 'unit_price')
    def _compute_total_value(self):
        for harvest in self:
            harvest.total_value = harvest.quantity * harvest.unit_price

    @api.constrains('quantity')
    def _check_quantity(self):
        for harvest in self:
            if harvest.quantity <= 0:
                raise ValidationError(_('Harvest quantity must be positive.'))

    def action_create_stock_move(self):
        """Create stock move to receive harvest into inventory."""
        self.ensure_one()
        if not self.location_id:
            raise ValidationError(_('Please select a storage location.'))
        if not self.product_id:
            raise ValidationError(_('Please select a harvest product.'))

        move_vals = {
            'product_id': self.product_id.id,
            'product_uom_qty': self.quantity,
            'product_uom': self.uom_id.id,
            'location_id': self.env.ref('stock.stock_location_suppliers').id,
            'location_dest_id': self.location_id.id,
            'name': _('Harvest: %s') % self.name,
            'origin': self.name,
        }
        move = self.env['stock.move'].create(move_vals)
        move._action_confirm()
        move._action_done()
        self.stock_move_id = move.id
        return True

    def action_generate_traceability_report(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Traceability Report'),
            'res_model': 'farm.harvest',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
            'views': [(self.env.ref('agriculture_management.view_farm_harvest_traceability_form').id, 'form')],
        }
