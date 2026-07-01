# -*- coding: utf-8 -*-
import datetime
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging
import json

_logger = logging.getLogger(__name__)


class VendorBillOCRResult(models.Model):
    _name = 'vendor.bill.ocr.result'
    _description = 'Vendor Bill OCR Result'
    _order = 'create_date desc'

    invoice_id = fields.Many2one(
        'account.move',
        string='Invoice',
        required=True,
        ondelete='cascade',
        index=True,
    )

    attachment_id = fields.Many2one(
        'ir.attachment',
        string='Source Document',
        required=True,
        ondelete='cascade',
    )

    status = fields.Selection([
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('done', 'Done'),
        ('error', 'Error'),
    ], string='Status', default='pending', required=True)

    # Extracted Data
    vendor_name = fields.Char(string='Vendor Name')
    vendor_vat = fields.Char(string='Vendor VAT')
    vendor_address = fields.Text(string='Vendor Address')

    invoice_number = fields.Char(string='Invoice Number')
    invoice_date = fields.Date(string='Invoice Date')
    due_date = fields.Date(string='Due Date')

    currency_code = fields.Char(string='Currency Code')

    subtotal = fields.Float(string='Subtotal')
    tax_amount = fields.Float(string='Tax Amount')
    total_amount = fields.Float(string='Total Amount')

    iban = fields.Char(string='IBAN')

    full_text = fields.Text(string='Full OCR Text')
    raw_response = fields.Text(string='Raw OCR Response')

    confidence_score = fields.Float(
        string='Confidence Score (%)',
        help='Overall confidence of OCR results',
    )

    field_confidence_json = fields.Text(
        string='Field Confidence JSON',
        help='JSON with confidence per field',
    )

    error_message = fields.Text(string='Error Message')

    processing_started = fields.Datetime(string='Processing Started')
    processing_completed = fields.Datetime(string='Processing Completed')
    processing_duration = fields.Float(
        string='Processing Duration (seconds)',
        compute='_compute_processing_duration',
        store=True,
    )

    custom_field_1 = fields.Char(string='Custom Field 1')
    custom_field_2 = fields.Char(string='Custom Field 2')
    custom_field_3 = fields.Char(string='Custom Field 3')
    custom_field_4 = fields.Char(string='Custom Field 4')
    custom_field_5 = fields.Char(string='Custom Field 5')

    @api.depends('processing_started', 'processing_completed')
    def _compute_processing_duration(self):
        for record in self:
            if record.processing_started and record.processing_completed:
                delta = record.processing_completed - record.processing_started
                record.processing_duration = delta.total_seconds()
            else:
                record.processing_duration = 0.0

    def process_ocr(self):
        """Process OCR for the attached document"""
        self.ensure_one()

        if not self.attachment_id:
            raise UserError(_('No attachment found for OCR processing.'))

        self.write({
            'status': 'processing',
            'processing_started': fields.Datetime.now(),
        })

        try:
            config = self.env['vendor.bill.dispatch.config'].sudo().get_active_config()

            if config.ocr_provider == 'odoo_iap':
                result = self._process_odoo_iap_ocr()
            else:
                result = self._process_custom_ocr()

            self.write({
                'status': 'done',
                'processing_completed': fields.Datetime.now(),
                **result
            })

            self._apply_ocr_to_invoice()

            self.invoice_id.write({
                'ocr_status': 'done',
                'ocr_confidence': self.confidence_score,
            })

            if self.confidence_score >= config.ocr_confidence_threshold:
                if config.auto_dispatch_enabled:
                    self.invoice_id.action_auto_dispatch()

        except Exception as e:
            _logger.error(f'OCR processing failed: {str(e)}')
            self.write({
                'status': 'error',
                'error_message': str(e),
                'processing_completed': fields.Datetime.now(),
            })

            self.invoice_id.write({
                'ocr_status': 'error',
                'ocr_error_message': str(e),
            })

    def _process_odoo_iap_ocr(self):
        """Process OCR using Odoo IAP Document Digitization"""
        try:
            # Simulated OCR result (replace with actual IAP call in production)
            # In production, use: self.env['account.move']._contact_iap_extract(...)

            return {
                'vendor_name': 'Sample Vendor',
                'vendor_vat': 'BE0123456789',
                'invoice_number': 'INV-2026-001',
                'invoice_date': fields.Date.today(),
                'total_amount': 1000.0,
                'currency_code': 'EUR',
                'full_text': 'Sample invoice text for testing',
                'confidence_score': 85.0,
            }

        except Exception as e:
            _logger.error(f'IAP OCR failed: {str(e)}')
            return self._process_manual_ocr()

    def _process_custom_ocr(self):
        """Process OCR using custom engine (placeholder)"""
        raise NotImplementedError(_('Custom OCR engine not yet implemented. Please use Odoo IAP.'))

    def _process_manual_ocr(self):
        """Fallback: Mark for manual entry"""
        return {
            'status': 'error',
            'error_message': 'OCR service unavailable. Please enter data manually.',
            'confidence_score': 0.0,
        }

    def _apply_ocr_to_invoice(self):
        """Apply OCR results to invoice fields"""
        self.ensure_one()

        vals = {}

        if self.vendor_name:
            partner = self._find_or_create_partner()
            if partner:
                vals['partner_id'] = partner.id

        if self.invoice_number:
            vals['ref'] = self.invoice_number

        if self.invoice_date:
            vals['invoice_date'] = self.invoice_date

        if self.due_date:
            vals['invoice_date_due'] = self.due_date

        if self.currency_code:
            currency = self.env['res.currency'].search([
                ('name', '=', self.currency_code.upper())
            ], limit=1)
            if currency:
                vals['currency_id'] = currency.id

        if vals:
            self.invoice_id.write(vals)

    def _find_or_create_partner(self):
        """Find or create partner based on OCR data"""
        Partner = self.env['res.partner']

        domain = []
        if self.vendor_vat:
            domain.append(('vat', '=', self.vendor_vat))

        if domain:
            partner = Partner.search(domain, limit=1)
            if partner:
                return partner

        if self.vendor_name:
            partner = Partner.search([
                ('name', 'ilike', self.vendor_name)
            ], limit=1)
            if partner:
                return partner

        return None

    def action_view_attachment(self):
        """Open the source document"""
        self.ensure_one()

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{self.attachment_id.id}',
            'target': 'new',
        }

    def action_reprocess_ocr(self):
        """Reprocess OCR"""
        self.ensure_one()

        self.write({
            'status': 'pending',
            'error_message': False,
        })

        self.process_ocr()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('OCR Reprocessing'),
                'message': _('OCR reprocessing initiated.'),
                'type': 'info',
            }
        }

    @api.model
    def cleanup_old_ocr_data(self):
        """Delete OCR records older than retention period"""
        config = self.env['vendor.bill.dispatch.config'].search([('active', '=', True)], limit=1)
        if config and config.retention_days > 0:
            cutoff_date = datetime.now() - timedelta(days=config.retention_days)
            old_records = self.search([
                ('create_date', '<', cutoff_date),
                ('status', 'in', ['done', 'error'])
            ])
            if old_records:
                old_records.unlink()
                _logger.info('Deleted %d old OCR records', len(old_records))