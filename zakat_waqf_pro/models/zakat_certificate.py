from odoo import models, fields


class ZakatCertificate(models.Model):
    _name = 'zakat.certificate'
    _description = 'Zakat Certificate'

    name = fields.Char(string='Certificate No.', default=lambda self: self.env['ir.sequence'].next_by_code('zakat.certificate'))
    calculation_id = fields.Many2one('zakat.calculation')
    recipient_name = fields.Char(string='Recipient')
    amount_paid = fields.Monetary(string='Zakat Paid')
    issue_date = fields.Date(default=fields.Date.today)
    qr_code = fields.Char(string='QR Data')
    notes = fields.Text()
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)
    state = fields.Selection([('draft', 'Draft'), ('issued', 'Issued')], default='draft')

    def _print_certificate(self):
        return self.env.ref('zakat_waqf_pro.zakat_certificate_report_action').report_action(self)