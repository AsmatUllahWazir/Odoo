/** @odoo-module **/

import { Component, useState, onWillDestroy } from '@odoo/owl';
import { Dialog } from '@web/core/dialog/dialog';
import { useService } from '@web/core/utils/hooks';

class PrintDialog extends Component {
    setup() {
        this.notification = useService('notification');

        this.state = useState({
            selectedPrinter: null,
            copies: this.props.copies || 1,
            format: this.props.format || 'pdf',
            loading: false,
        });
    }

    onSelectPrinter(ev) {
        const printerId = parseInt(ev.target.value);
        this.state.selectedPrinter = printerId;
    }

    onCopiesChange(ev) {
        const value = parseInt(ev.target.value) || 1;
        this.state.copies = Math.max(1, Math.min(999, value));
    }

    onFormatChange(ev) {
        this.state.format = ev.target.value;
    }

    async onPrint() {
        if (!this.state.selectedPrinter) {
            this.notification.add(
                'Please select a printer',
                { type: 'warning' }
            );
            return;
        }

        this.state.loading = true;

        try {
            await this.props.onSelect(this.state.selectedPrinter, {
                copies: this.state.copies,
                format: this.state.format,
            });
            this.close();
        } catch (error) {
            console.error('Print failed:', error);
            this.notification.add(
                'Print failed: ' + (error.message || 'Unknown error'),
                { type: 'danger' }
            );
        } finally {
            this.state.loading = false;
        }
    }

    onCancel() {
        if (this.props.onCancel) {
            this.props.onCancel();
        }
        this.close();
    }

    close() {
        this.props.close();
    }

    getSelectedPrinterName() {
        if (!this.state.selectedPrinter) {
            return '';
        }
        const printer = this.props.printers.find(
            p => p.id === this.state.selectedPrinter
        );
        return printer ? printer.name : '';
    }
}

PrintDialog.components = { Dialog };
PrintDialog.template = `
    <Dialog 
        size="md" 
        title="Print Document" 
        class="smart-print-dialog"
    >
        <div class="modal-body">
            <div class="form-group">
                <label for="printer-select">Select Printer</label>
                <select 
                    id="printer-select"
                    class="form-control smart-print-printer-selector" 
                    t-on-change="onSelectPrinter"
                    t-att-disabled="state.loading"
                >
                    <option value="" disabled selected>Choose a printer...</option>
                    <option 
                        t-foreach="props.printers" 
                        t-as="printer" 
                        t-att-value="printer.id"
                        t-att-selected="state.selectedPrinter === printer.id"
                    >
                        <t t-esc="printer.name"/> 
                        (<t t-esc="printer.printer_type"/>)
                        <t t-if="printer.status === 'offline'"> [Offline]</t>
                    </option>
                </select>
                <small class="form-text text-muted" t-if="state.selectedPrinter">
                    Selected: <strong t-esc="getSelectedPrinterName()"/>
                </small>
            </div>
            
            <div class="form-group">
                <label for="copies-input">Number of Copies</label>
                <input 
                    id="copies-input"
                    type="number" 
                    class="form-control" 
                    t-model="state.copies"
                    t-on-change="onCopiesChange"
                    min="1" 
                    max="999"
                    t-att-disabled="state.loading"
                />
            </div>
            
            <div class="form-group">
                <label for="format-select">Output Format</label>
                <select 
                    id="format-select"
                    class="form-control" 
                    t-model="state.format"
                    t-on-change="onFormatChange"
                    t-att-disabled="state.loading"
                >
                    <option value="pdf">PDF</option>
                    <option value="zpl">ZPL</option>
                    <option value="esc_pos">ESC/POS</option>
                    <option value="raw">RAW</option>
                    <option value="png">PNG</option>
                    <option value="jpg">JPG</option>
                </select>
            </div>
            
            <div t-if="state.loading" class="smart-print-progress">
                <div class="smart-print-progress-bar">
                    <div class="smart-print-progress-bar-inner" style="width: 50%;"></div>
                    <div class="smart-print-progress-label">Sending to printer...</div>
                </div>
            </div>
        </div>
        
        <div class="modal-footer">
            <button 
                class="btn btn-secondary" 
                t-on-click="onCancel"
                t-att-disabled="state.loading"
            >
                Cancel
            </button>
            <button 
                class="btn btn-primary" 
                t-on-click="onPrint" 
                t-att-disabled="!state.selectedPrinter || state.loading"
            >
                <span t-if="!state.loading" class="fa fa-print"/> 
                <span t-if="state.loading" class="fa fa-spinner fa-spin"/>
                <t t-if="state.loading">Printing...</t>
                <t t-else="">Print</t>
            </button>
        </div>
    </Dialog>
`;

export const printDialog = PrintDialog;

// Register as a component
registry.category('components').add('SmartPrintDialog', PrintDialog);