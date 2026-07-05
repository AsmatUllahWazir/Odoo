# -*- coding: utf-8 -*-
from odoo import models, fields, api, tools
from odoo.tools import date_utils
from datetime import datetime, timedelta


class DocumentAnalytics(models.Model):
    _name = 'document.analytics'
    _description = 'Document Analytics'
    _auto = False
    _order = 'date desc'

    date = fields.Date(string='Date', readonly=True)
    document_id = fields.Many2one('smart.document', string='Document', readonly=True)
    category_id = fields.Many2one('document.category', string='Category', readonly=True)
    folder_id = fields.Many2one('document.folder', string='Folder', readonly=True)
    owner_id = fields.Many2one('res.users', string='Owner', readonly=True)

    # Metrics
    upload_count = fields.Integer(string='Uploads', readonly=True)
    download_count = fields.Integer(string='Downloads', readonly=True)
    view_count = fields.Integer(string='Views', readonly=True)
    total_size = fields.Integer(string='Total Size', readonly=True)
    duplicate_count = fields.Integer(string='Duplicates', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    MIN(id) as id,
                    DATE(create_date) as date,
                    id as document_id,
                    category_id,
                    folder_id,
                    owner_id,
                    1 as upload_count,
                    download_count,
                    view_count,
                    file_size as total_size,
                    CASE WHEN is_duplicate THEN 1 ELSE 0 END as duplicate_count
                FROM smart_document
                WHERE state NOT IN ('archived', 'rejected')
                GROUP BY DATE(create_date), id, category_id, folder_id, owner_id,
                         download_count, view_count, file_size, is_duplicate
            )
        """ % self._table)


class DocumentStorageAnalytics(models.Model):
    _name = 'document.storage.analytics'
    _description = 'Storage Analytics'
    _auto = False

    category_id = fields.Many2one('document.category', string='Category', readonly=True)
    folder_id = fields.Many2one('document.folder', string='Folder', readonly=True)
    file_type = fields.Char(string='File Type', readonly=True)

    document_count = fields.Integer(string='Documents', readonly=True)
    total_size = fields.Integer(string='Total Size (Bytes)', readonly=True)
    avg_size = fields.Integer(string='Average Size', readonly=True)
    duplicate_count = fields.Integer(string='Duplicates', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    MIN(id) as id,
                    category_id,
                    folder_id,
                    file_type,
                    COUNT(*) as document_count,
                    SUM(file_size) as total_size,
                    AVG(file_size)::int as avg_size,
                    SUM(CASE WHEN is_duplicate THEN 1 ELSE 0 END) as duplicate_count
                FROM smart_document
                WHERE state NOT IN ('archived', 'rejected')
                GROUP BY category_id, folder_id, file_type
            )
        """ % self._table)
