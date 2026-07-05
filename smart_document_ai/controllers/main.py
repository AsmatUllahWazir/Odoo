# -*- coding: utf-8 -*-
import json
import base64
from odoo import http, fields
from odoo.http import request


class SmartDocumentController(http.Controller):

    @http.route('/smart_document/upload', type='http', auth='user', methods=['POST'], csrf=False)
    def upload_document(self, **kwargs):
        """Handle drag-and-drop file uploads."""
        files = request.httprequest.files.getlist('files')
        uploaded = []

        for file in files:
            content = base64.b64encode(file.read()).decode('utf-8')
            doc = request.env['smart.document'].create({
                'name': file.filename.rsplit('.', 1)[0].replace('_', ' ').replace('-', ' ').title(),
                'file': content,
                'file_name': file.filename,
            })
            uploaded.append({
                'id': doc.id,
                'name': doc.name,
                'status': 'success',
            })

        return request.make_response(
            json.dumps({'success': True, 'documents': uploaded}),
            headers=[('Content-Type', 'application/json')]
        )

    @http.route('/smart_document/preview/<int:document_id>', type='http', auth='user')
    def preview_document(self, document_id, **kwargs):
        """Generate document preview."""
        document = request.env['smart.document'].browse(document_id)
        if not document.exists() or not document.file:
            return request.not_found()

        # Update view stats
        document.sudo().write({
            'view_count': document.view_count + 1,
            'last_accessed': fields.Datetime.now(),
            'last_accessed_by': request.env.user.id,
        })

        file_content = base64.b64decode(document.file)
        return request.make_response(
            file_content,
            headers=[
                ('Content-Type', document.mime_type or 'application/octet-stream'),
                ('Content-Disposition', 'inline; filename="%s"' % document.file_name),
            ]
        )
