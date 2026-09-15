/** Saudi HR Compliance Hub - lightweight dashboard enhancement. */
odoo.define('saudi_muqeem_workforce_operations.dashboard', function (require) {
    'use strict';
    const AbstractAction = require('web.AbstractAction');
    return AbstractAction.extend({
        start: function () { return this._super.apply(this, arguments); },
    });
});
