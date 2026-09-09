import secrets
from datetime import timedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class DeliveryProof(models.Model):
    _name = "delivery.proof"
    _description = "Proof of Delivery"
    _inherit = ["mail.thread"]
    _order = "signed_at desc, id desc"

    name = fields.Char(required=True, copy=False, default="POD")
    company_id = fields.Many2one("res.company", related="route_line_id.route_id.company_id", store=True)
    route_line_id = fields.Many2one("delivery.route.line", required=True, ondelete="cascade", index=True)
    route_id = fields.Many2one("delivery.route", related="route_line_id.route_id", store=True)
    picking_id = fields.Many2one("stock.picking", related="route_line_id.picking_id", store=True)
    partner_id = fields.Many2one("res.partner", related="route_line_id.partner_id", store=True)
    signature = fields.Image(attachment=True, max_width=1600, max_height=1200)
    photo = fields.Image(attachment=True, max_width=2400, max_height=1800)
    photo_2 = fields.Image(attachment=True, max_width=2400, max_height=1800)
    photo_3 = fields.Image(attachment=True, max_width=2400, max_height=1800)
    recipient_name = fields.Char()
    recipient_phone = fields.Char()
    recipient_relation = fields.Char()
    otp = fields.Char(copy=False)
    otp_hash = fields.Char(copy=False)
    otp_generated_at = fields.Datetime(copy=False)
    otp_expires_at = fields.Datetime(copy=False)
    otp_verified = fields.Boolean(copy=False)
    otp_verified_at = fields.Datetime(copy=False)
    notes = fields.Text()
    latitude = fields.Float(digits=(10, 7))
    longitude = fields.Float(digits=(10, 7))
    accuracy_meters = fields.Float()
    captured_at = fields.Datetime(default=fields.Datetime.now)
    signed_at = fields.Datetime()
    status = fields.Selection(
        [("draft", "Draft"), ("verified", "Verified"), ("rejected", "Rejected")],
        default="draft",
        tracking=True,
    )
    driver_id = fields.Many2one("hr.employee", related="route_line_id.route_id.driver_id", store=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "POD") == "POD":
                vals["name"] = self.env["ir.sequence"].next_by_code("delivery.proof") or "POD"
        return super().create(vals_list)

    def action_generate_otp(self):
        for proof in self:
            config = self.env["delivery.config"].sudo().get_company_config(proof.company_id)
            otp = "".join(str(secrets.randbelow(10)) for _ in range(config.otp_length))
            proof.write({
                "otp": otp,
                "otp_hash": proof._hash_otp(otp),
                "otp_generated_at": fields.Datetime.now(),
                "otp_expires_at": fields.Datetime.now() + timedelta(minutes=config.otp_expiry_minutes),
                "otp_verified": False,
            })
        return True

    def _hash_otp(self, value):
        import hashlib
        self.ensure_one()
        return hashlib.sha256((value + (self.company_id.name or "")).encode()).hexdigest()

    def action_verify_otp(self, code):
        self.ensure_one()
        if not self.otp_hash or not self.otp_expires_at:
            raise UserError(_("No active OTP exists for this POD."))
        if fields.Datetime.now() > self.otp_expires_at:
            raise UserError(_("The OTP has expired."))
        if self._hash_otp(code or "") != self.otp_hash:
            raise UserError(_("The OTP is incorrect."))
        self.write({"otp_verified": True, "otp_verified_at": fields.Datetime.now()})
        return True

    def action_verify(self):
        for proof in self:
            if not proof.signature and proof.route_line_id.route_id.service_type_id.requires_signature:
                raise ValidationError(_("A signature is required."))
            if proof.route_line_id.route_id.service_type_id.requires_photo and not proof.photo:
                raise ValidationError(_("A photo is required."))
            if proof.route_line_id.route_id.service_type_id.requires_otp and not proof.otp_verified:
                raise ValidationError(_("OTP verification is required."))
            proof.write({"status": "verified", "signed_at": proof.signed_at or fields.Datetime.now()})
            proof.route_line_id.write({"proof_id": proof.id})
            self.env["delivery.event"].log_event("pod", route=proof.route_id, line=proof.route_line_id, source="driver")
        return True

    def action_reject(self):
        self.write({"status": "rejected"})
        return True

    def action_print(self):
        return self.env.ref("delivery_fleet_pro.action_report_delivery_pod").report_action(self)
