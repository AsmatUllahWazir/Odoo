/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class SmartInventoryDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.state = useState({
            loading: true,
            error: null,
            totalProducts: 0,
            deadStockCount: 0,
            totalValue: 0,
            deadStockValue: 0,
            highPriorityCount: 0,
            agingBuckets: {
                "0_30": 0,
                "31_60": 0,
                "61_90": 0,
                "90_plus": 0,
                "no_move": 0,
            },
            topDead: [],
            topReorder: [],
        });

        onWillStart(async () => {
            await this.loadDashboardData();
        });
    }

    async loadDashboardData() {
        this.state.loading = true;
        this.state.error = null;
        try {
            const products = await this.orm.searchRead(
                "product.product",
                [
                    ["type", "in", ["product", "consu"]],
                    ["qty_available", ">", 0],
                ],
                [
                    "id", "name", "default_code", "qty_available", "standard_price",
                    "stock_value_aging", "is_dead_stock", "aging_bucket",
                    "dead_stock_score", "reorder_priority", "suggested_reorder_qty",
                    "days_since_last_move",
                ],
                { order: "dead_stock_score desc", limit: 500 }
            );

            let totalValue = 0;
            let deadValue = 0;
            let deadCount = 0;
            let highPriority = 0;
            const buckets = { "0_30": 0, "31_60": 0, "61_90": 0, "90_plus": 0, "no_move": 0 };
            const deadList = [];
            const reorderList = [];

            for (const p of products) {
                const val = p.stock_value_aging || (p.qty_available * (p.standard_price || 0));
                totalValue += val;

                if (p.is_dead_stock) {
                    deadCount += 1;
                    deadValue += val;
                    deadList.push(p);
                }
                if (p.reorder_priority === "high" || p.reorder_priority === "critical") {
                    highPriority += 1;
                    reorderList.push(p);
                }
                if (p.aging_bucket && buckets.hasOwnProperty(p.aging_bucket)) {
                    buckets[p.aging_bucket] += 1;
                }
            }

            // Sort and limit top lists
            deadList.sort((a, b) => (b.dead_stock_score || 0) - (a.dead_stock_score || 0));
            reorderList.sort((a, b) => {
                const prio = { critical: 4, high: 3, medium: 2, low: 1, none: 0 };
                return (prio[b.reorder_priority] || 0) - (prio[a.reorder_priority] || 0);
            });

            this.state.totalProducts = products.length;
            this.state.deadStockCount = deadCount;
            this.state.totalValue = totalValue.toFixed(2);
            this.state.deadStockValue = deadValue.toFixed(2);
            this.state.highPriorityCount = highPriority;
            this.state.agingBuckets = buckets;
            this.state.topDead = deadList.slice(0, 8);
            this.state.topReorder = reorderList.slice(0, 8);
            this.state.loading = false;
        } catch (err) {
            console.error("Smart Inventory Dashboard error:", err);
            this.state.error = err.message || "Failed to load dashboard data";
            this.state.loading = false;
        }
    }

    getBucketLabel(key) {
        const labels = {
            "0_30": "0-30 Days",
            "31_60": "31-60 Days",
            "61_90": "61-90 Days",
            "90_plus": "90+ Days",
            "no_move": "No Movement",
        };
        return labels[key] || key;
    }
}

SmartInventoryDashboard.template = "smart_inventory_analytics.Dashboard";

// Accept the props that Odoo client actions automatically inject
SmartInventoryDashboard.props = {
    "*": true,   // allow any extra props (action, actionId, className, etc.)
};

registry.category("actions").add("smart_inventory_dashboard", SmartInventoryDashboard);
