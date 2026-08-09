/** @odoo-module **/

import { Component, useState, onWillDestroy } from '@odoo/owl';
import { registry } from '@web/core/registry';
import { useService } from '@web/core/utils/hooks';

class PrintButton extends Component {
    setup() {
        this.printService = useService('smart_print');
        this.notification = useService('notification');
        this.dialog = useService('dialog');

        this.state = useState({
            printing: false,
            jobId: null,
            status: null,
        });

        // Auto-close timer
        this.closeTimer = null;

        // Get props with defaults
        this.reportId = this.props.reportId || null;
        this.model = this.props.model || null;
        this.resId = this.props.resId || null;
        this.label = this.props.label || 'Print';
        this.copies = this.props.copies || 1;
        this.format = this.props.format || 'pdf';
        this.autoClose = this.props.autoClose || false;
        this.printerId = this.props.printerId || null;
        this.className = this.props.className || 'btn-primary';
        this.size = this.props.size || '';

        // Cleanup on destroy
        onWillDestroy(() => {
            if (this.closeTimer) {
                clearTimeout(this.closeTimer);
            }
        });
    }

    async onClick() {
        if (this.state.printing) {
            return;
        }

        if (!this.model || !this.resId) {
            this.notification.add(
                'Missing document information for printing',
                { type: 'danger' }
            );
            return;
        }

        // If printer is explicitly provided, use it
        if (this.printerId) {
            await this.doPrint(this.printerId);
            return;
        }

        // Get available printers
        try {
            const printers = await this.printService.getAvailablePrinters();

            if (printers.length === 0) {
                this.notification.add(
                    'No printers available. Please configure a printer first.',
                    { type: 'warning' }
                );
                return;
            }

            // If only one printer, use it directly
            if (printers.length === 1) {
                await this.doPrint(printers[0].id);
            } else {
                // Show printer selection dialog
                this.showPrinterSelection(printers);
            }
        } catch (error) {
            console.error('Failed to get printers:', error);
            this.notification.add(
                'Failed to retrieve printers: ' + (error.message || 'Unknown error'),
                { type: 'danger' }
            );
        }
    }

    async doPrint(printerId, options = {}) {
        if (this.state.printing) {
            return;
        }

        this.state.printing = true;
        this.state.jobId = null;
        this.state.status = 'queued';

        try {
            const copies = options.copies || this.copies;
            const format = options.format || this.format;

            const jobId = await this.printService.printDirect({
                model: this.model,
                resId: this.resId,
                reportId: this.reportId,
                printerId: printerId,
                copies: copies,
                format: format,
            });

            this.state.jobId = jobId;

            // Show success notification
            this.notification.add(
                `Print job submitted successfully (ID: ${jobId})`,
                { type: 'success' }
            );

            // Emit success event
            if (this.props.onSuccess) {
                this.props.onSuccess(jobId);
            }

            // Auto-close if configured
            if (this.autoClose && this.props.onClose) {
                this.closeTimer = setTimeout(() => {
                    this.props.onClose();
                }, 3000);
            }

        } catch (error) {
            console.error('Print failed:', error);
            this.state.status = 'error';

            this.notification.add(
                `Print failed: ${error.message || 'Unknown error'}`,
                { type: 'danger' }
            );

            if (this.props.onError) {
                this.props.onError(error);
            }
        } finally {
            this.state.printing = false;
        }
    }

    showPrinterSelection(printers) {
        this.dialog.add(PrintDialog, {
            printers: printers,
            copies: this.copies,
            format: this.format,
            onSelect: (printerId, options) => {
                this.doPrint(printerId, options);
            },
            onCancel: () => {
                if (this.props.onCancel) {
                    this.props.onCancel();
                }
            }
        });
    }

    cancelPrint() {
        if (this.state.jobId) {
            this.printService.cancelJob(this.state.jobId)
                .then(() => {
                    this.state.jobId = null;
                    this.state.status = 'cancelled';
                    this.notification.add(
                        'Print job cancelled',
                        { type: 'info' }
                    );
                })
                .catch(error => {
                    this.notification.add(
                        `Failed to cancel job: ${error.message}`,
                        { type: 'danger' }
                    );
                });
        }
    }

    getStatusClass() {
        const statusMap = {
            'queued': 'smart-print-status-queued',
            'processing': 'smart-print-status-processing',
            'sent': 'smart-print-status-sent',
            'done': 'smart-print-status-done',
            'error': 'smart-print-status-error',
            'cancelled': 'smart-print-status-cancelled',
        };
        return statusMap[this.state.status] || '';
    }
}

PrintButton.template = `
    <button 
        class="btn smart-print-button {{ className }} {{ size ? 'btn-' + size : '' }}"
        t-attf-class="{{ state.printing ? 'disabled' : '' }} {{ className }} {{ size ? 'btn-' + size : '' }}"
        t-on-click="onClick"
        t-att-disabled="state.printing"
    >
        <span t-if="state.printing" class="fa fa-spinner fa-spin"></span>
        <span t-else="" class="fa fa-print"></span>
        <t t-if="state.printing">Printing...</t>
        <t t-else=""><t t-esc="label"/></t>
    </button>
`;

export const printButton = PrintButton;

// Register as a component for use in other modules
registry.category('components').add('SmartPrintButton', PrintButton);