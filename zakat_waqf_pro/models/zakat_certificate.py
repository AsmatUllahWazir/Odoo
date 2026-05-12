# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import qrcode
import base64
from io import BytesIO


class ZakatCertificate(models.Model):
    _name = 'zakat.certificate'
    _description = 'Zakat Certificate'
    _rec_name = 'name'
    _order = 'issue_date desc, id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        string='Certificate No.',
        default=lambda self: self.env['ir.sequence'].next_by_code('zakat.certificate'),
        readonly=True,
        copy=False,
        required=True
    )

    calculation_id = fields.Many2one(
        'zakat.calculation',
        string='Zakat Calculation',
        required=True,
        ondelete='cascade'
    )

    partner_id = fields.Many2one(
        'res.partner',
        related='calculation_id.partner_id',
        string='Partner',
        store=True
    )

    recipient_name = fields.Char(
        string='Recipient Name',
        required=True
    )

    amount_paid = fields.Monetary(
        string='Zakat Paid',
        required=True
    )

    issue_date = fields.Date(
        default=fields.Date.today,
        string='Issue Date',
        required=True
    )

    hijri_issue_date = fields.Char(
        string='Hijri Date',
        compute='_compute_hijri_date'
    )

    qr_code = fields.Binary(
        string='QR Code',
        compute='_generate_qr_code',
        attachment=True
    )

    notes = fields.Text(string='Notes')

    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company,
        string='Company'
    )

    currency_id = fields.Many2one(
        'res.currency',
        related='company_id.currency_id',
        readonly=True
    )

    state = fields.Selection([
        ('draft', 'Draft'),
        ('issued', 'Issued'),
        ('cancelled', 'Cancelled'),
    ], default='issued', string='Status')

    authorized_signature = fields.Binary(
        string='Authorized Signature',
        related='company_id.partner_id.image_1920'
    )

    company_logo = fields.Binary(
        string='Company Logo',
        related='company_id.logo'
    )

    @api.depends('issue_date')
    def _compute_hijri_date(self):
        for rec in self:
            if rec.issue_date:
                try:
                    from hijri_converter import Hijri, Gregorian
                    hijri = Gregorian(rec.issue_date.year, rec.issue_date.month, rec.issue_date.day).to_hijri()
                    rec.hijri_issue_date = f"{hijri.year}/{hijri.month:02d}/{hijri.day:02d}"
                except ImportError:
                    rec.hijri_issue_date = rec.issue_date.strftime("%Y/%m/%d")
            else:
                rec.hijri_issue_date = False

    @api.depends('name', 'recipient_name', 'amount_paid', 'issue_date')
    def _generate_qr_code(self):
        """Generate QR code containing certificate verification data"""
        for rec in self:
            if rec.name and rec.recipient_name:
                verification_data = f"""
                Certificate: {rec.name}
                Recipient: {rec.recipient_name}
                Amount: {rec.amount_paid} {rec.currency_id.symbol or 'SAR'}
                Date: {rec.issue_date}
                """
                qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=4, border=2)
                qr.add_data(verification_data.strip())
                qr.make(fit=True)
                qr_image = qr.make_image(fill_color="#b8860b", back_color="white")
                buffer = BytesIO()
                qr_image.save(buffer, format='PNG')
                rec.qr_code = base64.b64encode(buffer.getvalue())
            else:
                rec.qr_code = False

    def action_print_certificate(self):
        """Print the certificate"""
        self.ensure_one()
        return self.env.ref('zakat_waqf_pro.zakat_certificate_report_action').report_action(self)

    def action_send_by_email(self):
        """Send certificate via email"""
        self.ensure_one()
        template = self.env.ref('zakat_waqf_pro.email_zakat_certificate_template', raise_if_not_found=False)
        if template:
            template.send_mail(self.id, force_send=True)
        return True

    def action_cancel_certificate(self):
        """Cancel certificate"""
        for rec in self:
            rec.state = 'cancelled'
