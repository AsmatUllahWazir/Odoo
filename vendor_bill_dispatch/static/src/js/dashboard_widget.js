/** @odoo-module **/

// Vendor Bill Dispatch Dashboard Widget
// Placeholder for custom dashboard JavaScript functionality

import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";

class DispatchDashboard extends Component {
    setup() {
        // Dashboard setup code
    }
}

DispatchDashboard.template = "vendor_bill_dispatch.Dashboard";

// Register the widget
registry.category("actions").add("dispatch_dashboard", DispatchDashboard);