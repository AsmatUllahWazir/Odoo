# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class DocumentMergeWizard(models.TransientModel):
    _name = 'document.merge.wizard'
    _description = 'Document Merge Wizard'

    primary_document_id = fields.Many2one(
        'smart.document',
        string='Primary Document',
        required=True,
        domain="[('id', 'in', duplicate_ids)]",
    )
    duplicate_ids = fields.Many2many(
        'smart.document',
        'merge_wizard_duplicate_rel',
        'wizard_id',
        'document_id',
        string='Duplicates to Merge',
    )
    keep_primary_only = fields.Boolean(
        string='Keep Only Primary',
        default=True,
        help='If checked, duplicates will be deleted. Otherwise, they will be archived.',
    )
    merge_tags = fields.Boolean(
        string='Merge All Tags',
        default=True,
        help='Combine tags from all duplicates into the primary document',
    )

    @api.onchange('duplicate_ids')
    def _onchange_duplicate_ids(self):
        if self.duplicate_ids and not self.primary_document_id:
            return {'value': {'primary_document_id': self.duplicate_ids[0].id}}

    def action_merge(self):
        self.ensure_one()
        if not self.primary_document_id or not self.duplicate_ids:
            raise UserError(_('Please select a primary document and duplicates to merge.'))

        primary = self.primary_document_id
        duplicates = self.duplicate_ids - primary

        if not duplicates:
            raise UserError(_('No duplicates selected for merging.'))

        # Merge tags
        if self.merge_tags:
            all_tags = primary.tag_ids | duplicates.mapped('tag_ids')
            primary.tag_ids = [(6, 0, all_tags.ids)]

        # Update download/view counts
        primary.download_count += sum(duplicates.mapped('download_count'))
        primary.view_count += sum(duplicates.mapped('view_count'))

        # Add merge note
        duplicate_names = ', '.join(duplicates.mapped('name'))
        primary.message_post(
            body=_("Merged duplicates: %s") % duplicate_names,
            message_type='notification',
        )

        # Remove or archive duplicates
        if self.keep_primary_only:
            duplicates.unlink()
        else:
            duplicates.write({'state': 'archived'})

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'smart.document',
            'res_id': primary.id,
            'view_mode': 'form',
            'target': 'current',
        }
