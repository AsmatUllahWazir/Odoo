# -*- coding: utf-8 -*-
{
    'name': 'Smart Document AI',
    'version': '17.0.1.0.0',
    'category': 'Document Management',
    'summary': 'AI-Powered Smart Document Management with Auto-Categorization, Duplicate Detection & Intelligent Search',
    'description': """
Smart Document AI - Revolutionize Your Document Management
==========================================================

A next-generation document management system that leverages AI and smart algorithms
to automatically organize, categorize, and manage your business documents.

**Key Features:**

- **AI Auto-Categorization**: Automatically categorizes documents based on content analysis
- **Smart Pattern Recognition**: For invoices, contracts, receipts, etc.
- **Machine Learning**: Improves over time

- **Intelligent Full-Text Search**: OCR-powered text extraction, fuzzy search with typo tolerance
- **Duplicate Detection**: Hash-based and content-similarity detection
- **Smart Tagging System**: Auto-generated tags, custom hierarchies, color coding
- **Document Analytics Dashboard**: Visual insights, storage optimization reports
- **Advanced Security**: Role-based access control, audit trail
- **Modern UI**: Drag-and-drop upload, Kanban/List/Grid views

**Supported Formats:** PDF, DOC/DOCX, XLS/XLSX, PPT/PPTX, TXT, JPG, PNG, TIFF
    """,
    'author': 'Wazirz',
    'website': '',
    'license': 'OPL-1',
    'price': 89.00,
    'currency': 'USD',
    'depends': [
        'base',
        'mail',
        'web',
        'portal',
    ],
    'data': [
        'security/smart_document_security.xml',
        'security/ir.model.access.csv',
        'data/document_category_data.xml',
        'data/document_tag_data.xml',
        'data/ir_cron_data.xml',
        'data/mail_template_data.xml',
        'views/smart_document_views.xml',
        'views/document_category_views.xml',
        'views/document_tag_views.xml',
        'views/document_folder_views.xml',
        'views/document_analytics_views.xml',
        'views/res_config_settings_views.xml',
        'wizard/document_upload_wizard_views.xml',
        'wizard/document_merge_wizard_views.xml',
        'wizard/bulk_tag_wizard_views.xml',
        'report/document_report_templates.xml',
        'views/menu_views.xml',
    ],
    'demo': [
        'demo/document_demo.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'smart_document_ai/static/src/scss/smart_document.scss',
            'smart_document_ai/static/src/components/document_dropzone/document_dropzone.js',
            'smart_document_ai/static/src/components/document_dropzone/document_dropzone.xml',
            'smart_document_ai/static/src/components/document_preview/document_preview.js',
            'smart_document_ai/static/src/components/document_preview/document_preview.xml',
            'smart_document_ai/static/src/components/document_analytics/document_analytics.js',
            'smart_document_ai/static/src/components/document_analytics/document_analytics.xml',
        ],
        'web.assets_qweb': [
            'smart_document_ai/static/src/xml/**/*',
        ],
    },

    'images': ['static/description/icon.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
    'external_dependencies': {
        'python': ['PyPDF2', 'python-magic'],
    },
}
