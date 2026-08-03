# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class FarmDiseasePest(models.Model):
    _name = 'farm.disease.pest'
    _description = 'Disease and Pest Incident'
    _inherit = ['mail.thread']
    _order = 'detection_date desc'

    name = fields.Char(string='Incident Reference', readonly=True, copy=False, default='New')
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', string='Company', required=True,
                                  default=lambda self: self.env.company)

    # Classification
    incident_type = fields.Selection([
        ('disease', 'Disease'),
        ('pest', 'Pest/Insect'),
        ('weed', 'Weed Infestation'),
        ('weather', 'Weather Damage'),
        ('nutrient', 'Nutrient Deficiency'),
        ('other', 'Other'),
    ], string='Incident Type', required=True, tracking=True)

    severity = fields.Selection([
        ('low', 'Low / Localized'),
        ('moderate', 'Moderate'),
        ('high', 'High / Widespread'),
        ('critical', 'Critical / Total Loss Risk'),
    ], string='Severity', required=True, tracking=True)

    # Details
    detection_date = fields.Date(string='Detection Date', required=True, default=fields.Date.today, tracking=True)
    resolved_date = fields.Date(string='Resolution Date')
    common_name = fields.Char(string='Common Name', required=True, tracking=True,
                               help='e.g., Wheat Rust, Aphids, Root Rot')
    scientific_name = fields.Char(string='Scientific Name')
    symptoms = fields.Text(string='Symptoms Observed')
    affected_area_percent = fields.Float(string='Affected Area %', help='Percentage of field affected')

    # Relations
    season_id = fields.Many2one('farm.season', string='Season', required=True)
    cultivation_id = fields.Many2one('farm.cultivation', string='Cultivation',
                                      domain="[('season_id', '=', season_id)]")
    field_id = fields.Many2one('farm.field', string='Field', required=True)

    # Treatment
    treatment_applied = fields.Text(string='Treatment Applied')
    treatment_date = fields.Date(string='Treatment Date')
    treatment_cost = fields.Float(string='Treatment Cost')
    treatment_effective = fields.Selection([
        ('yes', 'Yes - Resolved'),
        ('partial', 'Partially Effective'),
        ('no', 'No - Recurred'),
        ('pending', 'Pending Assessment'),
    ], string='Treatment Effective?')

    # Economic Impact
    estimated_yield_loss_percent = fields.Float(string='Est. Yield Loss %')
    estimated_financial_loss = fields.Float(string='Est. Financial Loss')
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', store=True)

    # Photos/Documents
    attachment_ids = fields.Many2many('ir.attachment', string='Photos/Documents')

    # Status
    state = fields.Selection([
        ('detected', 'Detected'),
        ('treating', 'Under Treatment'),
        ('monitoring', 'Monitoring'),
        ('resolved', 'Resolved'),
        ('escalated', 'Escalated'),
    ], string='Status', default='detected', tracking=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('farm.disease') or 'New'
        return super(FarmDiseasePest, self).create(vals_list)

    def action_set_resolved(self):
        self.write({'state': 'resolved', 'resolved_date': fields.Date.today()})

    def action_set_treating(self):
        self.write({'state': 'treating'})

    def action_escalate(self):
        self.write({'state': 'escalated'})
