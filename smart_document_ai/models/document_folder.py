# -*- coding: utf-8 -*-
from odoo import models, fields, api


class DocumentFolder(models.Model):
    _name = 'document.folder'
    _description = 'Document Folder'
    _order = 'sequence, name'
    _inherit = ['mail.thread']

    name = fields.Char(
        string='Folder Name',
        required=True,
        translate=True,
        index=True,
    )

    description = fields.Text(
        string='Description',
        translate=True,
    )

    sequence = fields.Integer(
        string='Sequence',
        default=10,
    )

    color = fields.Integer(
        string='Color',
        default=0,
    )

    icon = fields.Char(
        string='Icon',
        default='fa-folder',
    )

    active = fields.Boolean(
        string='Active',
        default=True,
    )

    # ─── Hierarchy ───
    parent_id = fields.Many2one(
        'document.folder',
        string='Parent Folder',
        index=True,
    )

    child_ids = fields.One2many(
        'document.folder',
        'parent_id',
        string='Subfolders',
    )

    # ─── Security ───
    owner_id = fields.Many2one(
        'res.users',
        string='Owner',
        default=lambda self: self.env.user,
        required=True,
    )

    access_level = fields.Selection([
        ('private', 'Private'),
        ('internal', 'Internal'),
        ('department', 'Department'),
        ('public', 'Public'),
    ], string='Access Level', default='internal', required=True)

    allowed_user_ids = fields.Many2many(
        'res.users',
        string='Allowed Users',
    )

    # ─── Statistics ───
    document_count = fields.Integer(
        string='Documents',
        compute='_compute_document_count',
    )

    total_size = fields.Integer(
        string='Total Size (Bytes)',
        compute='_compute_total_size',
    )

    total_size_human = fields.Char(
        string='Total Size',
        compute='_compute_total_size',
    )

    # ─── Computed ───
    def _compute_document_count(self):
        for folder in self:
            folder.document_count = self.env['smart.document'].search_count([
                ('folder_id', '=', folder.id),
            ])

    def _compute_total_size(self):
        for folder in self:
            docs = self.env['smart.document'].search([
                ('folder_id', '=', folder.id),
            ])
            total = sum(docs.mapped('file_size'))
            folder.total_size = total
            folder.total_size_human = self._format_size(total)

    def _format_size(self, size_bytes):
        if size_bytes == 0:
            return '0 B'
        units = ['B', 'KB', 'MB', 'GB']
        i = 0
        while size_bytes >= 1024 and i < len(units) - 1:
            size_bytes /= 1024.0
            i += 1
        return "%.1f %s" % (size_bytes, units[i])

    # ─── Constraints ───
    @api.constrains('parent_id')
    def _check_parent_not_self(self):
        for folder in self:
            if folder.parent_id and folder.parent_id.id == folder.id:
                raise models.ValidationError('A folder cannot be its own parent.')
