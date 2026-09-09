/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class DeliveryFleetDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            loading: true, error: false, refreshing: false,
            dateFrom: this._dateDaysAgo(29), dateTo: this._dateToday(),
            data: {}, compare: {}, trend: [], routes: [], drivers: [],
        });
        onWillStart(() => this.loadDashboard());
    }
    _dateToday() { return new Date().toISOString().slice(0, 10); }
    _dateDaysAgo(days) { const d = new Date(); d.setDate(d.getDate() - days); return d.toISOString().slice(0, 10); }
    async loadDashboard() {
        this.state.loading = !this.state.data.kpis;
        this.state.refreshing = true; this.state.error = false;
        try {
            const [data, compare, trend, routes, drivers] = await Promise.all([
                this.orm.call("delivery.kpi.engine", "command_center", [this.state.dateFrom, this.state.dateTo]),
                this.orm.call("delivery.kpi.engine", "trend_compare", [this.state.dateFrom, this.state.dateTo]),
                this.orm.call("delivery.kpi.engine", "trend", [], { days: 30 }),
                this.orm.searchRead("delivery.route", [["date", ">=", this.state.dateFrom], ["date", "<=", this.state.dateTo]], ["name", "date", "state", "priority", "driver_id", "vehicle_id", "stop_count", "delivered_count", "failed_count", "profitability", "margin_percent", "readiness_score", "readiness_state", "open_exception_count"], { limit: 15, order: "priority desc, date desc, id desc" }),
                this.orm.searchRead("delivery.driver.performance", [], ["driver_id", "route_count", "delivered_count", "failed_count", "on_time_percent", "profit"], { limit: 12, order: "on_time_percent desc, delivered_count desc" }),
            ]);
            this.state.data = data; this.state.compare = compare; this.state.trend = trend; this.state.routes = routes; this.state.drivers = drivers;
        } catch (error) { console.error(error); this.state.error = true; }
        finally { this.state.loading = false; this.state.refreshing = false; }
    }
    async applyFilters() { if (this.state.dateFrom > this.state.dateTo) { [this.state.dateFrom, this.state.dateTo] = [this.state.dateTo, this.state.dateFrom]; } await this.loadDashboard(); }
    setPreset(days) { this.state.dateTo = this._dateToday(); this.state.dateFrom = this._dateDaysAgo(days - 1); this.loadDashboard(); }
    openAction(xmlId) { this.action.doAction(xmlId); }
    openRoute(id) { this.action.doAction({ type: "ir.actions.act_window", res_model: "delivery.route", views: [[false, "form"]], res_id: id }); }
    openException(id) { this.action.doAction({ type: "ir.actions.act_window", res_model: "delivery.exception", views: [[false, "form"]], res_id: id }); }
    formatNumber(value, decimals = 0) { return Number(value || 0).toLocaleString(undefined, { minimumFractionDigits: decimals, maximumFractionDigits: decimals }); }
    formatMoney(value) { return this.formatNumber(value, 2); }
    percent(value) { return `${this.formatNumber(value, 1)}%`; }
    progress(value) { return `${Math.max(0, Math.min(100, Number(value || 0)))}%`; }
    change(key) { return this.state.compare?.[key]?.change_percent || 0; }
    changeClass(key) { return this.change(key) >= 0 ? "dfp-up" : "dfp-down"; }
    stateLabel(value) { return ({ draft: "Draft", planned: "Planned", dispatched: "Dispatched", in_transit: "In Transit", done: "Done", partial: "Partial", failed: "Failed", cancelled: "Cancelled" })[value] || value || "—"; }
    priorityLabel(value) { return ({ "0": "Low", "1": "Normal", "2": "High", "3": "Critical" })[value] || "Normal"; }
    priorityClass(value) { return `dfp-priority-${value || "1"}`; }
    exceptionType(value) { return ({ late: "Late", capacity: "Capacity", vehicle: "Vehicle", driver: "Driver", address: "Address", customer: "Customer", pod: "POD", system: "System", other: "Other" })[value] || value; }
    get trendMax() { return Math.max(1, ...this.state.trend.map(i => Number(i.delivered_count || 0) + Number(i.failed_count || 0))); }
    get latestTrend() { return this.state.trend.slice(-14); }
}
DeliveryFleetDashboard.template = "delivery_fleet_pro.DeliveryFleetDashboard";
registry.category("actions").add("delivery_fleet_pro_dashboard", DeliveryFleetDashboard);
