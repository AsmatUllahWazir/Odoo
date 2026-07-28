odoo.define('boutique_hotel_pms.dashboard', function (require) {
    "use strict";

    var AbstractAction = require('web.AbstractAction');
    var core = require('web.core');
    var _t = core._t;
    var rpc = require('web.rpc');

    var HotelDashboard = AbstractAction.extend({
        template: 'hotel_dashboard_template',

        events: {
            'click .hotel-refresh-dashboard': '_onRefresh',
        },

        init: function(parent, action) {
            this._super.apply(this, arguments);
            this.controller = parent;
        },

        start: function() {
            this._super.apply(this, arguments);
            this._loadDashboardData();
            this._initCharts();
            this._autoRefresh();
            return this;
        },

        _loadDashboardData: function() {
            var self = this;

            // Load room stats
            rpc.query({
                model: 'hotel.room',
                method: 'search_read',
                args: [[], ['status']],
                kwargs: {}
            }).then(function(rooms) {
                var total = rooms.length;
                var available = rooms.filter(function(r) { return r.status === 'available'; }).length;
                var occupied = rooms.filter(function(r) { return r.status === 'occupied'; }).length;
                var dirty = rooms.filter(function(r) { return r.status === 'dirty'; }).length;

                self.$('#total_rooms').text(total);
                self.$('#available_rooms').text(available);
                self.$('#occupied_rooms').text(occupied);
                self.$('#dirty_rooms').text(dirty);
            }).catch(function(err) {
                console.warn('Error loading room stats:', err);
            });

            // Load today's check-ins
            rpc.query({
                model: 'hotel.reservation',
                method: 'get_today_checkins',
                args: [],
                kwargs: {}
            }).then(function(checkins) {
                self.$('#today_checkins').text(checkins.length);
                var html = '';
                if (checkins.length > 0) {
                    checkins.forEach(function(res) {
                        html += '<div class="border-bottom py-2">';
                        html += '<strong>' + (res.partner_id ? res.partner_id[1] : 'Unknown') + '</strong>';
                        html += ' - Room ';
                        if (res.room_ids && res.room_ids.length > 0) {
                            res.room_ids.forEach(function(room, index) {
                                html += room[1];
                                if (index < res.room_ids.length - 1) html += ', ';
                            });
                        }
                        html += ' <span class="badge badge-info float-right">Check-in</span>';
                        html += '</div>';
                    });
                } else {
                    html = '<p class="text-muted mb-0">No check-ins today</p>';
                }
                self.$('#today_checkins_list').html(html);
            }).catch(function(err) {
                console.warn('Error loading check-ins:', err);
            });

            // Load today's check-outs
            rpc.query({
                model: 'hotel.reservation',
                method: 'get_today_checkouts',
                args: [],
                kwargs: {}
            }).then(function(checkouts) {
                var html = '';
                if (checkouts.length > 0) {
                    checkouts.forEach(function(res) {
                        html += '<div class="border-bottom py-2">';
                        html += '<strong>' + (res.partner_id ? res.partner_id[1] : 'Unknown') + '</strong>';
                        html += ' - Room ';
                        if (res.room_ids && res.room_ids.length > 0) {
                            res.room_ids.forEach(function(room, index) {
                                html += room[1];
                                if (index < res.room_ids.length - 1) html += ', ';
                            });
                        }
                        html += ' <span class="badge badge-warning float-right">Check-out</span>';
                        html += '</div>';
                    });
                } else {
                    html = '<p class="text-muted mb-0">No check-outs today</p>';
                }
                self.$('#today_checkouts_list').html(html);
            }).catch(function(err) {
                console.warn('Error loading check-outs:', err);
            });

            // Load upcoming reservations
            var today = new Date().toISOString().split('T')[0];
            rpc.query({
                model: 'hotel.reservation',
                method: 'search_read',
                args: [
                    [
                        ['state', '=', 'confirmed'],
                        ['check_in', '>', today]
                    ],
                    ['partner_id', 'check_in', 'check_out', 'room_ids']
                ],
                kwargs: {'limit': 10}
            }).then(function(reservations) {
                var html = '';
                if (reservations.length > 0) {
                    html = '<table class="table table-sm mb-0">';
                    html += '<thead><tr><th>Guest</th><th>Check-in</th><th>Check-out</th><th>Rooms</th></tr></thead>';
                    html += '<tbody>';
                    reservations.forEach(function(res) {
                        html += '<tr>';
                        html += '<td>' + (res.partner_id ? res.partner_id[1] : 'Unknown') + '</td>';
                        html += '<td>' + res.check_in + '</td>';
                        html += '<td>' + res.check_out + '</td>';
                        html += '<td>';
                        if (res.room_ids && res.room_ids.length > 0) {
                            res.room_ids.forEach(function(room, index) {
                                html += room[1];
                                if (index < res.room_ids.length - 1) html += ', ';
                            });
                        }
                        html += '</td>';
                        html += '</tr>';
                    });
                    html += '</tbody></table>';
                } else {
                    html = '<p class="text-muted mb-0">No upcoming reservations</p>';
                }
                self.$('#upcoming_reservations').html(html);
            }).catch(function(err) {
                console.warn('Error loading upcoming reservations:', err);
            });

            // Load housekeeping stats
            rpc.query({
                model: 'hotel.housekeeping',
                method: 'search_count',
                args: [[['status', '=', 'in_progress']]],
                kwargs: {}
            }).then(function(count) {
                self.$('#cleaning_progress').text(count);
            }).catch(function(err) {
                console.warn('Error loading cleaning progress:', err);
            });

            var today = new Date().toISOString().split('T')[0];
            rpc.query({
                model: 'hotel.housekeeping',
                method: 'search_count',
                args: [[['status', '=', 'completed'], ['completed_date', '>=', today]]],
                kwargs: {}
            }).then(function(count) {
                self.$('#cleaned_today').text(count);
            }).catch(function(err) {
                console.warn('Error loading cleaned today:', err);
            });

            rpc.query({
                model: 'hotel.housekeeping',
                method: 'search_count',
                args: [[['status', '=', 'inspected'], ['inspection_date', '>=', today]]],
                kwargs: {}
            }).then(function(count) {
                self.$('#inspected_today').text(count);
            }).catch(function(err) {
                console.warn('Error loading inspected today:', err);
            });
        },

        _initCharts: function() {
            var self = this;

            // Check if Chart.js is available
            if (typeof Chart !== 'undefined') {
                self._renderCharts();
            } else {
                // Load Chart.js from CDN
                var script = document.createElement('script');
                script.src = 'https://cdn.jsdelivr.net/npm/chart.js@3.9.1/dist/chart.min.js';
                script.onload = function() {
                    self._renderCharts();
                };
                script.onerror = function() {
                    console.warn('Failed to load Chart.js');
                };
                document.head.appendChild(script);
            }
        },

        _renderCharts: function() {
            try {
                // Wait for DOM to be ready
                setTimeout(function() {
                    // Occupancy Chart
                    var ctx1 = document.getElementById('occupancy_chart');
                    if (ctx1) {
                        new Chart(ctx1.getContext('2d'), {
                            type: 'line',
                            data: {
                                labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
                                datasets: [{
                                    label: 'Occupancy Rate',
                                    data: [65, 70, 75, 80, 85, 90, 75],
                                    borderColor: 'rgb(75, 192, 192)',
                                    backgroundColor: 'rgba(75, 192, 192, 0.2)',
                                    tension: 0.1,
                                    fill: true
                                }]
                            },
                            options: {
                                responsive: true,
                                maintainAspectRatio: false,
                                plugins: {
                                    legend: {
                                        display: true,
                                        position: 'top'
                                    }
                                },
                                scales: {
                                    y: {
                                        beginAtZero: true,
                                        max: 100
                                    }
                                }
                            }
                        });
                    }

                    // Revenue Chart
                    var ctx2 = document.getElementById('revenue_chart');
                    if (ctx2) {
                        new Chart(ctx2.getContext('2d'), {
                            type: 'bar',
                            data: {
                                labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
                                datasets: [{
                                    label: 'Revenue',
                                    data: [1200, 1500, 1800, 2000, 2200, 2500, 1800],
                                    backgroundColor: 'rgba(54, 162, 235, 0.5)',
                                    borderColor: 'rgb(54, 162, 235)',
                                    borderWidth: 1
                                }]
                            },
                            options: {
                                responsive: true,
                                maintainAspectRatio: false,
                                plugins: {
                                    legend: {
                                        display: true,
                                        position: 'top'
                                    }
                                },
                                scales: {
                                    y: {
                                        beginAtZero: true
                                    }
                                }
                            }
                        });
                    }
                }, 200);
            } catch (e) {
                console.warn('Chart rendering error:', e);
            }
        },

        _autoRefresh: function() {
            var self = this;
            // Auto-refresh every 60 seconds
            setInterval(function() {
                self._loadDashboardData();
            }, 60000);
        },

        _onRefresh: function() {
            this._loadDashboardData();
            this._initCharts();
        }
    });

    // Register the client action
    core.action_registry.add(HotelDashboard);

    return HotelDashboard;
});