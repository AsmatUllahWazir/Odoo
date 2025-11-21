from odoo import models, fields
from odoo.exceptions import UserError


class ZakatCertificateWizard(models.TransientModel):
    _name = 'zakat.certificate.wizard'
    _description = 'Generate Zakat Certificate'

    calculation_id = fields.Many2one('zakat.calculation', required=True)
    recipient_name = fields.Char(string='Recipient Name')
    notes = fields.Text(string='Additional Notes')

    def action_generate_certificate(self):
        self.ensure_one()
        if not self.calculation_id.zakat_due:
            raise UserError("No Zakat due for certificate.")

        cert = self.env['zakat.certificate'].create({
            'calculation_id': self.calculation_id.id,
            'recipient_name': self.recipient_name or self.calculation_id.partner_id.name,
            'amount_paid': self.calculation_id.zakat_due,
            'notes': self.notes,
        })

        return cert._print_certificate()
