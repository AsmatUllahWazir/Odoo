/** @odoo-module **/

import { registry } from "@web/core/registry";
import {
    Component,
    onWillStart,
    onMounted,
    onWillUnmount,
    useState,
    useRef,
    xml,
} from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

const INACTIVITY_TIMEOUT_MS = 120000;
const DEBOUNCE_MS = 1500;

export class StockBarcodeScannerPro extends Component {
    static template = xml`
        <div class="o_barcode_scanner_pro">
            <div class="scanner-scroll">

                <div class="scanner-header">
                    <div class="scanner-title">
                        <h3>Scan: <t t-esc="state.pickingName"/></h3>
                        <p class="text-muted mb-0">
                            <t t-esc="state.partner"/>
                            <span t-if="state.origin"> - <t t-esc="state.origin"/></span>
                            <span t-if="state.state" class="badge bg-info ms-2"><t t-esc="state.state"/></span>
                        </p>
                    </div>
                    <div class="scanner-status">
                        <span t-if="state.scanning" class="status-dot status-live"/>
                        <span t-if="!state.scanning" class="status-dot status-off"/>
                        <span t-esc="state.scanning ? 'Camera ON' : 'Camera OFF'"/>
                    </div>
                </div>

                <div class="scanner-camera-wrap">
                    <div t-ref="reader" id="scanner-reader" class="scanner-reader"/>
                    <div t-if="state.flash" class="scanner-flash"/>
                    <div t-if="showScanOverlay" class="scanner-overlay">
                        <div class="scanner-overlay-text">
                            <t t-esc="state.lastScan.product_name"/>
                            <div class="scanner-overlay-qty">
                                <t t-esc="state.lastScan.new_quantity"/> <t t-esc="state.lastScan.uom"/>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="scanner-controls">
                    <button t-if="!state.scanning"
                            t-on-click="startScanner"
                            class="btn btn-primary btn-lg w-100 mb-2">
                        📷 Start Camera
                    </button>
                    <button t-if="state.scanning"
                            t-on-click="stopScanner"
                            class="btn btn-secondary btn-lg w-100 mb-2">
                        ⏹ Stop Camera
                    </button>
                    <button t-on-click="validatePicking"
                            class="btn btn-success btn-lg w-100 mb-2"
                            t-att-disabled="isValidateDisabled">
                        ✅ Validate Picking
                    </button>
                    <button t-on-click="resetLog"
                            class="btn btn-outline-secondary btn-sm w-100">
                        Clear log
                    </button>
                </div>

                <div class="scanner-manual mt-3">
                    <label class="form-label">Manual barcode entry:</label>
                    <div class="input-group">
                        <input type="text"
                               class="form-control"
                               placeholder="Type barcode and press Enter"
                               t-model="state.manualBarcode"
                               t-on-keydown="onManualKeydown"/>
                        <button class="btn btn-outline-secondary" t-on-click="submitManual">Add</button>
                    </div>
                </div>

                <div class="scanner-log mt-3">
                    <div class="scanner-log-title">
                        Scan Log
                        <span class="badge bg-secondary"><t t-esc="state.log.length"/></span>
                    </div>
                    <t t-if="state.log.length === 0">
                        <div class="text-muted small py-2">No scans yet.</div>
                    </t>
                    <t t-foreach="state.log" t-as="entry" t-key="entry.id">
                        <div t-att-class="logEntryClass(entry)">
                            <span class="log-time"><t t-esc="entry.time"/></span>
                            <span class="log-msg"><t t-esc="entry.message"/></span>
                        </div>
                    </t>
                </div>

                <div class="scanner-lines mt-4">
                    <div class="scanner-lines-title">
                        Lines
                        <span class="badge bg-secondary"><t t-esc="state.lines.length"/></span>
                    </div>
                    <div class="table-responsive">
                        <table class="table table-sm">
                            <thead>
                                <tr>
                                    <th>Product</th>
                                    <th class="text-end">Demand</th>
                                    <th class="text-end">Done</th>
                                    <th>UoM</th>
                                </tr>
                            </thead>
                            <tbody>
                                <t t-foreach="state.lines" t-as="line" t-key="line.move_id">
                                    <tr t-att-class="lineRowClass(line)">
                                        <td><t t-esc="line.product_name"/></td>
                                        <td class="text-end"><t t-esc="line.demand"/></td>
                                        <td class="text-end"><strong><t t-esc="line.quantity"/></strong></td>
                                        <td><t t-esc="line.uom"/></td>
                                    </tr>
                                </t>
                            </tbody>
                        </table>
                    </div>
                </div>

                <div class="scanner-footer-hint">
                    <t t-if="state.scanning">
                        Camera will auto-stop after 2 minutes of inactivity.
                    </t>
                    <t t-else="">
                        Tap "Start Camera" to begin scanning.
                    </t>
                </div>
            </div>
        </div>
    `;

    setup() {
        this.orm = useService("orm");
        this.rpc = useService("rpc");
        this.notification = useService("notification");

        this.state = useState({
            pickingId: this.props.action.params.picking_id,
            pickingName: "",
            partner: "",
            origin: "",
            state: "",
            lines: [],
            scanning: false,
            log: [],
            manualBarcode: "",
            loading: true,
            flash: false,
            lastScan: null,
            highlightMoveId: null,
        });

        this.readerRef = useRef("reader");
        this.html5Qrcode = null;
        this._lastScan = null;
        this._inactivityTimer = null;
        this._flashTimer = null;
        this._highlightTimer = null;
        this._logId = 0;
        this._audioCtx = null;

        onWillStart(async () => {
            await this.loadPickingState();
        });

        onMounted(() => {
            this._visibilityHandler = () => {
                if (document.hidden && this.state.scanning) {
                    this.stopScanner();
                }
            };
            document.addEventListener("visibilitychange", this._visibilityHandler);
        });

        onWillUnmount(() => {
            document.removeEventListener("visibilitychange", this._visibilityHandler);
            this._clearTimers();
            this.stopScanner();
        });
    }

    // -------- computed helpers (no logic in template) --------

    get showScanOverlay() {
        return !!(this.state.lastScan && this.state.flash);
    }

    get isValidateDisabled() {
        return this.state.state === "done" || this.state.state === "cancel";
    }

    logEntryClass(entry) {
        return "scanner-log-entry log-" + entry.level;
    }

    lineRowClass(line) {
        const classes = ["line-row"];
        if (line.quantity >= line.demand) {
            classes.push("line-complete");
        }
        if (this.state.highlightMoveId === line.move_id) {
            classes.push("line-highlight");
        }
        return classes.join(" ");
    }

    // -------- lifecycle helpers --------

    _clearTimers() {
        if (this._inactivityTimer) clearTimeout(this._inactivityTimer);
        if (this._flashTimer) clearTimeout(this._flashTimer);
        if (this._highlightTimer) clearTimeout(this._highlightTimer);
        this._inactivityTimer = null;
        this._flashTimer = null;
        this._highlightTimer = null;
    }

    _resetInactivityTimer() {
        if (this._inactivityTimer) clearTimeout(this._inactivityTimer);
        if (!this.state.scanning) return;
        this._inactivityTimer = setTimeout(() => {
            this.addLog(_t("Camera stopped after 2 minutes of inactivity."), "warning");
            this.stopScanner();
        }, INACTIVITY_TIMEOUT_MS);
    }

    // -------- data loading --------

    async loadPickingState() {
        try {
            const data = await this.orm.read(
                "stock.picking",
                [this.state.pickingId],
                ["name", "partner_id", "origin", "state"]
            );
            if (data && data.length) {
                this.state.pickingName = data[0].name;
                this.state.partner = data[0].partner_id ? data[0].partner_id[1] : "";
                this.state.origin = data[0].origin || "";
                this.state.state = data[0].state;
            }
            await this.refreshLines();
        } catch (e) {
            this.notification.add(_t("Could not load picking: ") + e.message, {
                type: "danger",
            });
        } finally {
            this.state.loading = false;
        }
    }

    async refreshLines() {
        const data = await this.rpc(
            "/stock_barcode_scanner_pro/picking/" + this.state.pickingId + "/state",
            {}
        );
        this.state.lines = data.lines || [];
        this.state.state = data.state;
        this.state.pickingName = data.picking_name;
        this.state.partner = data.partner;
        this.state.origin = data.origin;
    }

    // -------- camera --------

    async startScanner() {
        if (typeof Html5Qrcode === "undefined") {
            this.notification.add(_t("Barcode library not loaded."), { type: "danger" });
            return;
        }
        if (this.state.scanning) return;

        const readerEl = this.readerRef.el;
        readerEl.innerHTML = "";

        this.html5Qrcode = new Html5Qrcode(readerEl.id, { verbose: false });

        this.state.scanning = true;
        try {
            await this.html5Qrcode.start(
                { facingMode: "environment" },
                {
                    fps: 10,
                    qrbox: (vw, vh) => {
                        const size = Math.floor(Math.min(vw, vh) * 0.7);
                        return { width: size, height: size };
                    },
                    aspectRatio: 1.0,
                    disableFlip: false,
                },
                (decodedText) => this.onScanSuccess(decodedText),
                () => {}
            );

            const video = readerEl.querySelector("video");
            if (video) {
                video.style.width = "100%";
                video.style.height = "100%";
                video.style.objectFit = "cover";
                video.style.display = "block";
            }
            const canvas = readerEl.querySelector("canvas");
            if (canvas) {
                canvas.style.position = "absolute";
                canvas.style.top = "0";
                canvas.style.left = "0";
                canvas.style.width = "100%";
                canvas.style.height = "100%";
                canvas.style.pointerEvents = "none";
            }

            this._resetInactivityTimer();
            this.addLog(_t("Camera started."), "info");
        } catch (err) {
            this.state.scanning = false;
            this.html5Qrcode = null;
            this.notification.add(_t("Camera error: ") + err, { type: "danger" });
            this.addLog(_t("Camera error: ") + err, "danger");
        }
    }

    async stopScanner() {
        if (this.html5Qrcode) {
            try {
                await this.html5Qrcode.stop();
                await this.html5Qrcode.clear();
            } catch (e) {
                // already stopped
            }
            this.html5Qrcode = null;
        }
        this.state.scanning = false;
        if (this._inactivityTimer) {
            clearTimeout(this._inactivityTimer);
            this._inactivityTimer = null;
        }
    }

    // -------- scanning --------

    async onScanSuccess(decodedText) {
        const now = Date.now();
        if (
            this._lastScan &&
            this._lastScan.text === decodedText &&
            now - this._lastScan.time < DEBOUNCE_MS
        ) {
            return;
        }
        this._lastScan = { text: decodedText, time: now };
        await this.processBarcode(decodedText);
        this._resetInactivityTimer();
    }

    async processBarcode(barcode) {
        let result;
        try {
            result = await this.rpc("/stock_barcode_scanner_pro/scan", {
                picking_id: this.state.pickingId,
                barcode: barcode,
                increment: 1.0,
            });
        } catch (e) {
            this.addLog(_t("Error: ") + e.message, "danger");
            this.feedback("error");
            return;
        }

        if (!result.success) {
            this.addLog(result.message || _t("Scan failed."), "warning");
            this.feedback("warning");
            return;
        }

        this.addLog(
            result.product_name + " → " + result.new_quantity + " " + result.uom,
            "success"
        );
        this.feedback("success", {
            product_name: result.product_name,
            new_quantity: result.new_quantity,
            uom: result.uom,
            move_line_id: result.move_line_id,
        });
        await this.refreshLines();
    }

    // -------- feedback --------

    feedback(kind, data) {
        this.state.lastScan = data || null;
        this.state.flash = true;
        if (this._flashTimer) clearTimeout(this._flashTimer);
        this._flashTimer = setTimeout(() => {
            this.state.flash = false;
        }, 600);

        if (data && data.move_line_id) {
            const line = this.state.lines.find((l) =>
                l.move_lines.some((ml) => ml.move_line_id === data.move_line_id)
            );
            if (line) {
                this.state.highlightMoveId = line.move_id;
                if (this._highlightTimer) clearTimeout(this._highlightTimer);
                this._highlightTimer = setTimeout(() => {
                    this.state.highlightMoveId = null;
                }, 1200);
            }
        }

        try {
            if (kind === "success") {
                this._beep(880, 0.08);
                if (navigator.vibrate) navigator.vibrate(60);
            } else if (kind === "warning") {
                this._beep(440, 0.12);
                if (navigator.vibrate) navigator.vibrate([30, 40, 30]);
            } else {
                this._beep(220, 0.2);
                if (navigator.vibrate) navigator.vibrate(200);
            }
        } catch (e) {
            // audio might be blocked until a user gesture — ignore
        }
    }

    _beep(freq, duration) {
        const Ctx = window.AudioContext || window.webkitAudioContext;
        if (!Ctx) return;
        if (!this._audioCtx) this._audioCtx = new Ctx();
        const ctx = this._audioCtx;
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.frequency.value = freq;
        osc.type = "sine";
        gain.gain.value = 0.15;
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start();
        osc.stop(ctx.currentTime + duration);
    }

    // -------- manual entry & misc --------

    async submitManual() {
        const barcode = this.state.manualBarcode.trim();
        if (!barcode) return;
        this.state.manualBarcode = "";
        await this.processBarcode(barcode);
    }

    onManualKeydown(ev) {
        if (ev.key === "Enter") {
            ev.preventDefault();
            this.submitManual();
        }
    }

    resetLog() {
        this.state.log = [];
    }

    async validatePicking() {
        try {
            const result = await this.rpc("/stock_barcode_scanner_pro/validate", {
                picking_id: this.state.pickingId,
            });
            if (result.success) {
                this.notification.add(result.message, { type: "success" });
                this.addLog(result.message, "success");
                await this.refreshLines();
                if (this.state.scanning) this.stopScanner();
            } else {
                this.notification.add(result.message, { type: "warning" });
                this.addLog(result.message, "warning");
            }
        } catch (e) {
            this.notification.add(e.message, { type: "danger" });
            this.addLog(e.message, "danger");
        }
    }

    addLog(message, level) {
        this.state.log.unshift({
            id: ++this._logId,
            message,
            level,
            time: new Date().toLocaleTimeString(),
        });
        if (this.state.log.length > 50) this.state.log.pop();
    }
}

registry.category("actions").add("stock_barcode_scanner_pro", StockBarcodeScannerPro);