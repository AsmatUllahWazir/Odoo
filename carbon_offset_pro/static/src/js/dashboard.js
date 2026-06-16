odoo.define('carbon_offset_pro.dashboard', function (require) {
    "use strict";

    var AbstractField = require('web.AbstractField');
    var fieldRegistry = require('web.field_registry');
    var core = require('web.core');
    var _t = core._t;

    var SustainabilityChartWidget = AbstractField.extend({
        init: function () {
            this._super.apply(this, arguments);
        },
        _render: function () {
            if (!this.value) return;
            console.log('Dashboard rendered with data:', this.value);
        }
    });

    fieldRegistry.add('sustainability_chart', SustainabilityChartWidget);

    return {
        SustainabilityChartWidget: SustainabilityChartWidget
    };
});