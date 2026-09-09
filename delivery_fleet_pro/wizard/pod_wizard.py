from odoo import api, fields, models, _
from odoo.exceptions import UserError


class DeliveryPodWizard(models.TransientModel):
    _name = "delivery.pod.wizard"
    _description = "Capture Proof of Delivery"

    route_line_id = fields.Many2one("delivery.route.line", required=True)
    recipient_name = fields.Char(required=True)
    recipient_phone = fields.Char()
    recipient_relation = fields.Char()
    signature = fields.Image(attachment=True)
    photo = fields.Image(attachment=True)
    photo_2 = fields.Image(attachment=True)
    photo_3 = fields.Image(attachment=True)
    otp = fields.Char()
    otp_verified = fields.Boolean(readonly=True)
    latitude = fields.Float(digits=(10, 7))
    longitude = fields.Float(digits=(10, 7))
    accuracy_meters = fields.Float()
    notes = fields.Text()
    generate_otp = fields.Boolean()

    def action_save(self):
        self.ensure_one()
        line = self.route_line_id
        proof = line.proof_id
        if not proof:
            proof = self.env["delivery.proof"].create({"route_line_id": line.id})
        proof.write({
            "recipient_name": self.recipient_name,
            "recipient_phone": self.recipient_phone,
            "recipient_relation": self.recipient_relation,
            "signature": self.signature,
            "photo": self.photo,
            "photo_2": self.photo_2,
            "photo_3": self.photo_3,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "accuracy_meters": self.accuracy_meters,
            "notes": self.notes,
        })
        if self.generate_otp:
            proof.action_generate_otp()
        if self.otp:
            proof.action_verify_otp(self.otp)
        proof.action_verify()
        line.action_mark_delivered()
        return True
