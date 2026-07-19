# -*- coding: utf-8 -*-
"""
Property IoT Device Model - Smart device management
"""

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta
import json
import logging

_logger = logging.getLogger(__name__)


class PropertyIoTDevice(models.Model):
    """
    Property IoT Device - Smart devices and sensors
    Placeholder for IoT integration
    """
    _name = 'property.iot.device'
    _description = 'IoT Device'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'device_name'
    _rec_name = 'device_name'

    # ==========================================================================
    # Basic Information
    # ==========================================================================

    device_name = fields.Char(
        string='Device Name',
        required=True,
        tracking=True
    )

    device_type = fields.Selection([
        ('smart_lock', 'Smart Lock'),
        ('thermostat', 'Thermostat'),
        ('sensor_motion', 'Motion Sensor'),
        ('sensor_door', 'Door Sensor'),
        ('sensor_window', 'Window Sensor'),
        ('sensor_water', 'Water Leak Sensor'),
        ('sensor_smoke', 'Smoke Detector'),
        ('sensor_co2', 'CO2 Detector'),
        ('camera', 'Security Camera'),
        ('hub', 'Smart Hub'),
        ('other', 'Other'),
    ], string='Device Type', required=True, default='other')

    device_id = fields.Char(
        string='Device ID',
        help='Unique device identifier from manufacturer'
    )

    property_id = fields.Many2one(
        'property.property',
        string='Property',
        required=True,
        ondelete='cascade'
    )

    unit_id = fields.Many2one(
        'property.unit',
        string='Unit',
        help='Specific unit where device is installed'
    )

    # ==========================================================================
    # Status
    # ==========================================================================

    status = fields.Selection([
        ('online', 'Online'),
        ('offline', 'Offline'),
        ('maintenance', 'Maintenance'),
        ('error', 'Error'),
        ('inactive', 'Inactive'),
    ], string='Status', required=True, default='offline', tracking=True)

    battery_level = fields.Integer(
        string='Battery Level (%)',
        default=100,
        help='Battery level percentage (0-100)'
    )

    last_seen = fields.Datetime(
        string='Last Seen',
        help='Last time device communicated'
    )

    has_alert = fields.Boolean(
        string='Has Alert',
        default=False,
        help='Whether device has an active alert'
    )

    # ==========================================================================
    # Location
    # ==========================================================================

    location_description = fields.Char(
        string='Location Description',
        help='Description of device location (e.g., "Front Door")'
    )

    floor = fields.Integer(
        string='Floor',
        help='Floor where device is located'
    )

    room = fields.Char(
        string='Room',
        help='Room where device is located'
    )

    # ==========================================================================
    # Technical
    # ==========================================================================

    manufacturer = fields.Char(
        string='Manufacturer'
    )

    model = fields.Char(
        string='Model'
    )

    firmware_version = fields.Char(
        string='Firmware Version'
    )

    installation_date = fields.Date(
        string='Installation Date'
    )

    last_maintenance_date = fields.Date(
        string='Last Maintenance Date'
    )

    # ==========================================================================
    # Data
    # ==========================================================================

    last_data = fields.Json(
        string='Last Data',
        help='Last data received from device'
    )

    alert_ids = fields.One2many(
        'property.iot.alert',
        'device_id',
        string='Alerts',
        help='Alert history for this device'
    )

    # ==========================================================================
    # Computed Fields
    # ==========================================================================

    device_status_color = fields.Char(
        string='Status Color',
        compute='_compute_status_color'
    )

    @api.depends('status')
    def _compute_status_color(self):
        """Compute status color for UI"""
        colors = {
            'online': 'success',
            'offline': 'danger',
            'maintenance': 'warning',
            'error': 'danger',
            'inactive': 'secondary',
        }
        for record in self:
            record.device_status_color = colors.get(record.status, 'secondary')

    # ==========================================================================
    # Constraints
    # ==========================================================================

    @api.constrains('battery_level')
    def _check_battery_level(self):
        """Validate battery level"""
        for record in self:
            if record.battery_level and (record.battery_level < 0 or record.battery_level > 100):
                raise ValidationError(
                    _("Battery level must be between 0 and 100.")
                )

    # ==========================================================================
    # Business Methods
    # ==========================================================================

    def action_receive_data(self, data):
        """Receive data from IoT device (webhook)"""
        self.ensure_one()
        self.last_data = data
        self.last_seen = fields.Datetime.now()
        self.status = 'online'

        # Process data and check for alerts
        self._process_device_data(data)

        return True

    def _process_device_data(self, data):
        """Process device data for alerts"""
        self.ensure_one()

        # Check for low battery
        if data.get('battery_level', 0) <= 20:
            self._create_alert('low_battery', f"Battery level at {data.get('battery_level')}%")

        # Check for security events
        if self.device_type == 'smart_lock':
            if data.get('event') == 'unauthorized_access':
                self._create_alert('security_alert', 'Unauthorized access attempt detected')

        # Check for environmental issues
        if self.device_type in ['sensor_smoke', 'sensor_co2']:
            if data.get('alert', False):
                self._create_alert('safety_alert', 'Safety alert triggered')

        # Check for water leak
        if self.device_type == 'sensor_water':
            if data.get('leak_detected', False):
                self._create_alert('water_leak', 'Water leak detected')

    def _create_alert(self, alert_type, description):
        """Create an alert for the device"""
        self.ensure_one()

        # Create maintenance request if needed
        if alert_type in ['security_alert', 'safety_alert', 'water_leak']:
            maintenance_vals = {
                'property_id': self.property_id.id,
                'title': f"IoT Alert: {self.device_name} - {description}",
                'description': f"Alert type: {alert_type}\nDevice: {self.device_name}\nDescription: {description}",
                'category': 'iot',
                'priority': 'high',
                'requestor_id': self.env.user.partner_id.id,
                'iot_alert': True,
                'iot_device_id': self.id,
                'iot_data': json.dumps({'alert_type': alert_type}),
            }
            self.env['property.maintenance.request'].create(maintenance_vals)

        # Create alert record
        alert_vals = {
            'device_id': self.id,
            'alert_type': alert_type,
            'description': description,
            'status': 'active',
        }
        self.env['property.iot.alert'].create(alert_vals)
        self.has_alert = True

    def action_clear_alert(self):
        """Clear active alert"""
        for record in self:
            active_alerts = record.alert_ids.filtered(lambda a: a.status == 'active')
            for alert in active_alerts:
                alert.action_resolve()
            record.has_alert = False

    @api.model
    def _cron_check_offline_devices(self):
        """Cron job to check for offline devices"""
        timeout_threshold = timedelta(hours=24)
        cutoff_time = fields.Datetime.now() - timeout_threshold

        offline = self.search([
            ('status', '=', 'online'),
            ('last_seen', '<', cutoff_time)
        ])

        for device in offline:
            device.status = 'offline'
            device._create_alert(
                'offline',
                f"Device has been offline for more than 24 hours"
            )


class PropertyIoTAlert(models.Model):
    """
    IoT Device Alert - Alert history
    """
    _name = 'property.iot.alert'
    _description = 'IoT Device Alert'
    _order = 'create_date desc'
    _rec_name = 'display_name'

    display_name = fields.Char(
        string='Display Name',
        compute='_compute_display_name',
        store=True
    )

    device_id = fields.Many2one(
        'property.iot.device',
        string='Device',
        required=True,
        ondelete='cascade'
    )

    property_id = fields.Many2one(
        'property.property',
        string='Property',
        related='device_id.property_id',
        store=True
    )

    alert_type = fields.Selection([
        ('low_battery', 'Low Battery'),
        ('offline', 'Device Offline'),
        ('security_alert', 'Security Alert'),
        ('safety_alert', 'Safety Alert'),
        ('water_leak', 'Water Leak'),
        ('maintenance_required', 'Maintenance Required'),
        ('unknown', 'Unknown'),
    ], string='Alert Type', required=True)

    description = fields.Text(
        string='Description',
        required=True
    )

    status = fields.Selection([
        ('active', 'Active'),
        ('acknowledged', 'Acknowledged'),
        ('resolved', 'Resolved'),
    ], string='Status', required=True, default='active')

    acknowledged_date = fields.Datetime(
        string='Acknowledged Date'
    )

    resolved_date = fields.Datetime(
        string='Resolved Date'
    )

    resolved_by = fields.Many2one(
        'res.users',
        string='Resolved By'
    )

    notes = fields.Text(
        string='Notes'
    )

    @api.depends('alert_type', 'device_id')
    def _compute_display_name(self):
        """Compute display name"""
        for record in self:
            device_name = record.device_id.device_name if record.device_id else ''
            record.display_name = f"{record.alert_type} - {device_name}"

    def action_acknowledge(self):
        """Acknowledge the alert"""
        for record in self:
            if record.status != 'active':
                continue
            record.status = 'acknowledged'
            record.acknowledged_date = fields.Datetime.now()

    def action_resolve(self):
        """Resolve the alert"""
        for record in self:
            if record.status == 'resolved':
                continue
            record.status = 'resolved'
            record.resolved_date = fields.Datetime.now()
            record.resolved_by = self.env.user
            