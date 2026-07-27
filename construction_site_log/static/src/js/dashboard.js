/** @odoo-module **/

import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class ConstructionDashboard extends Component {
    setup() {
        this.action = useService("action");
    }

    _onButtonClick(ev) {
        ev.preventDefault();
        const action = ev.currentTarget.dataset.action;
        if (action) {
            this.action.doAction(action);
        }
    }
}

ConstructionDashboard.template = "construction_site_log.ConstructionDashboard";
ConstructionDashboard.components = {};

// Register the dashboard component
registry.category("actions").add("construction_dashboard", ConstructionDashboard);