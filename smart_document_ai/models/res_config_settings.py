# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # ─── AI Settings ───
    module_smart_document_ai_ocr = fields.Boolean(
        string='Enable OCR (Text Extraction)',
        help='Extract text from PDFs and images using OCR',
    )

    document_auto_categorize = fields.Boolean(
        string='Auto-Categorize on Upload',
        config_parameter='smart_document_ai.auto_categorize',
        help='Automatically categorize documents when uploaded',
    )

    document_auto_tag = fields.Boolean(
        string='Auto-Tag on Upload',
        config_parameter='smart_document_ai.auto_tag',
        help='Automatically generate tags from document content',
    )

    document_duplicate_check = fields.Boolean(
        string='Check Duplicates on Upload',
        config_parameter='smart_document_ai.duplicate_check',
        default=True,
        help='Warn users when uploading duplicate documents',
    )

    # ─── Storage Settings ───
    document_max_size = fields.Integer(
        string='Max File Size (MB)',
        config_parameter='smart_document_ai.max_file_size',
        default=50,
        help='Maximum allowed file size in megabytes',
    )

    document_allowed_extensions = fields.Char(
        string='Allowed Extensions',
        config_parameter='smart_document_ai.allowed_extensions',
        default='pdf,doc,docx,xls,xlsx,ppt,pptx,txt,jpg,jpeg,png,tiff,zip',
        help='Comma-separated list of allowed file extensions',
    )

    # ─── Retention Settings ───
    document_retention_days = fields.Integer(
        string='Default Retention (Days)',
        config_parameter='smart_document_ai.retention_days',
        default=365,
        help='Default number of days to retain documents before archival',
    )

    document_auto_archive = fields.Boolean(
        string='Auto-Archive Expired Documents',
        config_parameter='smart_document_ai.auto_archive',
        help='Automatically archive documents past their expiration date',
    )

    # ─── Notification Settings ───
    document_notify_expiration = fields.Boolean(
        string='Notify Before Expiration',
        config_parameter='smart_document_ai.notify_expiration',
        default=True,
        help='Send notifications before documents expire',
    )

    document_notify_days_before = fields.Integer(
        string='Notify Days Before',
        config_parameter='smart_document_ai.notify_days_before',
        default=7,
        help='Number of days before expiration to send notification',
    )
