from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import UserError, ValidationError


@tagged("post_install", "-at_install")
class TestDeliveryPOD(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.warehouse = cls.env["stock.warehouse"].search([("company_id", "=", cls.company.id)], limit=1)
        cls.partner = cls.env["res.partner"].create({"name": "POD Customer", "email": "pod@example.com"})
        cls.vehicle = cls.env["fleet.vehicle"].create({"name": "POD Vehicle", "company_id": cls.company.id, "delivery_status": "available"})
        cls.driver = cls.env["hr.employee"].create({"name": "POD Driver", "company_id": cls.company.id, "delivery_available": True, "delivery_license_number": "POD-1"})
        cls.service = cls.env["delivery.service.type"].create({"name": "POD Service", "code": "POD_TEST", "requires_signature": True, "requires_photo": False, "requires_otp": False})

    def _line(self):
        picking_type = self.env["stock.picking.type"].search([("warehouse_id", "=", self.warehouse.id), ("code", "=", "outgoing")], limit=1)
        picking = self.env["stock.picking"].create({"partner_id": self.partner.id, "picking_type_id": picking_type.id, "location_id": picking_type.default_location_src_id.id, "location_dest_id": self.env.ref("stock.stock_location_customers").id})
        route = self.env["delivery.route"].create({"warehouse_id": self.warehouse.id, "vehicle_id": self.vehicle.id, "driver_id": self.driver.id, "service_type_id": self.service.id})
        return self.env["delivery.route.line"].create({"route_id": route.id, "picking_id": picking.id})

    def test_pod_sequence(self):
        line = self._line()
        pod = self.env["delivery.proof"].create({"route_line_id": line.id})
        self.assertTrue(pod.name)

    def test_otp_requires_generation(self):
        line = self._line()
        pod = self.env["delivery.proof"].create({"route_line_id": line.id})
        with self.assertRaises(UserError):
            pod.action_verify_otp("123456")

    def test_pod_signature_requirement(self):
        line = self._line()
        pod = self.env["delivery.proof"].create({"route_line_id": line.id})
        with self.assertRaises(ValidationError):
            pod.action_verify()
