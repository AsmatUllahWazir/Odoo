odoo.define('salon_spa_management.pos_salon', function(require) {
    "use strict";

    var PosBase = require('point_of_sale.Base');
    var PopupWidget = require('point_of_sale.PopupWidget');
    var Gui = require('point_of_sale.Gui');
    var core = require('web.core');
    var _t = core._t;

    // Extend POS Model
    var PosModel = require('point_of_sale.PosModel');
    PosModel.include({
        init: function(parent, options) {
            this._super(parent, options);
            this.salon_appointments = [];
        },
        loadAppointments: function() {
            var self = this;
            var session = this.get('selectedSession');
            if (!session) return;
            var appointments = this.db.get_salon_appointments(session.id);
            this.salon_appointments = appointments;
            return this;
        }
    });

    // Extend POS DB
    var PosDB = require('point_of_sale.DB');
    PosDB.include({
        get_salon_appointments: function(session_id) {
            var self = this;
            return new Promise(function(resolve) {
                var appointments = self.models.salon_appointment;
                if (appointments) {
                    resolve(appointments.filter(function(a) {
                        return a.state === 'confirmed' || a.state === 'checked_in' || a.state === 'in_progress';
                    }));
                } else {
                    resolve([]);
                }
            });
        }
    });

    // Extend POS Screen
    var PosScreen = require('point_of_sale.Screen');
    PosScreen.include({
        renderElement: function() {
            var self = this;
            this._super();
            if (this.pos.config.salon_enabled) {
                this.loadSalonData();
            }
        },
        loadSalonData: function() {
            var self = this;
            this.pos.loadAppointments().then(function() {
                self.renderSalonSidebar();
            });
        },
        renderSalonSidebar: function() {
            var self = this;
            var sidebar = this.$el.find('.pos-salon-sidebar');
            if (sidebar.length) {
                sidebar.html('');
                this.pos.salon_appointments.forEach(function(appointment) {
                    var item = $('<div class="pos-appointment-item">');
                    // Create appointment item HTML
                    var info = $('<div class="appointment-info">');
                    info.append('<strong>' + appointment.customer_id[1] + '</strong>');
                    var badge = $('<span class="badge">' + appointment.state + '</span>');
                    info.append(badge);

                    var details = $('<div class="appointment-details">');
                    details.append(appointment.employee_id[1]);
                    details.append(' - ');
                    if (appointment.service_ids) {
                        appointment.service_ids.forEach(function(service) {
                            details.append(service[1] + ' ');
                        });
                    }
                    info.append(details);

                    var time = $('<div class="appointment-time">');
                    time.append(appointment.appointment_date);
                    info.append(time);

                    var actions = $('<div class="appointment-actions">');
                    var checkinBtn = $('<button class="btn btn-sm btn-success">Check In</button>');
                    checkinBtn.on('click', function() {
                        self.checkInAppointment(appointment);
                    });
                    actions.append(checkinBtn);

                    var cancelBtn = $('<button class="btn btn-sm btn-danger">Cancel</button>');
                    cancelBtn.on('click', function() {
                        self.cancelAppointment(appointment);
                    });
                    actions.append(cancelBtn);

                    item.append(info);
                    item.append(actions);
                    sidebar.append(item);
                });
            }
        },
        checkInAppointment: function(appointment) {
            var self = this;
            this.rpc({
                model: 'salon.appointment',
                method: 'action_check_in',
                args: [[appointment.id]]
            }).then(function() {
                self.gui.show_popup('confirm', {
                    title: _t('Success'),
                    body: _t('Customer checked in successfully.'),
                });
                self.loadSalonData();
            });
        },
        cancelAppointment: function(appointment) {
            var self = this;
            this.gui.show_popup('confirm', {
                title: _t('Cancel Appointment'),
                body: _t('Are you sure you want to cancel this appointment?'),
                confirm: function() {
                    self.rpc({
                        model: 'salon.appointment',
                        method: 'action_cancel',
                        args: [[appointment.id]]
                    }).then(function() {
                        self.gui.show_popup('confirm', {
                            title: _t('Success'),
                            body: _t('Appointment cancelled successfully.'),
                        });
                        self.loadSalonData();
                    });
                }
            });
        }
    });

    // Add Appointment Popup
    var SalonAppointmentPopup = PopupWidget.extend({
        template: 'SalonAppointmentPopup',
        init: function(parent, options) {
            this._super(parent, options);
            this.appointment = {
                customer_id: false,
                service_ids: [],
                employee_id: false,
                appointment_date: false,
            };
            this.customers = this.pos.db.get_partners();
            this.services = this.pos.db.get_services();
            this.staff = this.pos.db.get_employees();
        },
        saveAppointment: function() {
            var self = this;
            var appointmentData = {
                customer_id: this.appointment.customer_id,
                service_ids: [[6, 0, this.appointment.service_ids]],
                employee_id: this.appointment.employee_id,
                appointment_date: this.appointment.appointment_date,
            };
            this.rpc({
                model: 'salon.appointment',
                method: 'create',
                args: [appointmentData]
            }).then(function(result) {
                self.gui.show_popup('confirm', {
                    title: _t('Success'),
                    body: _t('Appointment created successfully.'),
                });
                self.close();
            });
        }
    });

    // Register popup
    Gui.include({
        _popup_widgets: {
            'salon_appointment_popup': SalonAppointmentPopup,
        },
    });

    return {
        SalonAppointmentPopup: SalonAppointmentPopup,
    };
});