/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

/**
 * IoT Device Management Widget
 * Displays and controls IoT devices for a property
 */
export class IoTDeviceWidget extends Component {
    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.action = useService("action");

        this.state = useState({
            devices: [],
            loading: true,
            selectedDevice: null,
            showAlertDetails: false,
        });

        this.props = {
            propertyId: this.props.propertyId || false,
        };
    }

    async willStart() {
        await this.loadDevices();
    }

    async loadDevices() {
        this.state.loading = true;
        try {
            const domain = this.props.propertyId
                ? [["property_id", "=", this.props.propertyId]]
                : [];

            const devices = await this.orm.searchRead(
                "property.iot.device",
                domain,
                [
                    "id",
                    "device_name",
                    "device_type",
                    "status",
                    "battery_level",
                    "last_seen",
                    "has_alert",
                    "location_description",
                    "device_id",
                ],
                { order: "device_name asc" }
            );

            this.state.devices = devices;
        } catch (error) {
            console.error("Error loading IoT devices:", error);
            this.notification.add("Failed to load IoT devices", {
                type: "danger",
            });
        } finally {
            this.state.loading = false;
        }
    }

    getStatusIcon(status) {
        const icons = {
            online: "fa-wifi text-success",
            offline: "fa-wifi text-danger",
            maintenance: "fa-wrench text-warning",
            error: "fa-exclamation-triangle text-danger",
            inactive: "fa-minus-circle text-secondary",
        };
        return icons[status] || "fa-question-circle";
    }

    getStatusBadge(status) {
        const badges = {
            online: "badge-success",
            offline: "badge-danger",
            maintenance: "badge-warning",
            error: "badge-danger",
            inactive: "badge-secondary",
        };
        return badges[status] || "badge-secondary";
    }

    getBatteryLevelClass(level) {
        if (level >= 70) return "high";
        if (level >= 30) return "medium";
        return "low";
    }

    getDeviceIcon(type) {
        const icons = {
            smart_lock: "fa-lock",
            thermostat: "fa-thermometer-half",
            sensor_motion: "fa-bolt",
            sensor_door: "fa-door-open",
            sensor_water: "fa-tint",
            sensor_smoke: "fa-fire",
            sensor_co2: "fa-exclamation-circle",
            camera: "fa-video-camera",
            hub: "fa-microchip",
            other: "fa-cog",
        };
        return icons[type] || "fa-cog";
    }

    formatLastSeen(dateStr) {
        if (!dateStr) return "Never";
        const date = new Date(dateStr);
        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMs / 3600000);
        const diffDays = Math.floor(diffMs / 86400000);

        if (diffMins < 1) return "Just now";
        if (diffMins < 60) return `${diffMins} min ago`;
        if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
        return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
    }

    async sendDeviceCommand(deviceId, command, params = {}) {
        try {
            const result = await this.orm.call(
                "property.iot.device",
                "action_send_command",
                [deviceId, command, params],
                {}
            );

            this.notification.add(`Command "${command}" sent successfully`, {
                type: "success",
            });

            // Refresh devices
            await this.loadDevices();

            return result;
        } catch (error) {
            console.error("Error sending device command:", error);
            this.notification.add("Failed to send command", {
                type: "danger",
            });
            return false;
        }
    }

    async refreshDevice(deviceId) {
        try {
            const result = await this.orm.call(
                "property.iot.device",
                "action_refresh",
                [deviceId],
                {}
            );

            this.notification.add("Device refreshed", {
                type: "success",
            });

            await this.loadDevices();

            return result;
        } catch (error) {
            console.error("Error refreshing device:", error);
            this.notification.add("Failed to refresh device", {
                type: "danger",
            });
            return false;
        }
    }

    viewDeviceDetail(deviceId) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "property.iot.device",
            res_id: deviceId,
            views: [[false, "form"]],
            target: "current",
        });
    }
}

IoTDeviceWidget.template = "smart_property_lifecycle.IoTDeviceWidget";

registry.category("widgets").add("iot_device_widget", IoTDeviceWidget);