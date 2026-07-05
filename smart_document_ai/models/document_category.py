# -*- coding: utf-8 -*-
from odoo import models, fields, api


class DocumentCategory(models.Model):
    _name = 'document.category'
    _description = 'Document Category'
    _order = 'sequence, name'
    _inherit = ['mail.thread']

    name = fields.Char(
        string='Category Name',
        required=True,
        translate=True,
        index=True,
    )

    description = fields.Text(
        string='Description',
        translate=True,
    )

    code = fields.Char(
        string='Code',
        required=True,
        index=True,
        help='Unique code for this category',
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
        default='fa-file-o',
        help='Font Awesome icon class',
    )

    active = fields.Boolean(
        string='Active',
        default=True,
    )

    # ─── AI Configuration ───
    keywords = fields.Text(
        string='Detection Keywords',
        help='Comma-separated keywords for AI auto-detection. Example: invoice, bill, payment',
    )

    allowed_extensions = fields.Char(
        string='Allowed Extensions',
        help='Comma-separated file extensions. Example: pdf, docx, xlsx',
    )

    auto_tag_ids = fields.Many2many(
        'document.tag',
        string='Auto-Assign Tags',
        help='Tags automatically assigned to documents in this category',
    )

    # ─── Statistics ───
    document_count = fields.Integer(
        string='Document Count',
        compute='_compute_document_count',
    )

    # ─── Hierarchy ───
    parent_id = fields.Many2one(
        'document.category',
        string='Parent Category',
        index=True,
    )

    child_ids = fields.One2many(
        'document.category',
        'parent_id',
        string='Subcategories',
    )

    # ─── Settings ───
    retention_days = fields.Integer(
        string='Retention Period (Days)',
        help='Number of days to retain documents in this category before archival',
    )

    requires_approval = fields.Boolean(
        string='Requires Approval',
        default=False,
        help='Documents in this category require approval workflow',
    )

    approver_ids = fields.Many2many(
        'res.users',
        string='Approvers',
        help='Users who can approve documents in this category',
    )

    # ─── Computed ───
    def _compute_document_count(self):
        for category in self:
            category.document_count = self.env['smart.document'].search_count([
                ('category_id', '=', category.id),
            ])

    # ─── Constraints ───
    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'Category code must be unique!'),
    ]

    @api.constrains('parent_id')
    def _check_parent_not_self(self):
        for category in self:
            if category.parent_id and category.parent_id.id == category.id:
                raise models.ValidationError('A category cannot be its own parent.')
