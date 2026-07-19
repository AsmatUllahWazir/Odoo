/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

/**
 * Property Dashboard Widget
 * Displays key metrics and statistics for property management
 */
export class PropertyDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");

        this.state = useState({
            totalProperties: 0,
            activeProperties: 0,
            occupiedUnits: 0,
            vacantUnits: 0,
            totalRevenue: 0,
            pendingMaintenance: 0,
            activeLeases: 0,
            recentActivities: [],
            loading: true,
        });

        onWillStart(async () => {
            await this.loadDashboardData();
        });
    }

    async loadDashboardData() {
        this.state.loading = true;
        try {
            // Fetch property statistics
            const propertyStats = await this.orm.call(
                "property.property",
                "get_dashboard_stats",
                [],
                {}
            );

            // Fetch recent activities
            const recentActivities = await this.orm.searchRead(
                "mail.message",
                [
                    ["model", "in", ["property.property", "property.lease", "property.maintenance.request"]],
                    ["create_date", ">=", this.getDateDaysAgo(7)],
                ],
                ["create_date", "body", "author_id", "model"],
                { limit: 10, order: "create_date desc" }
            );

            this.state.totalProperties = propertyStats.total_properties || 0;
            this.state.activeProperties = propertyStats.active_properties || 0;
            this.state.occupiedUnits = propertyStats.occupied_units || 0;
            this.state.vacantUnits = propertyStats.vacant_units || 0;
            this.state.totalRevenue = propertyStats.total_revenue || 0;
            this.state.pendingMaintenance = propertyStats.pending_maintenance || 0;
            this.state.activeLeases = propertyStats.active_leases || 0;
            this.state.recentActivities = recentActivities;
        } catch (error) {
            console.error("Error loading dashboard data:", error);
        } finally {
            this.state.loading = false;
        }
    }

    getDateDaysAgo(days) {
        const date = new Date();
        date.setDate(date.getDate() - days);
        return date.toISOString().split("T")[0];
    }

    formatCurrency(amount) {
        if (!amount) return "$0";
        return "$" + Number(amount).toLocaleString("en-US", {
            minimumFractionDigits: 0,
            maximumFractionDigits: 0,
        });
    }

    formatDate(dateStr) {
        if (!dateStr) return "";
        const date = new Date(dateStr);
        return date.toLocaleDateString("en-US", {
            month: "short",
            day: "numeric",
            year: "numeric",
        });
    }

    getActivityIcon(model) {
        const icons = {
            "property.property": "fa-building",
            "property.lease": "fa-file-text-o",
            "property.maintenance.request": "fa-wrench",
            "property.viewing": "fa-calendar",
        };
        return icons[model] || "fa-bell";
    }

    getActivityColor(model) {
        const colors = {
            "property.property": "primary",
            "property.lease": "success",
            "property.maintenance.request": "warning",
            "property.viewing": "info",
        };
        return colors[model] || "secondary";
    }

    navigateTo(action) {
        this.action.doAction(action);
    }
}

PropertyDashboard.template = "smart_property_lifecycle.PropertyDashboard";
PropertyDashboard.components = {};

registry.category("dashboard").add("property_dashboard", PropertyDashboard);