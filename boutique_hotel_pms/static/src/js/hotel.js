odoo.define('boutique_hotel_pms.hotel', function (require) {
    "use strict";

    var core = require('web.core');
    var _t = core._t;
    var ajax = require('web.ajax');
    var Dialog = require('web.Dialog');

    var Hotel = {
        init: function() {
            this._initRoomStatusBoard();
            this._initReservationCalendar();
            this._initQuickCheckin();
            this._initRoomAvailability();
        },

        _initRoomStatusBoard: function() {
            // Room status board functionality
            $('.hotel-room-status-board').each(function() {
                var board = $(this);
                var roomCards = board.find('.room-card');

                roomCards.on('click', function() {
                    var roomId = $(this).data('room-id');
                    var roomNumber = $(this).data('room-number');

                    Dialog.confirm(
                        _t('What would you like to do with Room ' + roomNumber + '?'),
                        {
                            confirm_callback: function() {
                                // Show room details
                                window.location = '/web#model=hotel.room&id=' + roomId;
                            },
                            cancel_callback: function() {
                                // Close dialog
                            }
                        }
                    );
                });

                // Drag and drop for room status
                roomCards.draggable({
                    revert: true,
                    helper: 'clone',
                    zIndex: 1000
                });

                $('.status-column').droppable({
                    drop: function(event, ui) {
                        var roomId = ui.draggable.data('room-id');
                        var newStatus = $(this).data('status');
                        var oldStatus = ui.draggable.data('status');

                        // Update room status via AJAX
                        ajax.jsonRpc('/web/dataset/call_kw', 'call', {
                            model: 'hotel.room',
                            method: 'write',
                            args: [[roomId], {'status': newStatus}],
                            kwargs: {}
                        }).then(function() {
                            // Move card to new column
                            var card = ui.draggable;
                            card.data('status', newStatus);
                            card.removeAttr('style');
                            $(this).append(card);

                            // Update UI
                            card.find('.room-status').text(newStatus);
                            card.removeClass('bg-success bg-primary bg-warning bg-danger bg-secondary');
                            if (newStatus === 'available') {
                                card.addClass('bg-success');
                            } else if (newStatus === 'occupied') {
                                card.addClass('bg-primary');
                            } else if (newStatus === 'dirty') {
                                card.addClass('bg-warning');
                            } else if (newStatus === 'maintenance' || newStatus === 'blocked') {
                                card.addClass('bg-danger');
                            } else {
                                card.addClass('bg-secondary');
                            }
                        }.bind(this));
                    }.bind(this)
                });
            }.bind(this));
        },

        _initReservationCalendar: function() {
            // Reservation calendar functionality
            $('.hotel-reservation-calendar').each(function() {
                var calendar = $(this);
                var calendarId = calendar.data('calendar-id');

                // Initialize fullCalendar if available
                if (typeof FullCalendar !== 'undefined') {
                    var calendarEl = calendar[0];
                    var fc = new FullCalendar.Calendar(calendarEl, {
                        headerToolbar: {
                            left: 'prev,next today',
                            center: 'title',
                            right: 'dayGridMonth,timeGridWeek,timeGridDay'
                        },
                        events: function(info, successCallback, failureCallback) {
                            // Fetch events from server
                            ajax.jsonRpc('/web/dataset/call_kw', 'call', {
                                model: 'hotel.reservation',
                                method: 'search_read',
                                args: [
                                    [
                                        ['state', 'in', ['confirmed', 'checked_in']],
                                        ['check_in', '<=', info.endStr],
                                        ['check_out', '>=', info.startStr]
                                    ],
                                    ['name', 'partner_id', 'check_in', 'check_out', 'room_ids']
                                ],
                                kwargs: {}
                            }).then(function(reservations) {
                                var events = reservations.map(function(res) {
                                    return {
                                        title: res.partner_id[1] + ' - ' + res.name,
                                        start: res.check_in,
                                        end: res.check_out,
                                        extendedProps: {
                                            reservation_id: res.id,
                                            rooms: res.room_ids
                                        },
                                        color: res.state === 'confirmed' ? '#ffc107' : '#28a745'
                                    };
                                });
                                successCallback(events);
                            });
                        },
                        eventClick: function(info) {
                            // Open reservation on click
                            var resId = info.event.extendedProps.reservation_id;
                            window.open('/web#model=hotel.reservation&id=' + resId, '_blank');
                        },
                        eventDrop: function(info) {
                            // Handle event drag (rebooking)
                            var resId = info.event.extendedProps.reservation_id;
                            var newStart = info.event.start;
                            var newEnd = info.event.end;

                            ajax.jsonRpc('/web/dataset/call_kw', 'call', {
                                model: 'hotel.reservation',
                                method: 'write',
                                args: [
                                    [resId],
                                    {
                                        'check_in': newStart.toISOString(),
                                        'check_out': newEnd.toISOString()
                                    }
                                ],
                                kwargs: {}
                            }).then(function() {
                                Dialog.alert(_t('Reservation dates updated successfully!'));
                            }).catch(function(error) {
                                Dialog.alert(_t('Error updating reservation: ') + error.message);
                                info.revert();
                            });
                        }
                    });
                    fc.render();
                }
            }.bind(this));
        },

        _initQuickCheckin: function() {
            // Quick check-in functionality
            $('.hotel-quick-checkin').on('click', function() {
                var reservationId = $(this).data('reservation-id');
                var reservationName = $(this).data('reservation-name');

                Dialog.confirm(
                    _t('Are you sure you want to check in ' + reservationName + '?'),
                    {
                        confirm_callback: function() {
                            ajax.jsonRpc('/web/dataset/call_kw', 'call', {
                                model: 'hotel.reservation',
                                method: 'action_check_in',
                                args: [[reservationId]],
                                kwargs: {}
                            }).then(function() {
                                Dialog.alert(_t('Guest checked in successfully!'));
                                location.reload();
                            });
                        }
                    }
                );
            });
        },

        _initRoomAvailability: function() {
            // Real-time room availability check
            $('.hotel-check-availability').on('click', function() {
                var roomTypeId = $(this).data('room-type-id');
                var checkIn = $('#check_in').val();
                var checkOut = $('#check_out').val();
                var adults = $('#adults').val() || 1;
                var children = $('#children').val() || 0;

                if (!checkIn || !checkOut) {
                    Dialog.alert(_t('Please select both check-in and check-out dates.'));
                    return;
                }

                ajax.jsonRpc('/hotel/availability', 'call', {
                    room_type_id: roomTypeId,
                    check_in: checkIn,
                    check_out: checkOut,
                    adults: adults,
                    children: children
                }).then(function(result) {
                    if (result.error) {
                        Dialog.alert(_t(result.error));
                    } else if (result.available) {
                        Dialog.alert(_t(result.available_count + ' rooms available!'));
                    } else {
                        Dialog.alert(_t('No rooms available for the selected dates.'));
                    }
                });
            });
        }
    };

    // Initialize on page load
    $(document).ready(function() {
        Hotel.init();
    });

    return Hotel;
});