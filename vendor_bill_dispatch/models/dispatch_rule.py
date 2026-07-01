# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import re


class DispatchRule(models.Model):
    _name = 'vendor.bill.dispatch.rule'
    _description = 'Vendor Bill Dispatch Rule'
    _order = 'priority, sequence, id'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Rule Name', required=True, tracking=True)
    active = fields.Boolean(default=True, tracking=True)
    sequence = fields.Integer(string='Sequence', default=10, help='Lower numbers = higher priority')
    priority = fields.Integer(string='Priority', default=50, help='Rule execution priority (lower = first)')

    # Target Company
    target_company_id = fields.Many2one(
        'res.company',
        string='Target Company',
        required=True,
        help='Company to which the bill will be dispatched if this rule matches',
        tracking=True,
    )

    # Rule Type
    rule_type = fields.Selection([
        ('vendor_name', 'Vendor Name'),
        ('vendor_vat', 'Vendor VAT/Tax ID'),
        ('vendor_country', 'Vendor Country'),
        ('iban', 'IBAN'),
        ('currency', 'Currency'),
        ('amount_range', 'Amount Range'),
        ('keyword', 'OCR Keywords'),
        ('partner_id', 'Specific Partner'),
        ('domain', 'Advanced Domain Filter'),
    ], string='Rule Type', required=True, tracking=True)

    # Criteria Fields
    vendor_name_pattern = fields.Char(
        string='Vendor Name Pattern',
        help='Text pattern to match in vendor name (case-insensitive, supports wildcards: * and ?)',
    )

    vendor_vat_pattern = fields.Char(
        string='VAT/Tax ID Pattern',
        help='Pattern to match in VAT number (e.g., BE*, FR*, etc.)',
    )

    vendor_country_ids = fields.Many2many(
        'res.country',
        string='Vendor Countries',
        help='Countries to match',
    )

    iban_pattern = fields.Char(
        string='IBAN Pattern',
        help='IBAN pattern to match (e.g., BE*, FR76*, etc.)',
    )

    currency_ids = fields.Many2many(
        'res.currency',
        string='Currencies',
        help='Currencies to match',
    )

    amount_min = fields.Monetary(
        string='Minimum Amount',
        currency_field='currency_id',
        help='Minimum invoice amount (inclusive)',
    )

    amount_max = fields.Monetary(
        string='Maximum Amount',
        currency_field='currency_id',
        help='Maximum invoice amount (inclusive)',
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
    )

    keyword_list = fields.Text(
        string='Keywords (one per line)',
        help='Keywords to search in OCR text (one per line, case-insensitive)',
    )

    keyword_match_type = fields.Selection([
        ('any', 'Match Any Keyword'),
        ('all', 'Match All Keywords'),
    ], string='Keyword Match Type', default='any')

    partner_ids = fields.Many2many(
        'res.partner',
        string='Specific Partners',
        help='Match specific vendor partners',
    )

    domain_filter = fields.Text(
        string='Domain Filter',
        help='Advanced Odoo domain filter (for experts)',
        default='[]',
    )

    # Additional Conditions
    require_manual_confirmation = fields.Boolean(
        string='Require Manual Confirmation',
        default=False,
        help='Even if rule matches, ask user to confirm',
    )

    stop_on_match = fields.Boolean(
        string='Stop on Match',
        default=True,
        help='Stop evaluating other rules if this one matches',
    )

    # Statistics
    match_count = fields.Integer(
        string='Matches',
        default=0,
        readonly=True,
        help='Number of times this rule has matched',
    )

    last_match_date = fields.Datetime(
        string='Last Match',
        readonly=True,
    )

    # Description
    description = fields.Text(string='Description')

    @api.constrains('amount_min', 'amount_max')
    def _check_amount_range(self):
        for rule in self:
            if rule.amount_min and rule.amount_max and rule.amount_min > rule.amount_max:
                raise ValidationError(_('Minimum amount cannot be greater than maximum amount.'))

    @api.constrains('domain_filter')
    def _check_domain_filter(self):
        for rule in self:
            if rule.rule_type == 'domain' and rule.domain_filter:
                try:
                    eval(rule.domain_filter)
                except Exception as e:
                    raise ValidationError(_('Invalid domain filter syntax: %s') % str(e))

    def _match_pattern(self, text, pattern):
        """Match text against pattern (supports * and ? wildcards)"""
        if not text or not pattern:
            return False

        regex_pattern = re.escape(pattern)
        regex_pattern = regex_pattern.replace(r'\*', '.*').replace(r'\?', '.')
        regex_pattern = f'^{regex_pattern}$'

        return bool(re.match(regex_pattern, text, re.IGNORECASE))

    def _match_keywords(self, ocr_text):
        """Check if OCR text matches keyword criteria"""
        if not self.keyword_list or not ocr_text:
            return False

        keywords = [k.strip() for k in self.keyword_list.split('\n') if k.strip()]
        ocr_text_lower = ocr_text.lower()

        if self.keyword_match_type == 'any':
            return any(keyword.lower() in ocr_text_lower for keyword in keywords)
        else:
            return all(keyword.lower() in ocr_text_lower for keyword in keywords)

    def match_invoice(self, invoice):
        """Check if this rule matches the given invoice"""
        self.ensure_one()

        if not self.active:
            return False

        ocr_result = invoice.ocr_result_id

        if self.rule_type == 'vendor_name':
            if not invoice.partner_id or not invoice.partner_id.name:
                return False
            return self._match_pattern(invoice.partner_id.name, self.vendor_name_pattern)

        elif self.rule_type == 'vendor_vat':
            if not invoice.partner_id or not invoice.partner_id.vat:
                return False
            return self._match_pattern(invoice.partner_id.vat, self.vendor_vat_pattern)

        elif self.rule_type == 'vendor_country':
            if not invoice.partner_id or not invoice.partner_id.country_id:
                return False
            return invoice.partner_id.country_id in self.vendor_country_ids

        elif self.rule_type == 'iban':
            if not invoice.partner_id:
                return False
            partner_banks = invoice.partner_id.bank_ids
            if not partner_banks:
                return False
            return any(
                self._match_pattern(bank.acc_number, self.iban_pattern)
                for bank in partner_banks if bank.acc_number
            )

        elif self.rule_type == 'currency':
            return invoice.currency_id in self.currency_ids

        elif self.rule_type == 'amount_range':
            amount = invoice.amount_total
            if self.amount_min and amount < self.amount_min:
                return False
            if self.amount_max and amount > self.amount_max:
                return False
            return True

        elif self.rule_type == 'keyword':
            if not ocr_result or not ocr_result.full_text:
                return False
            return self._match_keywords(ocr_result.full_text)

        elif self.rule_type == 'partner_id':
            return invoice.partner_id in self.partner_ids

        elif self.rule_type == 'domain':
            try:
                domain = eval(self.domain_filter)
                domain.append(('id', '=', invoice.id))
                matching = self.env['account.move'].search(domain)
                return bool(matching)
            except Exception:
                return False

        return False

    def action_test_rule(self):
        """Test this rule against recent invoices"""
        self.ensure_one()

        recent_invoices = self.env['account.move'].search([
            ('move_type', '=', 'in_invoice'),
            ('dispatch_state', 'in', ['ocr_draft', 'routed']),
        ], limit=50)

        matching_invoices = recent_invoices.filtered(lambda inv: self.match_invoice(inv))

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Rule Test Results'),
                'message': _('This rule matches %d out of %d recent invoices.') % (
                    len(matching_invoices),
                    len(recent_invoices)
                ),
                'type': 'info',
                'sticky': True,
            }
        }

    def increment_match_count(self):
        """Increment match counter when rule is used"""
        self.ensure_one()
        self.sudo().write({
            'match_count': self.match_count + 1,
            'last_match_date': fields.Datetime.now(),
        })