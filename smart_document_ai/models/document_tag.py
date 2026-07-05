# -*- coding: utf-8 -*-
from odoo import models, fields, api


class DocumentTag(models.Model):
    _name = 'document.tag'
    _description = 'Document Tag'
    _order = 'name'

    name = fields.Char(
        string='Tag Name',
        required=True,
        translate=True,
        index=True,
    )

    color = fields.Integer(
        string='Color',
        default=0,
    )

    description = fields.Text(
        string='Description',
        translate=True,
    )

    active = fields.Boolean(
        string='Active',
        default=True,
    )

    document_count = fields.Integer(
        string='Documents',
        compute='_compute_document_count',
    )

    # ─── Computed ───
    def _compute_document_count(self):
        for tag in self:
            tag.document_count = self.env['smart.document'].search_count([
                ('tag_ids', 'in', tag.id),
            ])

    # ─── Constraints ───
    _sql_constraints = [
        ('name_unique', 'UNIQUE(name)', 'Tag name must be unique!'),
    ]

    # ─── Name Get ───
    def name_get(self):
        result = []
        for tag in self:
            result.append((tag.id, tag.name))
        return result
