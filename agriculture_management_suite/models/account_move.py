# -*- coding: utf-8 -*-
from odoo import fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    farm_season_id = fields.Many2one('farm.season', string='Farm Season',
                                      help='Link invoice to a specific farming season for P&L tracking')
    farm_cultivation_id = fields.Many2one('farm.cultivation', string='Cultivation',
                                           help='Link to specific cultivation record')
