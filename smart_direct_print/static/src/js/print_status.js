/** @odoo-module **/

import { Component, useState, onWillDestroy, onMounted } from '@odoo/owl';
import { useService } from '@web/core/utils/hooks';
import { registry } from '@web/core/registry';

class PrintStatus extends Component {
    setup() {
        this.printService = useService('smart_print');
        this.notification = useService('notification');

        this.state = useState({
            status: 'unknown',
            jobId: this.props.jobId || null,
            statusText: 'Unknown',
            errorMessage: null,
            progress: 0,
        });

        this.interval = null;
        this.pollCount = 0;
        this.maxPolls = this.props.maxPolls || 60; // Default: 5 minutes at 5s intervals

        onMounted(() => {
            if (this.state.jobId) {
                this.startMonitoring();
            }
        });

        onWillDestroy(() => {
            this.stopMonitoring();
        });
    }

    startMonitoring() {
        if (this.interval) {
            clearInterval(this.interval);
        }

        // Initial status check
        this.updateStatus();

        // Set up interval for monitoring
        this.interval = setInterval(() => {
            this.updateStatus();
        }, this.props.pollInterval || 5000); // Default: 5 seconds
    }

    stopMonitoring() {
        if (this.interval) {
            clearInterval(this.interval);
            this.interval = null;
        }
    }

    async updateStatus() {
        if (!this.state.jobId) {
            return;
        }

        this.pollCount++;

        try {
            const statusData = await this.printService.getJobStatus(this.state.jobId);

            const oldStatus = this.state.status;
            const newStatus = statusData.status || 'unknown';

            this.state.status = newStatus;
            this.state.statusText = this.getStatusLabel(newStatus);
            this.state.errorMessage = statusData.error_message || null;
            this.state.progress = this.calculateProgress(newStatus);

            // Check if we should stop monitoring
            if (newStatus === 'done' || newStatus === 'error' || newStatus === 'cancelled') {
                this.stopMonitoring();

                // Show notification on completion
                if (newStatus === 'done' && this.props.notifyOnComplete) {
                    this.notification.add(
                        `Print job ${this.state.jobId} completed successfully`,
                        { type: 'success' }
                    );
                } else if (newStatus === 'error') {
                    this.notification.add(
                        `Print job ${this.state.jobId} failed: ${statusData.error_message || 'Unknown error'}`,
                        { type: 'danger' }
                    );
                }

                // Call completion callback
                if (this.props.onComplete) {
                    this.props.onComplete(newStatus, statusData);
                }

                return;
            }

            // Check if we've exceeded max polls
            if (this.pollCount >= this.maxPolls) {
                this.stopMonitoring();
                this.state.status = 'error';
                this.state.errorMessage = 'Status check timed out';
            }

        } catch (error) {
            console.error('Failed to get job status:', error);
            // Don't stop monitoring on transient errors
            this.state.errorMessage = error.message || 'Error checking status';
        }
    }

    calculateProgress(status) {
        const progressMap = {
            'draft': 0,
            'queued': 10,
            'processing': 30,
            'sent': 60,
            'done': 100,
            'error': 100,
            'cancelled': 100,
        };
        return progressMap[status] || 0;
    }

    getStatusLabel(status) {
        const labelMap = {
            'draft': 'Draft',
            'queued': 'Queued',
            'processing': 'Processing',
            'sent': 'Sent to Printer',
            'done': 'Completed',
            'error': 'Error',
            'cancelled': 'Cancelled',
            'unknown': 'Unknown',
        };
        return labelMap[status] || 'Unknown';
    }

    getStatusClass() {
        const classMap = {
            'draft': 'smart-print-status-draft',
            'queued': 'smart-print-status-queued',
            'processing': 'smart-print-status-processing',
            'sent': 'smart-print-status-sent',
            'done': 'smart-print-status-done',
            'error': 'smart-print-status-error',
            'cancelled': 'smart-print-status-cancelled',
            'unknown': 'smart-print-status-draft',
        };
        return classMap[this.state.status] || 'smart-print-status-draft';
    }

    getStatusIcon() {
        const iconMap = {
            'draft': 'fa-file-o',
            'queued': 'fa-clock-o',
            'processing': 'fa-spinner fa-spin',
            'sent': 'fa-paper-plane-o',
            'done': 'fa-check',
            'error': 'fa-times',
            'cancelled': 'fa-ban',
            'unknown': 'fa-question',
        };
        return iconMap[this.state.status] || 'fa-question';
    }

    formatTimestamp(timestamp) {
        if (!timestamp) {
            return '';
        }
        try {
            const date = new Date(timestamp);
            return date.toLocaleString();
        } catch {
            return timestamp;
        }
    }

    retry() {
        if (this.props.onRetry) {
            this.props.onRetry(this.state.jobId);
        }
    }

    cancel() {
        if (this.props.onCancel) {
            this.props.onCancel(this.state.jobId);
        }
    }

    shouldShowActions() {
        return this.state.status === 'error' || this.state.status === 'queued';
    }

    getStatusText() {
        if (this.state.status === 'draft') {
            return 'Waiting to be processed';
        } else if (this.state.status === 'queued') {
            return 'Queued for printing';
        } else if (this.state.status === 'processing') {
            return 'Processing print job';
        } else if (this.state.status === 'sent') {
            return 'Sent to printer';
        } else if (this.state.status === 'done') {
            return 'Print completed successfully';
        } else if (this.state.status === 'error') {
            return `Error: ${this.state.errorMessage || 'Unknown error'}`;
        } else if (this.state.status === 'cancelled') {
            return 'Print job cancelled';
        }
        return 'Unknown status';
    }
}

PrintStatus.template = `
    <div class="smart-print-status-wrapper">
        <div class="smart-print-status" t-att-class="getStatusClass()">
            <span class="fa" t-att-class="getStatusIcon()"/>
            <span class="smart-print-status-label" t-esc="state.statusText"/>
        </div>
        
        <div t-if="state.status !== 'unknown'" class="smart-print-status-details">
            <div class="smart-print-progress" t-if="state.progress < 100">
                <div class="smart-print-progress-bar">
                    <div class="smart-print-progress-bar-inner" t-att-style="'width: ' + state.progress + '%'"/>
                    <div class="smart-print-progress-label" t-esc="state.progress + '%'"/>
                </div>
            </div>
            
            <div class="smart-print-status-text" t-esc="getStatusText()"/>
            
            <div t-if="state.errorMessage" class="smart-print-error">
                <span class="fa fa-exclamation-triangle text-danger"/>
                <span t-esc="state.errorMessage"/>
            </div>
            
            <div t-if="shouldShowActions()" class="smart-print-actions">
                <button t-if="state.status === 'error'" 
                        class="btn btn-sm btn-primary" 
                        t-on-click="retry">
                    <span class="fa fa-refresh"/> Retry
                </button>
                <button t-if="state.status === 'queued'" 
                        class="btn btn-sm btn-danger" 
                        t-on-click="cancel">
                    <span class="fa fa-times"/> Cancel
                </button>
            </div>
        </div>
        
        <div t-else="" class="smart-print-loading">
            <span class="fa fa-spinner fa-spin"/> Loading status...
        </div>
    </div>
`;

export const printStatus = PrintStatus;

// Register as a component
registry.category('components').add('SmartPrintStatus', PrintStatus);