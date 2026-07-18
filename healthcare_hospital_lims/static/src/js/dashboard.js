odoo.define('hospital_lims.dashboard', function (require) {
    "use strict";

    var AbstractAction = require('web.AbstractAction');
    var core = require('web.core');
    var QWeb = core.qweb;
    var rpc = require('web.rpc');

    var Dashboard = AbstractAction.extend({
        template: 'lims_dashboard_template',
        events: {
            'click .refresh-dashboard': '_onRefresh',
            'click .quick-action': '_onQuickAction',
        },

        init: function (parent, action) {
            this._super.apply(this, arguments);
            this.dashboardData = {};
        },

        start: function () {
            this._super.apply(this, arguments);
            this._loadDashboardData();
            // Auto-refresh every 60 seconds
            this.refreshInterval = setInterval(this._loadDashboardData.bind(this), 60000);
        },

        destroy: function () {
            if (this.refreshInterval) {
                clearInterval(this.refreshInterval);
            }
            this._super.apply(this, arguments);
        },

        _loadDashboardData: function () {
            var self = this;
            rpc.query({
                model: 'lims.dashboard',
                method: 'get_dashboard_data',
                args: [{}],
            }).then(function (data) {
                self.dashboardData = data;
                self._renderDashboard();
            }).catch(function (error) {
                console.error('Error loading dashboard data:', error);
            });
        },

        _renderDashboard: function () {
            var data = this.dashboardData;
            var $el = this.$('.dashboard-content');
            
            // Update stats
            $el.find('.stat-total-orders').text(data.total_orders || 0);
            $el.find('.stat-total-patients').text(data.total_patients || 0);
            $el.find('.stat-total-samples').text(data.total_samples || 0);
            $el.find('.stat-total-reports').text(data.total_reports || 0);
            
            $el.find('.stat-today-orders').text(data.today_orders || 0);
            $el.find('.stat-today-samples').text(data.today_samples || 0);
            $el.find('.stat-today-reports').text(data.today_reports || 0);
            $el.find('.stat-today-revenue').text(data.today_revenue || 0);
            
            $el.find('.stat-pending-orders').text(data.pending_orders || 0);
            $el.find('.stat-pending-samples').text(data.pending_samples || 0);
            $el.find('.stat-abnormal-results').text(data.abnormal_results || 0);
            $el.find('.stat-critical-results').text(data.critical_results || 0);
            
            // QC Stats
            $el.find('.stat-qc-passed').text(data.qc_passed || 0);
            $el.find('.stat-qc-failed').text(data.qc_failed || 0);
            $el.find('.stat-qc-pass-rate').text((data.qc_pass_rate || 0).toFixed(1) + '%');
            
            // Performance
            $el.find('.stat-completion-rate').text((data.completion_rate || 0).toFixed(1) + '%');
            $el.find('.stat-on-time-rate').text((data.on_time_rate || 0).toFixed(1) + '%');
            $el.find('.stat-avg-turnaround').text((data.avg_turnaround || 0).toFixed(1) + 'h');
            
            // Weekly/Monthly
            $el.find('.stat-week-orders').text(data.week_orders || 0);
            $el.find('.stat-week-revenue').text(data.week_revenue || 0);
            $el.find('.stat-month-orders').text(data.month_orders || 0);
            $el.find('.stat-month-revenue').text(data.month_revenue || 0);
            $el.find('.stat-year-orders').text(data.year_orders || 0);
            $el.find('.stat-year-revenue').text(data.year_revenue || 0);
        },

        _onRefresh: function () {
            this._loadDashboardData();
        },

        _onQuickAction: function (event) {
            var action = $(event.currentTarget).data('action');
            if (action) {
                this.do_action({
                    type: 'ir.actions.act_window',
                    name: action,
                    res_model: action,
                    view_mode: 'tree,form',
                    target: 'current',
                });
            }
        },
    });

    core.action_registry.add('lims_dashboard', Dashboard);

    return Dashboard;
});