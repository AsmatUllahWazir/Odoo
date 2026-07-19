# -*- coding: utf-8 -*-
"""
IoT Webhook Controller - Simulate receiving IoT device data
"""

from odoo import http, fields
from odoo.http import request
from odoo.exceptions import ValidationError
import json
import logging
from datetime import datetime

_logger = logging.getLogger(__name__)


class IoTWebhookController(http.Controller):
    """
    Controller for receiving IoT device webhook data
    Simulates real IoT device integration
    """

    @http.route('/api/iot/webhook', type='json', auth='public', methods=['POST'], csrf=False)
    def iot_webhook_receive(self, **kwargs):
        """
        Receive IoT device data via webhook
        Simulates data from smart locks, sensors, etc.

        Expected payload:
        {
            'device_id': 'DEVICE_ID_OR_NAME',
            'device_type': 'smart_lock|thermostat|sensor_*',
            'property_code': 'PROP001',
            'data': {
                'battery_level': 85,
                'status': 'locked|unlocked',
                'temperature': 72.5,
                'alert': False,
                # Additional sensor data...
            }
        }
        """
        try:
            # Get JSON payload
            payload = kwargs or request.jsonrequest

            _logger.info(f"Received IoT webhook: {json.dumps(payload, indent=2)}")

            # Validate required fields
            required_fields = ['device_id', 'property_code', 'data']
            for field in required_fields:
                if field not in payload:
                    return {'error': f'Missing required field: {field}'}

            # Find property
            property_record = request.env['property.property'].search([
                ('property_code', '=', payload.get('property_code'))
            ], limit=1)

            if not property_record:
                return {'error': f'Property not found: {payload.get("property_code")}'}

            # Find or create IoT device
            device = request.env['property.iot.device'].search([
                ('device_id', '=', payload.get('device_id')),
                ('property_id', '=', property_record.id),
            ], limit=1)

            if not device:
                # Create device if it doesn't exist
                device = request.env['property.iot.device'].create({
                    'device_name': f"{payload.get('device_type', 'Unknown')} - {payload.get('device_id')}",
                    'device_type': payload.get('device_type', 'other'),
                    'device_id': payload.get('device_id'),
                    'property_id': property_record.id,
                    'status': 'online',
                    'last_seen': fields.Datetime.now(),
                })
                _logger.info(f"Created new IoT device: {device.id}")

            # Process the data
            device.action_receive_data(payload.get('data'))

            # Check for specific device types and handle accordingly
            self._handle_device_specific_actions(payload, device)

            return {
                'success': True,
                'message': 'Data processed successfully',
                'device_id': device.id,
                'device_name': device.device_name,
            }

        except ValidationError as e:
            _logger.error(f"IoT webhook validation error: {e}")
            return {'error': str(e)}
        except Exception as e:
            _logger.error(f"IoT webhook error: {e}", exc_info=True)
            return {'error': 'Internal server error'}

    def _handle_device_specific_actions(self, payload, device):
        """Handle actions specific to device types"""
        device_type = payload.get('device_type')
        data = payload.get('data', {})

        if device_type == 'smart_lock':
            # Handle lock/unlock events
            if data.get('status') == 'unlocked':
                # Log the event
                device.message_post(
                    body=f"Smart lock unlocked at {datetime.now()}",
                    message_type='notification'
                )

                # If unauthorized, create alert
                if data.get('method') == 'unauthorized':
                    device._create_alert('security_alert', 'Unauthorized smart lock access')

            elif data.get('status') == 'locked':
                device.message_post(
                    body=f"Smart lock locked at {datetime.now()}",
                    message_type='notification'
                )

        elif device_type == 'sensor_motion' or device_type == 'sensor_door':
            # Handle motion/door sensor events
            if data.get('triggered', False):
                if device_type == 'sensor_door':
                    # Door opened/closed events
                    status = data.get('status', 'opened')
                    device.message_post(
                        body=f"Door {status} at {datetime.now()}",
                        message_type='notification'
                    )

                    # Create security alert if after hours
                    current_hour = datetime.now().hour
                    if current_hour < 6 or current_hour > 22:
                        device._create_alert('security_alert', f'Door {status} after hours')
                else:
                    # Motion detected
                    device.message_post(
                        body=f"Motion detected at {datetime.now()}",
                        message_type='notification'
                    )

        elif device_type == 'sensor_water':
            # Handle water leak detection
            if data.get('leak_detected', False):
                device._create_alert('water_leak', 'Water leak detected')

                # Auto-create maintenance request
                maintenance_vals = {
                    'property_id': device.property_id.id,
                    'title': f"Water leak detected by {device.device_name}",
                    'description': f"Water leak sensor triggered at {datetime.now()}",
                    'category': 'plumbing',
                    'priority': 'emergency',
                    'requestor_id': device.env.user.partner_id.id,
                    'iot_alert': True,
                    'iot_device_id': device.id,
                }
                request.env['property.maintenance.request'].create(maintenance_vals)

        elif device_type in ['sensor_smoke', 'sensor_co2']:
            # Handle safety sensor alerts
            if data.get('alert', False):
                device._create_alert('safety_alert', f'{device.device_type} triggered')

        # Check battery level
        if data.get('battery_level', 100) <= 20:
            device._create_alert('low_battery', f'Battery at {data.get("battery_level")}%')

        # Check for offline devices (simulate)
        if data.get('status') == 'offline':
            device.status = 'offline'
            device._create_alert('offline', 'Device reported offline')

    @http.route('/api/iot/simulate/<string:property_code>', type='json', auth='public', methods=['POST'])
    def simulate_iot_data(self, property_code, **kwargs):
        """
        Simulate IoT data for testing
        Returns random device data
        """
        property_record = request.env['property.property'].search([
            ('property_code', '=', property_code)
        ], limit=1)

        if not property_record:
            return {'error': f'Property not found: {property_code}'}

        import random
        from datetime import datetime, timedelta

        # Generate random device data
        device_types = ['smart_lock', 'thermostat', 'sensor_motion', 'sensor_door',
                        'sensor_water', 'sensor_smoke', 'camera', 'hub']

        simulation_data = {
            'device_id': f'SIM_DEVICE_{random.randint(1000, 9999)}',
            'device_type': random.choice(device_types),
            'property_code': property_code,
            'data': {
                'battery_level': random.randint(10, 100),
                'timestamp': datetime.now().isoformat(),
                'status': random.choice(['online', 'online', 'online', 'offline']),
            }
        }

        # Add device-specific data
        if simulation_data['device_type'] == 'smart_lock':
            simulation_data['data']['status'] = random.choice(['locked', 'unlocked', 'locked', 'locked'])
            simulation_data['data']['method'] = random.choice(['keypad', 'app', 'key', 'unauthorized'])

        elif simulation_data['device_type'] == 'thermostat':
            simulation_data['data']['temperature'] = round(random.uniform(60, 80), 1)
            simulation_data['data']['humidity'] = round(random.uniform(30, 70), 1)

        elif simulation_data['device_type'] == 'sensor_motion':
            simulation_data['data']['triggered'] = random.choice([True, False, False])

        elif simulation_data['device_type'] == 'sensor_door':
            simulation_data['data']['status'] = random.choice(['opened', 'closed', 'closed', 'closed'])
            simulation_data['data']['triggered'] = random.choice([True, False, False])

        elif simulation_data['device_type'] == 'sensor_water':
            simulation_data['data']['leak_detected'] = random.choice([True, False, False])

        elif simulation_data['device_type'] in ['sensor_smoke', 'sensor_co2']:
            simulation_data['data']['alert'] = random.choice([True, False, False])
            simulation_data['data']['level'] = random.randint(0, 100)

        # Add random alerts
        if random.random() < 0.1:  # 10% chance of alert
            simulation_data['data']['alert'] = True

        # Send the webhook
        return self.iot_webhook_receive(**simulation_data)

    @http.route('/api/iot/test', type='http', auth='public', methods=['GET'])
    def iot_test_page(self):
        """Test page for IoT webhook"""
        html = """
        <html>
        <head><title>IoT Webhook Test</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            .container { max-width: 800px; margin: 0 auto; }
            .test-btn { 
                background: #7c7bad; color: white; padding: 10px 20px; 
                border: none; border-radius: 5px; cursor: pointer;
                margin: 5px;
            }
            .test-btn:hover { background: #6a6a91; }
            pre { background: #f5f5f5; padding: 15px; border-radius: 5px; }
            .status { margin: 20px 0; padding: 15px; border-radius: 5px; }
            .success { background: #d4edda; color: #155724; }
            .error { background: #f8d7da; color: #721c24; }
        </style>
        </head>
        <body>
        <div class="container">
            <h1>IoT Webhook Test Simulator</h1>
            <p>Click a button below to simulate IoT data from different device types.</p>

            <div>
                <button class="test-btn" onclick="simulate('smart_lock')">Smart Lock</button>
                <button class="test-btn" onclick="simulate('thermostat')">Thermostat</button>
                <button class="test-btn" onclick="simulate('sensor_motion')">Motion Sensor</button>
                <button class="test-btn" onclick="simulate('sensor_door')">Door Sensor</button>
                <button class="test-btn" onclick="simulate('sensor_water')">Water Leak Sensor</button>
                <button class="test-btn" onclick="simulate('sensor_smoke')">Smoke Detector</button>
                <button class="test-btn" onclick="simulate('camera')">Security Camera</button>
            </div>

            <div id="result"></div>

            <h3>How it works:</h3>
            <ul>
                <li>Each button triggers a webhook with realistic IoT data</li>
                <li>The system processes the data and creates appropriate records</li>
                <li>Alerts and maintenance requests are auto-generated</li>
                <li>All data appears in the property's IoT device list</li>
            </ul>

            <h3>Example Payload:</h3>
            <pre>
{
    "device_id": "LOCK_001",
    "device_type": "smart_lock",
    "property_code": "PROP001",
    "data": {
        "battery_level": 85,
        "status": "unlocked",
        "method": "unauthorized",
        "timestamp": "2024-01-01T12:00:00"
    }
}
            </pre>

            <script>
                function simulate(deviceType) {
                    const resultDiv = document.getElementById('result');
                    resultDiv.innerHTML = '<div class="status">Sending request...</div>';

                    const propertyCode = prompt('Enter Property Code (e.g., PROP001):', 'PROP001');
                    if (!propertyCode) return;

                    fetch('/api/iot/simulate/' + propertyCode, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({ device_type: deviceType }),
                    })
                    .then(response => response.json())
                    .then(data => {
                        if (data.error) {
                            resultDiv.innerHTML = `<div class="status error">❌ Error: ${data.error}</div>`;
                        } else {
                            resultDiv.innerHTML = `<div class="status success">✅ ${data.message || 'Success!'}<br>
                            <pre>${JSON.stringify(data, null, 2)}</pre></div>`;
                        }
                    })
                    .catch(error => {
                        resultDiv.innerHTML = `<div class="status error">❌ Error: ${error.message}</div>`;
                    });
                }
            </script>
        </div>
        </body>
        </html>
        """
        return request.make_response(html)