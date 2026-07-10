/* global Chart */
odoo.define('construction_costing_suite.dashboard', function (require) {
    'use strict';

    var core = require('web.core');
    var Widget = require('web.Widget');

    var DashboardChartWidget = Widget.extend({
        template: 'dashboard_chart_widget',
        events: {
            'click .o_dashboard_refresh': '_onRefresh',
        },

        init: function (parent, data) {
            this._super(parent);
            this.data = data || {};
            this.chart = null;
        },

        start: function () {
            this._super();
            this._renderCharts();
        },

        _renderCharts: function () {
            this._renderCostByCategoryChart();
            this._renderMonthlyCostChart();
        },

        _renderCostByCategoryChart: function () {
            var self = this;
            var canvas = this.$el.find('#dashboard_cost_by_category')[0];
            if (!canvas) return;

            var ctx = canvas.getContext('2d');
            var data = this.data.category_cost_data || [];

            var colors = {
                'materials': '#2196F3',
                'labor': '#FF9800',
                'subcontractor': '#9C27B0',
                'equipment': '#4CAF50',
                'overhead': '#F44336',
                'other': '#607D8B'
            };

            var labels = data.map(function (item) { return item.label; });
            var values = data.map(function (item) { return item.value; });
            var backgroundColors = data.map(function (item) {
                return colors[item.label] || '#607D8B';
            });

            if (this.chart) {
                this.chart.destroy();
            }

            this.chart = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: labels,
                    datasets: [{
                        data: values,
                        backgroundColor: backgroundColors,
                        borderWidth: 2,
                        borderColor: '#ffffff'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: 'right',
                            labels: {
                                boxWidth: 15,
                                padding: 10,
                                font: {
                                    size: 12
                                }
                            }
                        },
                        tooltip: {
                            callbacks: {
                                label: function (context) {
                                    var label = context.label || '';
                                    var value = context.parsed || 0;
                                    var total = context.dataset.data.reduce(function (a, b) {
                                        return a + b;
                                    }, 0);
                                    var percentage = total > 0 ? (value / total * 100).toFixed(1) : 0;
                                    return label + ': $' + value.toFixed(2) + ' (' + percentage + '%)';
                                }
                            }
                        }
                    }
                }
            });
        },

        _renderMonthlyCostChart: function () {
            var self = this;
            var canvas = this.$el.find('#dashboard_monthly_cost')[0];
            if (!canvas) return;

            var ctx = canvas.getContext('2d');
            var data = this.data.monthly_cost_data || [];

            var labels = data.map(function (item) { return item.month; });
            var values = data.map(function (item) { return item.cost; });

            if (this.monthlyChart) {
                this.monthlyChart.destroy();
            }

            this.monthlyChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Monthly Cost',
                        data: values,
                        borderColor: '#2196F3',
                        backgroundColor: 'rgba(33, 150, 243, 0.1)',
                        borderWidth: 3,
                        fill: true,
                        tension: 0.4,
                        pointBackgroundColor: '#2196F3',
                        pointRadius: 4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: false
                        },
                        tooltip: {
                            callbacks: {
                                label: function (context) {
                                    return '$' + context.parsed.y.toFixed(2);
                                }
                            }
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: {
                                callback: function (value) {
                                    return '$' + value.toFixed(0);
                                }
                            }
                        }
                    }
                }
            });
        },

        _onRefresh: function (event) {
            event.preventDefault();
            this.trigger('refresh_dashboard');
        },

        destroy: function () {
            if (this.chart) {
                this.chart.destroy();
                this.chart = null;
            }
            if (this.monthlyChart) {
                this.monthlyChart.destroy();
                this.monthlyChart = null;
            }
            this._super();
        }
    });

    core.action_registry.add('construction_dashboard', DashboardChartWidget);

    return DashboardChartWidget;
});