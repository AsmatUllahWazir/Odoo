/** @odoo-module **/
/**
 * tracker_dashboard.js
 * =====================================================================
 * Live Monitoring Dashboard OWL Component
 * - Real-time stats cards (active/idle/offline users)
 * - Activity breakdown (creates/writes/deletes today)
 * - Module activity bar chart (pure CSS)
 * - Online users list with status badges
 * - Security alerts panel
 * - Auto-refreshes every 30 seconds
 * =====================================================================
 */

import { Component, useState, onMounted, onWillUnmount, xml } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

// -------------------------------------------------------------------------
// Utility: Format duration
// -------------------------------------------------------------------------
function formatDuration(hours) {
    if (!hours || hours < 0) return "0m";
    const h = Math.floor(hours);
    const m = Math.round((hours - h) * 60);
    if (h === 0) return `${m}m`;
    if (m === 0) return `${h}h`;
    return `${h}h ${m}m`;
}

// -------------------------------------------------------------------------
// Utility: Time-ago formatter
// -------------------------------------------------------------------------
function timeAgo(isoString) {
    if (!isoString) return "Never";
    const diff = (Date.now() - new Date(isoString).getTime()) / 1000;
    if (diff < 60) return `${Math.floor(diff)}s ago`;
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    return `${Math.floor(diff / 86400)}d ago`;
}

// -------------------------------------------------------------------------
// Dashboard Component
// -------------------------------------------------------------------------
class ActivityTrackerDashboard extends Component {
    static template = "employee_activity_tracker.Dashboard";

    setup() {
        this.rpc = useService("rpc");
        this.action = useService("action");

        this.state = useState({
            loading: true,
            lastRefresh: null,
            sessions: { active: 0, idle: 0, offline: 0, total: 0 },
            activities: {
                total: 0, creates: 0, writes: 0,
                deletes: 0, failed_logins: 0
            },
            modules: [],
            onlineUsers: [],
            securityAlerts: [],
            topUsers: [],
            currentTime: new Date().toLocaleTimeString(),
        });

        this._refreshTimer = null;
        this._clockTimer = null;

        onMounted(() => {
            this.loadDashboardData();
            // Auto-refresh every 30 seconds
            this._refreshTimer = setInterval(() => {
                this.loadDashboardData();
            }, 30000);
            // Clock update every second
            this._clockTimer = setInterval(() => {
                this.state.currentTime = new Date().toLocaleTimeString();
            }, 1000);
        });

        onWillUnmount(() => {
            if (this._refreshTimer) clearInterval(this._refreshTimer);
            if (this._clockTimer) clearInterval(this._clockTimer);
        });
    }

    async loadDashboardData() {
        try {
            const data = await this.rpc("/activity_tracker/live_stats", {});
            if (data && !data.error) {
                this.state.sessions = data.sessions || this.state.sessions;
                this.state.activities = data.activities || this.state.activities;
                this.state.modules = data.modules || [];
                this.state.securityAlerts = data.security_alerts || [];
                this.state.topUsers = data.top_users || [];
                this.state.lastRefresh = new Date().toLocaleTimeString();
            }
        } catch (e) {
            console.warn("[TrackerDashboard] Failed to load stats:", e);
        }

        // Load online users separately
        try {
            const sessionData = await this.rpc("/activity_tracker/dashboard_data", {});
            if (sessionData && !sessionData.error) {
                this.state.onlineUsers = sessionData.online_users || [];
            }
        } catch (e) {
            console.warn("[TrackerDashboard] Failed to load session data:", e);
        }

        this.state.loading = false;
    }

    // -----------------------------------------------------------------------
    // Navigation actions
    // -----------------------------------------------------------------------
    openSessionLogs() {
        this.action.doAction("employee_activity_tracker.action_tracker_session_log");
    }

    openActivityLogs() {
        this.action.doAction("employee_activity_tracker.action_tracker_activity_log");
    }

    openSecurityLogs() {
        this.action.doAction("employee_activity_tracker.action_tracker_security_log");
    }

    openActiveSessions() {
        this.action.doAction("employee_activity_tracker.action_tracker_active_sessions");
    }

    openUserStatus() {
        this.action.doAction("employee_activity_tracker.action_tracker_user_status");
    }

    openFieldChanges() {
        this.action.doAction("employee_activity_tracker.action_tracker_field_change_log");
    }

    manualRefresh() {
        this.state.loading = true;
        this.loadDashboardData();
    }

    // -----------------------------------------------------------------------
    // Computed helpers
    // -----------------------------------------------------------------------
    get maxModuleCount() {
        const counts = this.state.modules.map((m) => m.count);
        return Math.max(...counts, 1);
    }

    get onlineCount() {
        return (this.state.sessions.active || 0) + (this.state.sessions.idle || 0);
    }

    formatDuration(h) {
        return formatDuration(h);
    }

    timeAgo(s) {
        return timeAgo(s);
    }

    getStatusClass(status) {
        return {
            active: "tracker-badge-active",
            idle: "tracker-badge-idle",
            logged_out: "tracker-badge-offline",
            expired: "tracker-badge-expired",
            forced_logout: "tracker-badge-danger",
        }[status] || "tracker-badge-offline";
    }

    getSeverityClass(severity) {
        return {
            critical: "tracker-alert-critical",
            warning: "tracker-alert-warning",
            info: "tracker-alert-info",
        }[severity] || "tracker-alert-info";
    }
}

// Register as a client action
registry.category("actions").add(
    "activity_tracker.Dashboard",
    ActivityTrackerDashboard
);

export { ActivityTrackerDashboard };