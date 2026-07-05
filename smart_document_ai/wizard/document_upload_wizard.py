# -*- coding: utf-8 -*-
import base64
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class DocumentUploadWizard(models.TransientModel):
    _name = 'document.upload.wizard'
    _description = 'Document Upload Wizard'

    folder_id = fields.Many2one('document.folder', string='Folder')
    category_id = fields.Many2one('document.category', string='Category')
    tag_ids = fields.Many2many('document.tag', string='Tags')
    access_level = fields.Selection([
        ('private', 'Private'),
        ('internal', 'Internal'),
        ('department', 'Department'),
        ('public', 'Public'),
    ], string='Access Level', default='internal')
    file = fields.Binary(string='File', required=True)
    file_name = fields.Char(string='File Name', required=True)
    description = fields.Html(string='Description')
    expiration_date = fields.Date(string='Expiration Date')

    @api.onchange('file_name')
    def _onchange_file_name(self):
        if self.file_name:
            name = self.file_name.rsplit('.', 1)[0] if '.' in self.file_name else self.file_name
            return {'value': {'description': name.replace('_', ' ').replace('-', ' ').title()}}

    def action_upload(self):
        self.ensure_one()
        if not self.file:
            raise UserError(_('Please select a file to upload.'))

        # Check for duplicates
        duplicate_check = self.env['ir.config_parameter'].sudo().get_param(
            'smart_document_ai.duplicate_check', 'True') == 'True'

        file_content = base64.b64decode(self.file)
        file_hash = __import__('hashlib').sha256(file_content).hexdigest()

        if duplicate_check:
            existing = self.env['smart.document'].search([
                ('file_hash', '=', file_hash),
            ], limit=1)
            if existing:
                raise UserError(_(
                    'Duplicate detected! This file already exists as "%s". '
                    'Please use the existing document or remove the duplicate check setting.'
                ) % existing.name)

        document = self.env['smart.document'].create({
            'name': self.file_name.rsplit('.', 1)[0].replace('_', ' ').replace('-', ' ').title(),
            'file': self.file,
            'file_name': self.file_name,
            'folder_id': self.folder_id.id,
            'category_id': self.category_id.id,
            'tag_ids': [(6, 0, self.tag_ids.ids)],
            'access_level': self.access_level,
            'description': self.description,
            'expiration_date': self.expiration_date,
        })

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'smart.document',
            'res_id': document.id,
            'view_mode': 'form',
            'target': 'current',
        }
