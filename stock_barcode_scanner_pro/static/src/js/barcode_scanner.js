/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onWillStart, onMounted, onWillUnmount, useState, useRef, xml } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

export class StockBarcodeScannerPro extends Component {
    static template = xml`
        <div class="o_barcode_scanner_pro">
            <div class="scanner-header">
                <h3>Scan: <t t-esc="state.pickingName"/></h3>
                <p class="text-muted">
                    <t t-esc="state.partner"/> - <t t-esc="state.origin"/>
                    <span t-if="state.state" class="badge bg-info ms-2"><t t-esc="state.state"/></span>
                </p>
            </div>

            <div t-ref="reader" id="scanner-reader" class="scanner-reader"></div>

            <div class="scanner-controls">
                <button t-if="!state.scanning" t-on-click="startScanner" class="btn btn-primary btn-lg w-100 mb-2">
                    Start Camera
                </button>
                <button t-if="state.scanning" t-on-click="stopScanner" class="btn btn-secondary btn-lg w-100 mb-2">
                    Stop Camera
                </button>
                <button t-on-click="validatePicking"
                        class="btn btn-success btn-lg w-100 mb-2"
                        t-att-disabled="state.state === 'done' or state.state === 'cancel'">
                    Validate Picking
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
                <t t-foreach="state.log" t-as="entry" t-key="entry.time + entry.message">
                    <div t-attf-class="alert alert-#{entry.level} py-1 px-2 mb-1">
                        <small><t t-esc="entry.time"/></small> - <t t-esc="entry.message"/>
                    </div>
                </t>
            </div>

            <div class="scanner-lines mt-4">
                <h4>Lines</h4>
                <table class="table table-sm">
                    <thead>
                        <tr>
                            <th>Product</th>
                            <th>Demand</th>
                            <th>Done</th>
                            <th>UoM</th>
                        </tr>
                    </thead>
                    <tbody>
                        <t t-foreach="state.lines" t-as="line" t-key="line.move_id">
                            <tr>
                                <td><t t-esc="line.product_name"/></td>
                                <td><t t-esc="line.demand"/></td>
                                <td><t t-esc="line.quantity"/></td>
                                <td><t t-esc="line.uom"/></td>
                            </tr>
                        </t>
                    </tbody>
                </table>
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
        });

        this.readerRef = useRef("reader");
        this.html5Qrcode = null;

        onWillStart(async () => {
            await this.loadPickingState();
        });

        onMounted(() => {
        });

        onWillUnmount(() => {
            this.stopScanner();
        });
    }

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
            this.notification.add(_t("Could not load picking: ") + e.message, { type: "danger" });
        } finally {
            this.state.loading = false;
        }
    }

    async refreshLines() {
        const data = await this.rpc("/stock_barcode_scanner_pro/picking/" + this.state.pickingId + "/state", {});
        this.state.lines = data.lines || [];
        this.state.state = data.state;
        this.state.pickingName = data.picking_name;
        this.state.partner = data.partner;
        this.state.origin = data.origin;
    }

    async startScanner() {
        if (typeof Html5Qrcode === "undefined") {
            this.notification.add(_t("Barcode library not loaded."), { type: "danger" });
            return;
        }
        this.html5Qrcode = new Html5Qrcode(this.readerRef.el.id);
        this.state.scanning = true;
        try {
            await this.html5Qrcode.start(
                { facingMode: "environment" },
                { fps: 10, qrbox: { width: 250, height: 150 } },
                (decodedText) => this.onScanSuccess(decodedText),
                () => {}
            );
        } catch (err) {
            this.state.scanning = false;
            this.notification.add(_t("Camera error: ") + err, { type: "danger" });
        }
    }

    async stopScanner() {
        if (this.html5Qrcode) {
            try {
                await this.html5Qrcode.stop();
                await this.html5Qrcode.clear();
            } catch (e) {
            }
            this.html5Qrcode = null;
        }
        this.state.scanning = false;
    }

    async onScanSuccess(decodedText) {
        const now = Date.now();
        if (this._lastScan && this._lastScan.text === decodedText && now - this._lastScan.time < 1500) {
            return;
        }
        this._lastScan = { text: decodedText, time: now };
        await this.processBarcode(decodedText);
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
            return;
        }
        if (!result.success) {
            this.addLog(result.message || _t("Scan failed."), "warning");
            return;
        }
        this.addLog(
            result.product_name + " -> " + result.new_quantity + " " + result.uom,
            "success"
        );
        await this.refreshLines();
    }

    async submitManual() {
        const barcode = this.state.manualBarcode.trim();
        if (!barcode) {
            return;
        }
        this.state.manualBarcode = "";
        await this.processBarcode(barcode);
    }

    onManualKeydown(ev) {
        if (ev.key === "Enter") {
            ev.preventDefault();
            this.submitManual();
        }
    }

    async validatePicking() {
        try {
            const result = await this.rpc("/stock_barcode_scanner_pro/validate", {
                picking_id: this.state.pickingId,
            });
            if (result.success) {
                this.notification.add(result.message, { type: "success" });
                await this.refreshLines();
            } else {
                this.notification.add(result.message, { type: "warning" });
            }
        } catch (e) {
            this.notification.add(e.message, { type: "danger" });
        }
    }

    addLog(message, level) {
        this.state.log.unshift({ message, level, time: new Date().toLocaleTimeString() });
        if (this.state.log.length > 20) {
            this.state.log.pop();
        }
    }
}

registry.category("actions").add("stock_barcode_scanner_pro", StockBarcodeScannerPro);