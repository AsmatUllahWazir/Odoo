/** @odoo-module **/
/**
 * activity_tracker.js
 * =====================================================================
 * Global Activity Tracking Engine
 * Hooks into Odoo's web client (OWL) to capture:
 *   - Button clicks on all forms
 *   - View changes (form, list, kanban, pivot, graph, calendar)
 *   - Menu navigation
 *   - RPC/ORM operations
 *   - Developer mode toggle
 *   - Page unload (logout detection)
 * Sends events to /activity_tracker/track_event controller.
 * =====================================================================
 */

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { session } from "@web/session";
import { Component, onMounted, onWillUnmount } from "@odoo/owl";

// -------------------------------------------------------------------------
// Utility: Throttle function to avoid flooding the server
// -------------------------------------------------------------------------
function throttle(fn, delay) {
    let lastCall = 0;
    return function (...args) {
        const now = Date.now();
        if (now - lastCall >= delay) {
            lastCall = now;
            return fn.apply(this, args);
        }
    };
}

// -------------------------------------------------------------------------
// Utility: Debounce function
// -------------------------------------------------------------------------
function debounce(fn, delay) {
    let timer;
    return function (...args) {
        clearTimeout(timer);
        timer = setTimeout(() => fn.apply(this, args), delay);
    };
}

// -------------------------------------------------------------------------
// Core Tracker Service
// Registered as a global Odoo service so it's available everywhere
// -------------------------------------------------------------------------
const activityTrackerService = {
    name: "activity_tracker",
    dependencies: ["rpc", "router", "user"],

    async start(env, { rpc, router, user }) {
        // Don't track if not logged in
        if (!session.uid) return {};

        const tracker = {
            _sessionId: null,
            _rpc: rpc,
            _env: env,
            _lastUrl: window.location.href,
            _currentModel: null,
            _currentModule: null,
            _currentViewType: null,

            /**
             * Send a tracking event to the server.
             * Uses fetch for non-blocking async operation.
             */
            async trackEvent(eventType, data = {}) {
                try {
                    await rpc("/activity_tracker/track_event", {
                        event_type: eventType,
                        data: {
                            ...data,
                            url: window.location.href,
                        },
                    });
                } catch (e) {
                    // Silently fail — tracking must never break the main app
                    console.debug("[ActivityTracker] Event send failed:", e);
                }
            },

            /**
             * Track a button click from a form view.
             */
            trackButtonClick(buttonEl, context = {}) {
                const buttonName =
                    buttonEl.getAttribute("name") ||
                    buttonEl.getAttribute("data-method") ||
                    "";
                const buttonString =
                    buttonEl.getAttribute("string") ||
                    buttonEl.textContent?.trim() ||
                    buttonEl.getAttribute("title") ||
                    buttonName;

                if (!buttonString && !buttonName) return;

                // Skip tracking buttons that are purely UI (no server action)
                const skipButtons = ["discard", "edit", "cancel", "close"];
                if (skipButtons.includes(buttonName.toLowerCase())) return;

                this.trackEvent("button_click", {
                    button_name: buttonName,
                    string: buttonString,
                    model: context.model || this._currentModel || "",
                    model_description: context.model_description || "",
                    res_id: context.res_id || 0,
                    record_name: context.record_name || "",
                    module: this._currentModule || "",
                });
            },

            /**
             * Track view change (form → list, etc.)
             */
            trackViewChange(viewType, modelName, modelDescription) {
                if (viewType === this._currentViewType && modelName === this._currentModel) {
                    return; // No change
                }
                this._currentViewType = viewType;
                this._currentModel = modelName || this._currentModel;
                this._currentModule = this._guessModule(modelName);

                const eventTypeMap = {
                    form: "form_open",
                    list: "list_view",
                    kanban: "kanban_view",
                    calendar: "calendar_view",
                    pivot: "pivot_view",
                    graph: "graph_view",
                    activity: "list_view",
                    gantt: "list_view",
                };
                const eventType = eventTypeMap[viewType] || "form_open";

                this.trackEvent(eventType, {
                    view_type: viewType,
                    model: modelName || "",
                    model_description: modelDescription || "",
                    module: this._currentModule,
                });
            },

            /**
             * Track menu item click
             */
            trackMenuAccess(menuName, menuId) {
                this.trackEvent("menu_access", {
                    menu_name: menuName,
                    menu_id: menuId,
                    module: menuName,
                });
            },

            /**
             * Guess Odoo module from model name
             */
            _guessModule(modelName) {
                if (!modelName) return "";
                const moduleMap = {
                    "sale.": "Sales",
                    "purchase.": "Purchase",
                    "stock.": "Inventory",
                    "account.": "Accounting",
                    "crm.": "CRM",
                    "hr.": "HR/Employees",
                    "mrp.": "Manufacturing",
                    "project.": "Project",
                    "website.": "Website",
                    "pos.": "Point of Sale",
                    "helpdesk.": "Helpdesk",
                    "fleet.": "Fleet",
                    "maintenance.": "Maintenance",
                };
                for (const [prefix, module] of Object.entries(moduleMap)) {
                    if (modelName.startsWith(prefix)) return module;
                }
                return modelName.split(".")[0].charAt(0).toUpperCase() +
                       modelName.split(".")[0].slice(1);
            },
        };

        // -------------------------------------------------------------------------
        // DOM-level button click tracking (catches all button clicks globally)
        // -------------------------------------------------------------------------
        const handleButtonClick = throttle(function (event) {
            const target = event.target.closest(
                "button[name], button[data-method], .o_statusbar_status button, " +
                ".o_form_button_save, button.btn-primary, button.btn-secondary"
            );
            if (!target) return;

            // Skip pure UI buttons (pagination, toggle columns, etc.)
            const skipClasses = [
                "o_pager_", "o_optional_columns_dropdown", "o_group_header",
                "o_cp_", "o_dropdown_", "o_list_optional",
            ];
            const classList = target.className || "";
            if (skipClasses.some((c) => classList.includes(c))) return;

            tracker.trackButtonClick(target, {
                model: tracker._currentModel,
                module: tracker._currentModule,
            });
        }, 500);

        document.addEventListener("click", handleButtonClick, { passive: true });

        // -------------------------------------------------------------------------
        // Developer mode detection
        // -------------------------------------------------------------------------
        const checkDevMode = debounce(function () {
            const isDevMode =
                window.location.search.includes("debug=1") ||
                window.location.search.includes("debug=assets") ||
                window.location.search.includes("debug=tests");
            tracker.trackEvent("developer_mode", { enabled: isDevMode });
        }, 2000);

        // Watch URL for debug mode changes
        const originalPushState = history.pushState;
        history.pushState = function (...args) {
            originalPushState.apply(this, args);
            const newUrl = window.location.href;
            if (newUrl !== tracker._lastUrl) {
                tracker._lastUrl = newUrl;
                checkDevMode();
            }
        };

        // -------------------------------------------------------------------------
        // Page unload: track logout/close
        // -------------------------------------------------------------------------
        window.addEventListener("beforeunload", function () {
            // Use sendBeacon for reliable delivery on page close
            const payload = JSON.stringify({
                jsonrpc: "2.0",
                method: "call",
                params: {
                    event_type: "logout",
                    data: { url: window.location.href },
                },
            });
            navigator.sendBeacon(
                "/activity_tracker/track_event",
                new Blob([payload], { type: "application/json" })
            );
        });

        // -------------------------------------------------------------------------
        // Expose tracker on the env for use by other components/patches
        // -------------------------------------------------------------------------
        env.activityTracker = tracker;

        return tracker;
    },
};

registry.category("services").add("activity_tracker", activityTrackerService);

// -------------------------------------------------------------------------
// Patch ActionService to detect view changes
// Hooks into Odoo's action manager to know which model/view is active
// -------------------------------------------------------------------------
import { ActionService } from "@web/webclient/actions/action_service";

patch(ActionService.prototype, {
    async _handleAction(action, options) {
        const result = await super._handleAction(action, options);
        try {
            const tracker = this.env?.activityTracker;
            if (tracker && action) {
                if (action.type === "ir.actions.act_window") {
                    const viewMode = options?.viewType ||
                        (action.view_mode || "").split(",")[0] ||
                        "list";
                    tracker.trackViewChange(
                        viewMode,
                        action.res_model,
                        action.name
                    );
                }
            }
        } catch (e) {
            // Silently ignore tracking errors
        }
        return result;
    },
});

export { activityTrackerService };