odoo.define('smart_shipping_connector.shipment', function (require) {
    "use strict";

    var core = require('web.core');
    var Widget = require('web.Widget');
    var Dialog = require('web.Dialog');
    var _t = core._t;

    var ShipmentWidget = Widget.extend({
        events: {
            'click .btn-get-rates': '_onGetRates',
            'click .btn-generate-label': '_onGenerateLabel',
            'click .btn-update-tracking': '_onUpdateTracking',
            'click .btn-view-tracking': '_onViewTracking',
            'click .btn-create-return': '_onCreateReturn',
        },

        _onGetRates: function (ev) {
            ev.preventDefault();
            var self = this;
            var shipmentId = $(ev.currentTarget).data('shipment-id');

            this._rpc({
                model: 'shipping.shipment',
                method: 'action_get_rates',
                args: [[shipmentId]],
            }).then(function (result) {
                self.do_action(result);
            }).guardedCatch(function (error) {
                self.display_error(error);
            });
        },

        _onGenerateLabel: function (ev) {
            ev.preventDefault();
            var self = this;
            var shipmentId = $(ev.currentTarget).data('shipment-id');

            this._rpc({
                model: 'shipping.shipment',
                method: 'action_generate_label',
                args: [[shipmentId]],
            }).then(function (result) {
                self.do_action(result);
            }).guardedCatch(function (error) {
                self.display_error(error);
            });
        },

        _onUpdateTracking: function (ev) {
            ev.preventDefault();
            var self = this;
            var shipmentId = $(ev.currentTarget).data('shipment-id');

            this._rpc({
                model: 'shipping.shipment',
                method: 'action_update_tracking',
                args: [[shipmentId]],
            }).then(function (result) {
                self.display_notification(_t('Tracking Updated'), _t('Tracking information has been updated.'));
            }).guardedCatch(function (error) {
                self.display_error(error);
            });
        },

        _onViewTracking: function (ev) {
            ev.preventDefault();
            var shipmentId = $(ev.currentTarget).data('shipment-id');

            this.do_action({
                type: 'ir.actions.act_window',
                name: _t('Tracking Events'),
                res_model: 'shipping.tracking.event',
                view_mode: 'tree,form',
                domain: [['shipment_id', '=', shipmentId]],
            });
        },

        _onCreateReturn: function (ev) {
            ev.preventDefault();
            var shipmentId = $(ev.currentTarget).data('shipment-id');

            this.do_action({
                type: 'ir.actions.act_window',
                name: _t('Create Return'),
                res_model: 'shipping.return',
                view_mode: 'form',
                target: 'new',
                context: {
                    default_original_shipment_id: shipmentId,
                },
            });
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

    core.action_registry.add('shipping_shipment_widget', ShipmentWidget);
    return ShipmentWidget;
});