from datetime import timedelta
from odoo import fields
from odoo.exceptions import ValidationError, UserError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestDeliveryRoute(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.warehouse = cls.env["stock.warehouse"].search([("company_id", "=", cls.company.id)], limit=1)
        cls.partner = cls.env["res.partner"].create({
            "name": "Delivery Test Customer",
            "email": "delivery-test@example.com",
            "delivery_latitude": 24.7136,
            "delivery_longitude": 46.6753,
            "delivery_preferred_from": 9.0,
            "delivery_preferred_to": 17.0,
        })
        cls.vehicle = cls.env["fleet.vehicle"].create({
            "name": "Delivery Test Vehicle",
            "company_id": cls.company.id,
            "delivery_capacity_weight": 1000,
            "delivery_capacity_volume": 10,
            "delivery_status": "available",
        })
        cls.driver = cls.env["hr.employee"].create({
            "name": "Delivery Test Driver",
            "company_id": cls.company.id,
            "delivery_available": True,
            "delivery_license_number": "TEST-001",
            "delivery_max_hours": 8,
        })
        cls.service = cls.env["delivery.service.type"].search([], limit=1)
        cls.failure = cls.env["delivery.failure"].search([], limit=1)

    def _create_picking(self):
        picking_type = self.env["stock.picking.type"].search(
            [("warehouse_id", "=", self.warehouse.id), ("code", "=", "outgoing")], limit=1
        )
        return self.env["stock.picking"].create({
            "partner_id": self.partner.id,
            "picking_type_id": picking_type.id,
            "location_id": picking_type.default_location_src_id.id,
            "location_dest_id": self.env.ref("stock.stock_location_customers").id,
        })

    def test_route_create_has_sequence(self):
        route = self.env["delivery.route"].create({"warehouse_id": self.warehouse.id})
        self.assertTrue(route.name)
        self.assertTrue(route.tracking_token)
        self.assertEqual(route.state, "draft")

    def test_route_company_validation(self):
        route = self.env["delivery.route"].create({"warehouse_id": self.warehouse.id})
        self.assertEqual(route.company_id, self.company)

    def test_route_requires_stop_to_plan(self):
        route = self.env["delivery.route"].create({
            "warehouse_id": self.warehouse.id,
            "vehicle_id": self.vehicle.id,
            "driver_id": self.driver.id,
        })
        with self.assertRaises(UserError):
            route.action_plan()

    def test_route_plan_requires_driver(self):
        picking = self._create_picking()
        route = self.env["delivery.route"].create({"warehouse_id": self.warehouse.id, "vehicle_id": self.vehicle.id})
        self.env["delivery.route.line"].create({"route_id": route.id, "picking_id": picking.id})
        with self.assertRaises(ValidationError):
            route.action_plan()

    def test_route_plan(self):
        picking = self._create_picking()
        route = self.env["delivery.route"].create({
            "warehouse_id": self.warehouse.id,
            "vehicle_id": self.vehicle.id,
            "driver_id": self.driver.id,
            "service_type_id": self.service.id,
        })
        line = self.env["delivery.route.line"].create({"route_id": route.id, "picking_id": picking.id, "weight": 10})
        route.action_plan()
        self.assertEqual(route.state, "planned")
        self.assertEqual(route.stop_count, 1)
        self.assertEqual(route.total_weight, 10)
        self.assertEqual(line.status, "pending")

    def test_capacity_validation(self):
        picking = self._create_picking()
        route = self.env["delivery.route"].create({
            "warehouse_id": self.warehouse.id,
            "vehicle_id": self.vehicle.id,
            "driver_id": self.driver.id,
        })
        self.env["delivery.route.line"].create({"route_id": route.id, "picking_id": picking.id, "weight": 1001})
        with self.assertRaises(ValidationError):
            route.action_plan()

    def test_dispatch_workflow(self):
        picking = self._create_picking()
        route = self.env["delivery.route"].create({
            "warehouse_id": self.warehouse.id,
            "vehicle_id": self.vehicle.id,
            "driver_id": self.driver.id,
        })
        line = self.env["delivery.route.line"].create({"route_id": route.id, "picking_id": picking.id})
        route.action_plan()
        route.action_dispatch()
        self.assertEqual(route.state, "dispatched")
        self.assertEqual(line.status, "assigned")
        self.assertEqual(self.vehicle.delivery_status, "assigned")

    def test_start_workflow(self):
        picking = self._create_picking()
        route = self.env["delivery.route"].create({
            "warehouse_id": self.warehouse.id,
            "vehicle_id": self.vehicle.id,
            "driver_id": self.driver.id,
        })
        line = self.env["delivery.route.line"].create({"route_id": route.id, "picking_id": picking.id})
        route.action_plan()
        route.action_dispatch()
        route.action_start()
        self.assertEqual(route.state, "in_transit")
        self.assertEqual(line.status, "in_transit")
        self.assertEqual(self.vehicle.delivery_status, "in_transit")

    def test_failure_creates_retry(self):
        picking = self._create_picking()
        route = self.env["delivery.route"].create({
            "warehouse_id": self.warehouse.id,
            "vehicle_id": self.vehicle.id,
            "driver_id": self.driver.id,
        })
        line = self.env["delivery.route.line"].create({"route_id": route.id, "picking_id": picking.id})
        route.action_plan()
        route.action_dispatch()
        wizard = self.env["delivery.failure.wizard"].with_context(default_route_line_id=line.id).create({
            "route_line_id": line.id,
            "reason_id": self.failure.id,
            "create_retry": True,
        })
        wizard.action_confirm()
        self.assertEqual(line.status, "failed")
        self.assertTrue(self.env["delivery.retry"].search([("original_line_id", "=", line.id)]))

    def test_tracking_link(self):
        picking = self._create_picking()
        route = self.env["delivery.route"].create({"warehouse_id": self.warehouse.id, "vehicle_id": self.vehicle.id, "driver_id": self.driver.id})
        line = self.env["delivery.route.line"].create({"route_id": route.id, "picking_id": picking.id})
        line.action_create_tracking_link()
        self.assertTrue(line.tracking_link_id.token)
        self.assertEqual(line.tracking_link_id.partner_id, self.partner)

    def test_segment_building(self):
        picking1 = self._create_picking()
        picking2 = self._create_picking()
        route = self.env["delivery.route"].create({"warehouse_id": self.warehouse.id, "vehicle_id": self.vehicle.id, "driver_id": self.driver.id})
        self.env["delivery.route.line"].create({"route_id": route.id, "picking_id": picking1.id, "sequence": 10, "latitude": 24.70, "longitude": 46.67})
        self.env["delivery.route.line"].create({"route_id": route.id, "picking_id": picking2.id, "sequence": 20, "latitude": 24.72, "longitude": 46.69})
        route.action_build_segments()
        self.assertEqual(len(route.segment_ids), 1)

    def test_cost_creation(self):
        picking = self._create_picking()
        route = self.env["delivery.route"].create({"warehouse_id": self.warehouse.id, "vehicle_id": self.vehicle.id, "driver_id": self.driver.id, "estimated_distance": 100, "estimated_duration": 2})
        self.env["delivery.route.line"].create({"route_id": route.id, "picking_id": picking.id})
        route._create_default_costs()
        self.assertTrue(route.cost_line_ids)

    def test_window_constraint(self):
        picking = self._create_picking()
        route = self.env["delivery.route"].create({"warehouse_id": self.warehouse.id, "vehicle_id": self.vehicle.id, "driver_id": self.driver.id})
        with self.assertRaises(ValidationError):
            self.env["delivery.route.line"].create({
                "route_id": route.id,
                "picking_id": picking.id,
                "date_from": fields.Datetime.now() + timedelta(hours=2),
                "date_to": fields.Datetime.now(),
            })
