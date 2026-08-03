# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class FarmHarvestWizard(models.TransientModel):
    _name = 'farm.harvest.wizard'
    _description = 'Harvest Recording Wizard'

    cultivation_id = fields.Many2one('farm.cultivation', string='Cultivation', required=True)
    season_id = fields.Many2one('farm.season', string='Season', related='cultivation_id.season_id', store=True)
    field_id = fields.Many2one('farm.field', string='Field', related='cultivation_id.field_id', store=True)
    crop_id = fields.Many2one('farm.crop', string='Crop', related='cultivation_id.crop_id', store=True)

    harvest_date = fields.Date(string='Harvest Date', required=True, default=fields.Date.today)
    quantity = fields.Float(string='Quantity', required=True)
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure',
                              default=lambda self: self.env.ref('uom.product_uom_kgm'))
    quality_grade = fields.Selection([
        ('premium', 'Premium / Grade A'),
        ('standard', 'Standard / Grade B'),
        ('economy', 'Economy / Grade C'),
        ('rejected', 'Rejected'),
    ], string='Quality Grade', default='standard')
    moisture_percent = fields.Float(string='Moisture Content %', digits=(4, 2))
    unit_price = fields.Float(string='Sale Price per Unit')

    # Storage
    product_id = fields.Many2one('product.product', string='Harvest Product',
                                  domain="[('type', 'in', ['product', 'consu'])]")
    location_id = fields.Many2one('stock.location', string='Storage Location',
                                   domain=[('usage', '=', 'internal')])

    @api.constrains('quantity')
    def _check_quantity(self):
        for wiz in self:
            if wiz.quantity <= 0:
                raise ValidationError(_('Quantity must be positive.'))

    def action_confirm_harvest(self):
        self.ensure_one()
        harvest_vals = {
            'season_id': self.season_id.id,
            'cultivation_id': self.cultivation_id.id,
            'harvest_date': self.harvest_date,
            'quantity': self.quantity,
            'uom_id': self.uom_id.id,
            'quality_grade': self.quality_grade,
            'moisture_percent': self.moisture_percent,
            'unit_price': self.unit_price,
            'product_id': self.product_id.id if self.product_id else self.crop_id.product_tmpl_id.product_variant_id.id if self.crop_id.product_tmpl_id else False,
            'location_id': self.location_id.id,
        }
        harvest = self.env['farm.harvest'].create(harvest_vals)

        # Update cultivation state
        self.cultivation_id.write({'state': 'harvested', 'actual_harvest_date': self.harvest_date})

        # Auto-create stock move if configured
        if self.env['ir.config_parameter'].sudo().get_param('agriculture.auto_stock_moves'):
            if harvest.product_id and harvest.location_id:
                harvest.action_create_stock_move()

        return {
            'type': 'ir.actions.act_window',
            'name': _('Harvest Created'),
            'res_model': 'farm.harvest',
            'view_mode': 'form',
            'res_id': harvest.id,
            'target': 'current',
        }
