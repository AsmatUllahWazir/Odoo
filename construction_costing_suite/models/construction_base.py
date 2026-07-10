# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class ConstructionMixin(models.AbstractModel):
    _name = 'construction.mixin'
    _description = 'Construction Base Mixin'

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True
    )
    active = fields.Boolean(default=True)
    notes = fields.Text(string='Notes')
    attachment_ids = fields.Many2many('ir.attachment', string='Attachments')

    @api.model
    def _get_default_currency(self):
        return self.env.company.currency_id


class ConstructionProjectMixin(models.AbstractModel):
    _name = 'construction.project.mixin'
    _description = 'Construction Project Mixin'

    project_id = fields.Many2one('project.project', string='Construction Project', required=True, ondelete='cascade')
    project_name = fields.Char(related='project_id.name', string='Project Name', store=True)
    company_id = fields.Many2one(related='project_id.company_id', string='Company', store=True)
    currency_id = fields.Many2one(related='project_id.currency_id', string='Currency', store=True)
    