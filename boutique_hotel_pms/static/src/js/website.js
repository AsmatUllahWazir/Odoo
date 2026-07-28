odoo.define('boutique_hotel_pms.website', function (require) {
    "use strict";

    var publicWidget = require('web.public.widget');
    var ajax = require('web.ajax');
    var core = require('web.core');
    var _t = core._t;

    var HotelWebsite = publicWidget.Widget.extend({
        selector: '.hotel-website',
        events: {
            'change #check_in': '_onDateChange',
            'change #check_out': '_onDateChange',
            'click .hotel-book-now': '_onBookNow',
            'change .room-selector': '_onRoomChange',
        },

        init: function() {
            this._super.apply(this, arguments);
            this.checkIn = null;
            this.checkOut = null;
            this.roomTypeId = null;
        },

        start: function() {
            this._super.apply(this, arguments);
            this._initDatePickers();
            this._initRoomSelector();
            return this;
        },

        _initDatePickers: function() {
            var self = this;
            var today = new Date();

            $('#check_in, #check_out').datepicker({
                dateFormat: 'yy-mm-dd',
                minDate: today,
                onSelect: function(selectedDate) {
                    var field = $(this);
                    var targetField = field.attr('id') === 'check_in' ? '#check_out' : '#check_in';
                    var minDate = new Date(selectedDate);
                    if (field.attr('id') === 'check_in') {
                        minDate.setDate(minDate.getDate() + 1);
                        $(targetField).datepicker('option', 'minDate', minDate);
                        self.checkIn = selectedDate;
                    } else {
                        self.checkOut = selectedDate;
                    }

                    if (self.checkIn && self.checkOut && self.roomTypeId) {
                        self._checkAvailability();
                    }
                }
            });
        },

        _initRoomSelector: function() {
            var self = this;
            $('.room-selector').on('change', function() {
                self.roomTypeId = $(this).val();
                if (self.checkIn && self.checkOut) {
                    self._checkAvailability();
                }
            });
        },

        _onDateChange: function(ev) {
            var field = $(ev.currentTarget);
            if (field.attr('id') === 'check_in') {
                this.checkIn = field.val();
            } else {
                this.checkOut = field.val();
            }

            if (this.checkIn && this.checkOut && this.roomTypeId) {
                this._checkAvailability();
            }
        },

        _onRoomChange: function(ev) {
            this.roomTypeId = $(ev.currentTarget).val();
        },

        _onBookNow: function(ev) {
            var self = this;
            var form = $(ev.currentTarget).closest('form');
            var data = form.serialize();

            ajax.jsonRpc('/hotel/booking', 'call', data).then(function(result) {
                if (result.success) {
                    window.location.href = '/hotel/booking/success/' + result.reservation_id;
                } else {
                    self._showError(result.error || _t('An error occurred. Please try again.'));
                }
            }).catch(function() {
                self._showError(_t('Network error. Please try again.'));
            });
        },

        _checkAvailability: function() {
            var self = this;
            var data = {
                room_type_id: this.roomTypeId,
                check_in: this.checkIn,
                check_out: this.checkOut
            };

            $('.availability-indicator').html('<i class="fa fa-spinner fa-spin"/> Checking...');

            ajax.jsonRpc('/hotel/availability', 'call', data).then(function(result) {
                var indicator = $('.availability-indicator');
                if (result.error) {
                    indicator.html('<span class="text-danger"><i class="fa fa-exclamation-circle"/> ' + result.error + '</span>');
                } else if (result.available) {
                    indicator.html('<span class="text-success"><i class="fa fa-check-circle"/> ' +
                                  result.available_count + ' rooms available</span>');
                    $('.hotel-book-now').prop('disabled', false);
                } else {
                    indicator.html('<span class="text-danger"><i class="fa fa-times-circle"/> No rooms available</span>');
                    $('.hotel-book-now').prop('disabled', true);
                }
            });
        },

        _showError: function(message) {
            var errorDiv = $('.hotel-error');
            if (errorDiv.length) {
                errorDiv.html('<div class="alert alert-danger">' + message + '</div>');
                errorDiv.show();
            }
        }
    });

    publicWidget.registry.hotel_website = HotelWebsite;

    return HotelWebsite;
});