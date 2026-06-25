from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class RejectReasonWizard(models.TransientModel):
    _name = 'reject.reason.wizard'
    _description = 'Reject Reason Wizard'

    reason = fields.Text(string='Rejection Reason', required=True)
    model_name = fields.Char(string='Model Name')
    record_id = fields.Integer(string='Record ID')

    def action_confirm(self):
        if not self.reason:
            raise ValidationError(_("Please enter a rejection reason."))

        if self.model_name == 'car.parking':
            record = self.env['car.parking'].browse(self.record_id)
            if record.exists():
                record.action_execute_reject(self.reason)

        return {'type': 'ir.actions.act_window_close'}
    