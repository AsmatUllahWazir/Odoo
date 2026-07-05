# -*- coding: utf-8 -*-
import base64
import hashlib
import re
from datetime import datetime, timedelta

from odoo import models, fields, api, _, tools
from odoo.exceptions import UserError, ValidationError


class SmartDocument(models.Model):
    _name = 'smart.document'
    _description = 'Smart Document'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    # ─── Core Fields ───
    name = fields.Char(
        string='Document Name',
        required=True,
        tracking=True,
        index=True,
    )

    description = fields.Html(
        string='Description',
        sanitize=True,
    )

    file = fields.Binary(
        string='File',
        required=True,
        attachment=True,
        tracking=True,
    )

    file_name = fields.Char(
        string='File Name',
        required=True,
    )

    file_size = fields.Integer(
        string='File Size (Bytes)',
        compute='_compute_file_info',
        store=True,
    )

    file_size_human = fields.Char(
        string='File Size',
        compute='_compute_file_info',
        store=True,
    )

    file_type = fields.Char(
        string='File Type',
        compute='_compute_file_info',
        store=True,
    )

    file_extension = fields.Char(
        string='Extension',
        compute='_compute_file_info',
        store=True,
    )

    mime_type = fields.Char(
        string='MIME Type',
        compute='_compute_file_info',
        store=True,
    )

    file_hash = fields.Char(
        string='File Hash (SHA-256)',
        compute='_compute_file_hash',
        store=True,
        index=True,
    )

    # ─── Categorization ───
    category_id = fields.Many2one(
        'document.category',
        string='Category',
        tracking=True,
        index=True,
        help='AI-detected or manually assigned document category',
    )

    category_confidence = fields.Float(
        string='AI Confidence',
        digits=(3, 2),
        help='Confidence score of AI categorization (0.0 - 1.0)',
    )

    folder_id = fields.Many2one(
        'document.folder',
        string='Folder',
        tracking=True,
        index=True,
    )

    tag_ids = fields.Many2many(
        'document.tag',
        string='Tags',
        tracking=True,
    )

    # ─── AI & Content Analysis ───
    extracted_text = fields.Text(
        string='Extracted Text',
        help='OCR-extracted text content from the document',
    )

    detected_language = fields.Char(
        string='Detected Language',
        size=5,
        help='ISO 639-1 language code detected from content',
    )

    document_summary = fields.Text(
        string='AI Summary',
        help='Auto-generated summary of document content',
    )

    keywords = fields.Char(
        string='Keywords',
        help='Comma-separated keywords extracted from document',
    )

    # ─── Duplicate Detection ───
    is_duplicate = fields.Boolean(
        string='Is Duplicate',
        compute='_compute_duplicate_info',
        store=True,
        help='True if this document has duplicates',
    )

    duplicate_count = fields.Integer(
        string='Duplicate Count',
        compute='_compute_duplicate_info',
        store=True,
    )

    # ─── Security & Access ───
    owner_id = fields.Many2one(
        'res.users',
        string='Owner',
        default=lambda self: self.env.user,
        required=True,
        tracking=True,
    )

    access_level = fields.Selection([
        ('private', 'Private'),
        ('internal', 'Internal'),
        ('department', 'Department'),
        ('public', 'Public'),
    ], string='Access Level', default='internal', required=True, tracking=True)

    allowed_user_ids = fields.Many2many(
        'res.users',
        string='Allowed Users',
        help='Users with explicit access to this document',
    )

    # ─── Status & Workflow ───
    state = fields.Selection([
        ('draft', 'Draft'),
        ('review', 'Under Review'),
        ('approved', 'Approved'),
        ('archived', 'Archived'),
        ('rejected', 'Rejected'),
    ], string='Status', default='draft', required=True, tracking=True)

    priority = fields.Selection([
        ('0', 'Low'),
        ('1', 'Normal'),
        ('2', 'High'),
        ('3', 'Urgent'),
    ], string='Priority', default='1')

    is_favorite = fields.Boolean(
        string='Favorite',
        default=False,
    )

    # ─── Metadata ───
    partner_id = fields.Many2one(
        'res.partner',
        string='Related Partner',
        tracking=True,
    )

    related_model = fields.Char(
        string='Related Model',
        help='Technical name of related Odoo model',
    )

    related_record_id = fields.Integer(
        string='Related Record ID',
    )

    related_record_ref = fields.Reference(
        selection='_select_related_model',
        string='Related Record',
        compute='_compute_related_record_ref',
        store=False,
    )

    expiration_date = fields.Date(
        string='Expiration Date',
        tracking=True,
    )

    is_expired = fields.Boolean(
        string='Expired',
        compute='_compute_is_expired',
        store=True,
    )

    version = fields.Integer(
        string='Version',
        default=1,
    )

    parent_document_id = fields.Many2one(
        'smart.document',
        string='Previous Version',
        help='Link to the previous version of this document',
    )

    child_document_ids = fields.One2many(
        'smart.document',
        'parent_document_id',
        string='Newer Versions',
    )

    # ─── Statistics ───
    download_count = fields.Integer(
        string='Downloads',
        default=0,
    )

    view_count = fields.Integer(
        string='Views',
        default=0,
    )

    last_accessed = fields.Datetime(
        string='Last Accessed',
    )

    last_accessed_by = fields.Many2one(
        'res.users',
        string='Last Accessed By',
    )

    # ─── Computed Fields ───
    @api.depends('file_name')
    def _compute_file_info(self):
        for doc in self:
            if doc.file_name:
                ext = doc.file_name.split('.')[-1].lower() if '.' in doc.file_name else ''
                doc.file_extension = ext

                mime_map = {
                    'pdf': 'application/pdf',
                    'doc': 'application/msword',
                    'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                    'xls': 'application/vnd.ms-excel',
                    'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    'ppt': 'application/vnd.ms-powerpoint',
                    'pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
                    'txt': 'text/plain',
                    'jpg': 'image/jpeg',
                    'jpeg': 'image/jpeg',
                    'png': 'image/png',
                    'gif': 'image/gif',
                    'tiff': 'image/tiff',
                    'zip': 'application/zip',
                }
                doc.mime_type = mime_map.get(ext, 'application/octet-stream')
                doc.file_type = ext.upper() if ext else 'Unknown'

                if doc.file:
                    try:
                        size = len(base64.b64decode(doc.file or ''))
                        doc.file_size = size
                        doc.file_size_human = self._format_file_size(size)
                    except Exception:
                        doc.file_size = 0
                        doc.file_size_human = '0 B'
                else:
                    doc.file_size = 0
                    doc.file_size_human = '0 B'
            else:
                doc.file_extension = ''
                doc.mime_type = ''
                doc.file_type = 'Unknown'
                doc.file_size = 0
                doc.file_size_human = '0 B'

    @api.depends('file')
    def _compute_file_hash(self):
        for doc in self:
            if doc.file:
                try:
                    content = base64.b64decode(doc.file)
                    doc.file_hash = hashlib.sha256(content).hexdigest()
                except Exception:
                    doc.file_hash = ''
            else:
                doc.file_hash = ''

    @api.depends('file_hash')
    def _compute_duplicate_info(self):
        for doc in self:
            # SAFETY: Check if we have a real ID
            if not doc.id:
                doc.is_duplicate = False
                doc.duplicate_count = 0
                continue

            # SAFETY: Check if it's a temporary NewId
            if isinstance(doc.id, str):
                doc.is_duplicate = False
                doc.duplicate_count = 0
                continue

            # SAFETY: Try to convert to int
            try:
                doc_id = int(doc.id)
            except (ValueError, TypeError):
                doc.is_duplicate = False
                doc.duplicate_count = 0
                continue

            if doc.file_hash:
                try:
                    duplicates = self.search([
                        ('file_hash', '=', doc.file_hash),
                        ('id', '!=', doc_id),
                    ])
                    doc.is_duplicate = bool(duplicates)
                    doc.duplicate_count = len(duplicates)
                except Exception:
                    doc.is_duplicate = False
                    doc.duplicate_count = 0
            else:
                doc.is_duplicate = False
                doc.duplicate_count = 0

    @api.depends('related_model', 'related_record_id')
    def _compute_related_record_ref(self):
        for doc in self:
            if doc.related_model and doc.related_record_id:
                try:
                    doc.related_record_ref = '%s,%s' % (doc.related_model, doc.related_record_id)
                except Exception:
                    doc.related_record_ref = False
            else:
                doc.related_record_ref = False

    @api.depends('expiration_date')
    def _compute_is_expired(self):
        today = fields.Date.today()
        for doc in self:
            doc.is_expired = bool(doc.expiration_date and doc.expiration_date < today)

    @api.model
    def _select_related_model(self):
        models = self.env['ir.model'].search([('transient', '=', False)])
        return [(m.model, m.name) for m in models]

    # ─── Helper Methods ───
    def _format_file_size(self, size_bytes):
        if size_bytes == 0:
            return '0 B'
        units = ['B', 'KB', 'MB', 'GB', 'TB']
        i = 0
        while size_bytes >= 1024 and i < len(units) - 1:
            size_bytes /= 1024.0
            i += 1
        return "%.1f %s" % (size_bytes, units[i])

    # ─── Smart Categorization ───
    def action_auto_categorize(self):
        for doc in self:
            if not doc.extracted_text and not doc.file_name:
                continue

            content = (doc.extracted_text or '') + ' ' + (doc.file_name or '')
            content_lower = content.lower()

            categories = self.env['document.category'].search([])
            best_match = None
            best_score = 0.0

            for category in categories:
                score = 0.0
                if category.keywords:
                    cat_keywords = [k.strip().lower() for k in category.keywords.split(',')]
                    matches = sum(1 for kw in cat_keywords if kw in content_lower)
                    score = matches / len(cat_keywords) if cat_keywords else 0

                if category.allowed_extensions and doc.file_extension:
                    allowed = [ext.strip().lower() for ext in category.allowed_extensions.split(',')]
                    if doc.file_extension.lower() in allowed:
                        score += 0.3

                if score > best_score:
                    best_score = score
                    best_match = category

            if best_match and best_score > 0.2:
                doc.category_id = best_match
                doc.category_confidence = min(best_score, 1.0)

                if best_match.auto_tag_ids:
                    doc.tag_ids = [(4, tag.id) for tag in best_match.auto_tag_ids]

                if doc.extracted_text:
                    sentences = re.split(r'[.!?]+', doc.extracted_text)
                    summary = '. '.join(sentences[:3]) + '.' if len(sentences) > 3 else doc.extracted_text[:500]
                    doc.document_summary = summary[:1000]

    # ─── Duplicate Management ───
    def action_find_duplicates(self):
        self.ensure_one()
        if not self.is_duplicate:
            raise UserError(_('No duplicates found for this document.'))

        duplicates = self.search([
            ('file_hash', '=', self.file_hash),
            ('id', '!=', self.id),
        ])

        return {
            'name': _('Duplicate Documents'),
            'type': 'ir.actions.act_window',
            'res_model': 'smart.document',
            'view_mode': 'kanban,tree,form',
            'domain': [('id', 'in', duplicates.ids)],
            'target': 'current',
        }

    def action_merge_duplicates(self):
        self.ensure_one()
        if not self.is_duplicate:
            raise UserError(_('No duplicates to merge.'))

        duplicates = self.search([
            ('file_hash', '=', self.file_hash),
            ('id', '!=', self.id),
        ])

        return {
            'name': _('Merge Duplicate Documents'),
            'type': 'ir.actions.act_window',
            'res_model': 'document.merge.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_primary_document_id': self.id,
                'default_duplicate_ids': [(6, 0, duplicates.ids)],
            },
        }

    # ─── Version Control ───
    def action_create_new_version(self):
        self.ensure_one()

        new_doc = self.copy(default={
            'name': "%s (v%s)" % (self.name, self.version + 1),
            'version': self.version + 1,
            'parent_document_id': self.id,
            'state': 'draft',
            'download_count': 0,
            'view_count': 0,
        })

        self.write({'state': 'archived'})

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'smart.document',
            'res_id': new_doc.id,
            'view_mode': 'form',
            'target': 'current',
        }

    # ─── Download & Preview ───
    def action_download(self):
        self.ensure_one()
        self.download_count += 1
        self.last_accessed = fields.Datetime.now()
        self.last_accessed_by = self.env.user

        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/smart.document/%s/file/%s?download=1' % (self.id, self.file_name),
            'target': 'self',
        }

    def action_preview(self):
        self.ensure_one()
        self.view_count += 1
        self.last_accessed = fields.Datetime.now()
        self.last_accessed_by = self.env.user

        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/smart.document/%s/file/%s' % (self.id, self.file_name),
            'target': 'new',
        }

    # ─── Workflow Actions ───
    def action_submit_for_review(self):
        self.write({'state': 'review'})

    def action_approve(self):
        self.write({'state': 'approved'})

    def action_reject(self):
        self.write({'state': 'rejected'})

    def action_archive(self):
        self.write({'state': 'archived'})

    def action_restore(self):
        self.write({'state': 'draft'})

    def action_toggle_favorite(self):
        self.write({'is_favorite': not self.is_favorite})

    # ─── Bulk Operations ───
    def action_bulk_tag(self):
        return {
            'name': _('Bulk Tag Documents'),
            'type': 'ir.actions.act_window',
            'res_model': 'bulk.tag.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_document_ids': [(6, 0, self.ids)],
            },
        }

    # ─── Cron: Expiration Check ───
    @api.model
    def _cron_check_expired_documents(self):
        today = fields.Date.today()
        warning_date = today + timedelta(days=7)

        expiring_docs = self.search([
            ('expiration_date', '<=', warning_date),
            ('expiration_date', '>=', today),
            ('state', 'not in', ['archived', 'rejected']),
        ])

        for doc in expiring_docs:
            doc.message_post(
                body=_("Document '%s' is expiring on %s. Please review.") % (doc.name, doc.expiration_date),
                message_type='notification',
                subtype_xmlid='mail.mt_comment',
            )

    # ─── Cron: Auto-Categorize Uncategorized ───
    @api.model
    def _cron_auto_categorize(self):
        uncategorized = self.search([
            ('category_id', '=', False),
            ('state', 'not in', ['archived', 'rejected']),
        ], limit=100)
        uncategorized.action_auto_categorize()

    # ─── Onchange ───
    @api.onchange('file_name')
    def _onchange_file_name(self):
        if self.file_name and not self.name:
            name = self.file_name.rsplit('.', 1)[0] if '.' in self.file_name else self.file_name
            self.name = name.replace('_', ' ').replace('-', ' ').title()

    # ─── Override Create ───
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('file_name') and not vals.get('name'):
                name = vals['file_name'].rsplit('.', 1)[0] if '.' in vals['file_name'] else vals['file_name']
                vals['name'] = name.replace('_', ' ').replace('-', ' ').title()

        records = super(SmartDocument, self).create(vals_list)

        for record in records:
            if not record.category_id:
                record.action_auto_categorize()

        return records

    # ─── Override Write ───
    def write(self, vals):
        if 'file' in vals and vals.get('file'):
            vals['file_hash'] = False
        return super(SmartDocument, self).write(vals)

    # ─── Override Unlink ───
    def unlink(self):
        for doc in self:
            if doc.state == 'approved':
                raise UserError(_('Cannot delete approved documents. Archive them instead.'))
        return super(SmartDocument, self).unlink()

    # ─── Search Methods ───
    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        domain = []
        if name:
            domain = ['|', '|', '|',
                      ('name', operator, name),
                      ('file_name', operator, name),
                      ('extracted_text', operator, name),
                      ('keywords', operator, name),
                      ]
        return self._search(domain + args, limit=limit, access_rights_uid=name_get_uid)

    # ─── Smart Search ───
    @api.model
    def smart_search(self, query, limit=20):
        if not query or len(query.strip()) < 2:
            return self.browse([])

        query_lower = query.lower().strip()

        exact = self.search([('name', 'ilike', query_lower)], limit=limit)
        if exact:
            return exact

        content = self.search([
            '|', '|', '|', '|',
            ('name', 'ilike', query_lower),
            ('extracted_text', 'ilike', query_lower),
            ('keywords', 'ilike', query_lower),
            ('document_summary', 'ilike', query_lower),
            ('file_name', 'ilike', query_lower),
        ], limit=limit)

        return content
