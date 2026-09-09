/** @odoo-module **/

(function () {
    "use strict";

    const POLL_INTERVAL = 60000;
    const SELECTORS = {
        root: "[data-delivery-token]",
        status: "[data-delivery-status]",
        updated: "[data-delivery-updated]",
        progress: "[data-delivery-progress]",
        progressLabel: "[data-delivery-progress-label]",
        location: "[data-delivery-location]",
        error: "[data-delivery-error]",
        refresh: "[data-delivery-refresh]",
        copy: "[data-delivery-copy]",
        geolocation: "[data-delivery-geolocation]",
    };

    function query(selector, root = document) {
        return root.querySelector(selector);
    }

    function queryAll(selector, root = document) {
        return Array.from(root.querySelectorAll(selector));
    }

    function getRoot() {
        return query(SELECTORS.root);
    }

    function getToken(root) {
        return root ? root.dataset.deliveryToken : "";
    }

    function endpoint(token) {
        return `/delivery/track/${encodeURIComponent(token)}/json`;
    }

    function jsonRpcBody() {
        return JSON.stringify({jsonrpc: "2.0", method: "call", params: {}});
    }

    async function fetchTracking(token) {
        const response = await fetch(endpoint(token), {
            method: "POST",
            credentials: "same-origin",
            headers: {"Content-Type": "application/json"},
            body: jsonRpcBody(),
        });
        if (!response.ok) {
            throw new Error(`Tracking request failed: ${response.status}`);
        }
        const payload = await response.json();
        const result = payload.result || payload;
        if (!result || result.error) {
            throw new Error(result && result.error ? result.error : "Tracking information is unavailable.");
        }
        return result;
    }

    function setText(selector, value) {
        const node = query(selector);
        if (node && value !== undefined && value !== null) {
            node.textContent = String(value);
        }
    }

    function setVisible(selector, visible) {
        queryAll(selector).forEach((node) => {
            node.hidden = !visible;
        });
    }

    function normalizeStatus(status) {
        return String(status || "").toLowerCase().replace(/[^a-z0-9_]+/g, "_");
    }

    function statusClass(status) {
        const normalized = normalizeStatus(status);
        if (["delivered"].includes(normalized)) {
            return "dfp-badge-success";
        }
        if (["failed", "cancelled"].includes(normalized)) {
            return "dfp-badge-danger";
        }
        if (["partial"].includes(normalized)) {
            return "dfp-badge-warning";
        }
        return "dfp-badge-info";
    }

    function applyStatus(result) {
        const status = normalizeStatus(result.status);
        queryAll(SELECTORS.status).forEach((node) => {
            node.textContent = result.status_label || result.status || "Unknown";
            node.classList.remove("dfp-badge-success", "dfp-badge-warning", "dfp-badge-danger", "dfp-badge-info");
            node.classList.add(statusClass(status));
        });
        document.body.dataset.deliveryStatus = status;
    }

    function applyUpdatedAt(result) {
        if (!result.updated_at) {
            return;
        }
        setText(SELECTORS.updated, formatDate(result.updated_at));
    }

    function formatDate(value) {
        const date = new Date(value);
        if (Number.isNaN(date.getTime())) {
            return value;
        }
        return new Intl.DateTimeFormat(undefined, {
            dateStyle: "medium",
            timeStyle: "short",
        }).format(date);
    }

    function applyLocation(result) {
        if (!result.latitude || !result.longitude) {
            setVisible(SELECTORS.location, false);
            return;
        }
        setVisible(SELECTORS.location, true);
        setText(SELECTORS.location, `${Number(result.latitude).toFixed(6)}, ${Number(result.longitude).toFixed(6)}`);
    }

    function applyProgress(result) {
        if (!result.delivered_count || !result.stop_count) {
            return;
        }
        const percent = Math.max(0, Math.min(100, Number(result.delivered_count) / Number(result.stop_count) * 100));
        queryAll(SELECTORS.progress).forEach((node) => {
            node.style.width = `${percent}%`;
            node.setAttribute("aria-valuenow", String(Math.round(percent)));
        });
        setText(SELECTORS.progressLabel, `${result.delivered_count} / ${result.stop_count}`);
    }

    function showError(message) {
        const node = query(SELECTORS.error);
        if (!node) {
            return;
        }
        node.textContent = message;
        node.hidden = false;
    }

    function clearError() {
        const node = query(SELECTORS.error);
        if (node) {
            node.textContent = "";
            node.hidden = true;
        }
    }

    function setRefreshing(refreshing) {
        queryAll(SELECTORS.refresh).forEach((button) => {
            button.disabled = refreshing;
            button.setAttribute("aria-busy", refreshing ? "true" : "false");
            const label = button.querySelector("[data-refresh-label]");
            if (label) {
                label.textContent = refreshing ? "Refreshing…" : "Refresh status";
            }
        });
    }

    async function refreshTracking() {
        const root = getRoot();
        if (!root) {
            return;
        }
        const token = getToken(root);
        if (!token) {
            showError("Tracking token is missing.");
            return;
        }
        setRefreshing(true);
        try {
            clearError();
            const result = await fetchTracking(token);
            applyStatus(result);
            applyUpdatedAt(result);
            applyLocation(result);
            applyProgress(result);
            document.dispatchEvent(new CustomEvent("delivery-tracking-updated", {detail: result}));
        } catch (error) {
            showError(error.message || "Unable to refresh delivery status.");
        } finally {
            setRefreshing(false);
        }
    }

    async function copyTrackingUrl(button) {
        const root = getRoot();
        const token = getToken(root);
        if (!token || !navigator.clipboard) {
            return;
        }
        const url = `${window.location.origin}/delivery/track/${encodeURIComponent(token)}`;
        try {
            await navigator.clipboard.writeText(url);
            const original = button.textContent;
            button.textContent = "Copied";
            window.setTimeout(() => { button.textContent = original; }, 1600);
        } catch (error) {
            showError("The tracking link could not be copied.");
        }
    }

    function requestBrowserLocation() {
        if (!navigator.geolocation) {
            return;
        }
        navigator.geolocation.getCurrentPosition(
            (position) => {
                queryAll(SELECTORS.geolocation).forEach((node) => {
                    node.textContent = `${position.coords.latitude.toFixed(6)}, ${position.coords.longitude.toFixed(6)}`;
                });
            },
            () => {},
            {enableHighAccuracy: false, maximumAge: 300000, timeout: 5000},
        );
    }

    function bindActions() {
        queryAll(SELECTORS.refresh).forEach((button) => {
            button.addEventListener("click", (event) => {
                event.preventDefault();
                refreshTracking();
            });
        });
        queryAll(SELECTORS.copy).forEach((button) => {
            button.addEventListener("click", (event) => {
                event.preventDefault();
                copyTrackingUrl(button);
            });
        });
        queryAll(SELECTORS.geolocation).forEach((node) => {
            node.addEventListener("click", requestBrowserLocation);
        });
    }

    function startPolling() {
        const root = getRoot();
        if (!root) {
            return;
        }
        window.setInterval(() => {
            if (document.visibilityState === "visible") {
                refreshTracking();
            }
        }, POLL_INTERVAL);
    }

    document.addEventListener("DOMContentLoaded", () => {
        bindActions();
        refreshTracking();
        startPolling();
    });
})();
