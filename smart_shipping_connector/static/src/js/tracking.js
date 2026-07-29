odoo.define('smart_shipping_connector.tracking', function (require) {
    "use strict";

    var core = require('web.core');
    var Widget = require('web.Widget');
    var Dialog = require('web.Dialog');
    var _t = core._t;

    var TrackingWidget = Widget.extend({
        events: {
            'click .btn-track': '_onTrack',
            'click .btn-update-tracking': '_onUpdateTracking',
            'click .btn-refresh': '_onRefresh',
        },

        init: function (parent, options) {
            this._super(parent, options);
            this.trackingNumber = options.tracking_number || '';
            this.shipmentId = options.shipment_id || null;
        },

        start: function () {
            this._super();
            if (this.trackingNumber) {
                this._loadTrackingData();
            }
            return this;
        },

        _onTrack: function (ev) {
            ev.preventDefault();
            var self = this;
            var trackingNumber = this.$('#tracking-input').val();

            if (!trackingNumber) {
                Dialog.alert(this, _t('Please enter a tracking number.'), {
                    title: _t('Error'),
                });
                return;
            }

            window.location.href = '/shipping/track/' + trackingNumber;
        },

        _onUpdateTracking: function (ev) {
            ev.preventDefault();
            var self = this;

            if (!this.shipmentId) {
                Dialog.alert(this, _t('No shipment ID provided.'), {
                    title: _t('Error'),
                });
                return;
            }

            this._rpc({
                model: 'shipping.shipment',
                method: 'action_update_tracking',
                args: [[this.shipmentId]],
            }).then(function () {
                self._loadTrackingData();
                self.display_notification(_t('Tracking Updated'), _t('Tracking information has been updated.'));
            }).guardedCatch(function (error) {
                self.display_error(error);
            });
        },

        _onRefresh: function (ev) {
            ev.preventDefault();
            this._loadTrackingData();
        },

        _loadTrackingData: function () {
            var self = this;

            if (!this.trackingNumber) {
                return;
            }

            this._rpc({
                model: 'shipping.shipment',
                method: 'search',
                args: [[['tracking_number', '=', this.trackingNumber]]],
            }).then(function (ids) {
                if (ids.length > 0) {
                    return self._rpc({
                        model: 'shipping.shipment',
                        method: 'read',
                        args: [ids, ['name', 'state', 'tracking_number', 'tracking_url', 'tracking_event_ids']],
                    });
                }
                return null;
            }).then(function (data) {
                if (data && data.length > 0) {
                    self._updateUI(data[0]);
                } else {
                    self._showNotFound();
                }
            }).guardedCatch(function (error) {
                self.display_error(error);
            });
        },

        _updateUI: function (data) {
            // Update UI with tracking data
            this.$('.tracking-number').text(data.tracking_number || 'N/A');
            this.$('.shipment-status').text(data.state || 'Unknown');
            this.$('.shipment-name').text(data.name || 'N/A');

            if (data.tracking_url) {
                this.$('.tracking-url').attr('href', data.tracking_url).show();
            }

            // Update events
            var eventsContainer = this.$('.tracking-events');
            eventsContainer.empty();

            if (data.tracking_event_ids && data.tracking_event_ids.length > 0) {
                // Events are in the ID format, need to read them
                this._rpc({
                    model: 'shipping.tracking.event',
                    method: 'read',
                    args: [data.tracking_event_ids, ['event_date', 'status_description', 'location', 'is_delivered']],
                }).then(function (events) {
                    self._renderEvents(events);
                });
            } else {
                eventsContainer.append('<p class="text-muted">No tracking events available.</p>');
            }
        },

        _renderEvents: function (events) {
            var eventsContainer = this.$('.tracking-events');
            eventsContainer.empty();

            var sorted = events.sort(function (a, b) {
                return new Date(b.event_date) - new Date(a.event_date);
            });

            var html = '<ul class="list-unstyled timeline">';
            for (var i = 0; i < sorted.length; i++) {
                var event = sorted[i];
                var cls = event.is_delivered ? 'timeline-delivered' : 'timeline-item';
                html += '<li class="' + cls + '" style="border-left: 3px solid #ccc; padding-left: 10px; margin-bottom: 10px;">';
                html += '<div><strong>' + (event.event_date ? new Date(event.event_date).toLocaleString() : 'N/A') + '</strong>';
                html += '<span class="badge float-right badge-info">' + (event.status_description || 'Status Update') + '</span></div>';
                html += '<div>' + (event.status_description || '') + (event.location ? '<br/><small class="text-muted"><i class="fa fa-map-marker"></i> ' + event.location + '</small>' : '') + '</div>';
                html += '</li>';
            }
            html += '</ul>';
            eventsContainer.append(html);
        },

        _showNotFound: function () {
            this.$('.tracking-results').hide();
            this.$('.not-found').show();
        },

        display_notification: function (title, message, type) {
            this.do_action({
                type: 'ir.actions.client',
                tag: 'display_notification',
                params: {
                    title: title || _t('Success'),
                    message: message,
                    type: type || 'success',
                    sticky: false,
                }
            });
        },

        display_error: function (error) {
            var message = error.message || error;
            Dialog.alert(this, message, {
                title: _t('Error'),
            });
        },
    });

    core.action_registry.add('shipping_tracking_widget', TrackingWidget);
    return TrackingWidget;
});