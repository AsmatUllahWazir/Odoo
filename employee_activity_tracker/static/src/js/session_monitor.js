/** @odoo-module **/
/**
 * session_monitor.js
 * =====================================================================
 * Session Heartbeat Monitor
 * - Sends a heartbeat every 60 seconds to keep session alive
 * - Detects user idle state (no mouse/keyboard activity)
 * - Tracks idle time and updates session status
 * - Sends final logout signal on page close
 * =====================================================================
 */

import { registry } from "@web/core/registry";
import { session } from "@web/session";

const HEARTBEAT_INTERVAL_MS = 60 * 1000;    // 60 seconds
const IDLE_THRESHOLD_MS = 15 * 60 * 1000;   // 15 minutes

const sessionMonitorService = {
    name: "session_monitor",
    dependencies: ["rpc"],

    async start(env, { rpc }) {
        if (!session.uid) return {};

        let lastActivity = Date.now();
        let isIdle = false;
        let heartbeatTimer = null;
        let sessionId = null;

        // -----------------------------------------------------------------------
        // Activity detector: reset idle timer on any user interaction
        // -----------------------------------------------------------------------
        const ACTIVITY_EVENTS = [
            "mousemove", "mousedown", "keydown",
            "scroll", "touchstart", "click", "focus",
        ];

        function resetActivity() {
            lastActivity = Date.now();
            if (isIdle) {
                isIdle = false;
                // User came back from idle — send heartbeat immediately
                sendHeartbeat();
            }
        }

        ACTIVITY_EVENTS.forEach((evt) => {
            window.addEventListener(evt, resetActivity, { passive: true });
        });

        // -----------------------------------------------------------------------
        // Heartbeat: ping the server every 60 seconds
        // -----------------------------------------------------------------------
        async function sendHeartbeat() {
            const idleMs = Date.now() - lastActivity;
            const currentlyIdle = idleMs >= IDLE_THRESHOLD_MS;

            if (currentlyIdle && !isIdle) {
                isIdle = true;
            }

            try {
                const result = await rpc("/activity_tracker/heartbeat", {
                    is_idle: currentlyIdle,
                    idle_seconds: Math.floor(idleMs / 1000),
                });
                if (result && result.session_id) {
                    sessionId = result.session_id;
                }
            } catch (e) {
                // Heartbeat failures are non-critical
                console.debug("[SessionMonitor] Heartbeat failed:", e);
            }
        }

        // Start heartbeat loop
        async function startHeartbeatLoop() {
            await sendHeartbeat(); // Initial heartbeat on page load
            heartbeatTimer = setInterval(sendHeartbeat, HEARTBEAT_INTERVAL_MS);
        }

        startHeartbeatLoop();

        // -----------------------------------------------------------------------
        // Idle status indicator in the systray (optional visual badge)
        // -----------------------------------------------------------------------
        function getIdleStatus() {
            const idleMs = Date.now() - lastActivity;
            if (idleMs < 5 * 60 * 1000) return "active";
            if (idleMs < IDLE_THRESHOLD_MS) return "active";
            return "idle";
        }

        // -----------------------------------------------------------------------
        // Cleanup on component destroy
        // -----------------------------------------------------------------------
        function cleanup() {
            if (heartbeatTimer) {
                clearInterval(heartbeatTimer);
                heartbeatTimer = null;
            }
            ACTIVITY_EVENTS.forEach((evt) => {
                window.removeEventListener(evt, resetActivity);
            });
        }

        // Expose public API
        return {
            getSessionId: () => sessionId,
            getIdleStatus,
            cleanup,
            sendHeartbeat,
        };
    },
};

registry.category("services").add("session_monitor", sessionMonitorService);

export { sessionMonitorService };