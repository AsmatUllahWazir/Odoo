/** @odoo-module **/

import { registry } from '@web/core/registry';
import { reactive } from '@odoo/owl';

class PrintService {
    constructor(env, services) {
        this.env = env;
        this.orm = services.orm;
        this.notification = services.notification;
        this.rpc = services.rpc;

        // Reactive state
        this.printJobs = reactive({});
        this.statusPolling = null;
        this.pollingEnabled = true;
        this.isInitialized = false;
    }

    /**
     * Initialize the print service
     */
    async init() {
        if (this.isInitialized) {
            return;
        }
        this.isInitialized = true;

        // Start polling for active jobs
        this.startPolling();
    }

    /**
     * Print a document directly
     * @param {Object} params - Print parameters
     * @param {string} params.model - Model name
     * @param {number} params.resId - Record ID
     * @param {number} params.reportId - Report ID
     * @param {number} params.printerId - Printer ID
     * @param {number} params.copies - Number of copies
     * @param {string} params.format - Document format
     * @returns {Promise<number>} Job ID
     */
    async printDirect(params) {
        try {
            // Create print job
            const result = await this.orm.call(
                'smart.print.operations',
                'create_print_job',
                [[], {
                    model: params.model,
                    res_id: params.resId,
                    report_id: params.reportId,
                    printer_id: params.printerId,
                    copies: params.copies || 1,
                    format: params.format || 'pdf'
                }]
            );

            const jobId = result.id || result;

            // Queue the job for printing
            await this.orm.call(
                'smart.print.job',
                'action_queue',
                [[jobId]]
            );

            // Add to monitored jobs
            this.printJobs[jobId] = {
                status: 'queued',
                name: result.name || `Job ${jobId}`,
                timestamp: new Date().toISOString()
            };

            // Start polling if not already
            if (!this.statusPolling) {
                this.startPolling();
            }

            return jobId;
        } catch (error) {
            console.error('PrintDirect error:', error);
            this.notification.add(
                `Failed to print: ${error.message || 'Unknown error'}`,
                { type: 'danger' }
            );
            throw error;
        }
    }

    /**
     * Get available printers for the current user
     * @returns {Promise<Array>} List of printers
     */
    async getAvailablePrinters() {
        try {
            const printers = await this.orm.searchRead(
                'smart.printer',
                [
                    ['active', '=', true],
                    ['status', '=', 'online'],
                    '|',
                    ['user_ids', 'in', [this.env.user.id]],
                    ['user_ids', '=', false]
                ],
                ['id', 'name', 'printer_type', 'supported_formats', 'status', 'server_id']
            );
            return printers;
        } catch (error) {
            console.error('Failed to get printers:', error);
            return [];
        }
    }

    /**
     * Get status of a specific job
     * @param {number} jobId - Job ID
     * @returns {Promise<Object>} Job status
     */
    async getJobStatus(jobId) {
        try {
            const job = await this.orm.searchRead(
                'smart.print.job',
                [['id', '=', jobId]],
                ['id', 'state', 'error_message', 'external_job_id', 'completed_at']
            );

            if (job && job.length > 0) {
                return {
                    id: job[0].id,
                    status: job[0].state,
                    error_message: job[0].error_message,
                    external_job_id: job[0].external_job_id,
                    completed_at: job[0].completed_at
                };
            }
            return { status: 'unknown' };
        } catch (error) {
            console.error('Failed to get job status:', error);
            return { status: 'error', message: error.message };
        }
    }

    /**
     * Get multiple job statuses at once
     * @param {Array} jobIds - List of job IDs
     * @returns {Promise<Array>} List of job statuses
     */
    async getJobStatuses(jobIds) {
        if (!jobIds || jobIds.length === 0) {
            return [];
        }

        try {
            const jobs = await this.orm.searchRead(
                'smart.print.job',
                [['id', 'in', jobIds]],
                ['id', 'state', 'error_message', 'external_job_id', 'completed_at']
            );

            return jobs.map(job => ({
                id: job.id,
                status: job.state,
                error_message: job.error_message,
                external_job_id: job.external_job_id,
                completed_at: job.completed_at
            }));
        } catch (error) {
            console.error('Failed to get job statuses:', error);
            return jobIds.map(id => ({ id, status: 'error', error_message: error.message }));
        }
    }

    /**
     * Cancel a print job
     * @param {number} jobId - Job ID to cancel
     * @returns {Promise<void>}
     */
    async cancelJob(jobId) {
        try {
            await this.orm.call(
                'smart.print.job',
                'action_cancel',
                [[jobId]]
            );

            if (this.printJobs[jobId]) {
                this.printJobs[jobId].status = 'cancelled';
            }

            this.notification.add(
                'Print job cancelled successfully',
                { type: 'info' }
            );
        } catch (error) {
            console.error('Cancel job error:', error);
            this.notification.add(
                `Failed to cancel job: ${error.message || 'Unknown error'}`,
                { type: 'danger' }
            );
            throw error;
        }
    }

    /**
     * Start polling for job status updates
     */
    startPolling() {
        if (this.statusPolling) {
            return;
        }

        this.pollingEnabled = true;
        this.statusPolling = setInterval(async () => {
            if (!this.pollingEnabled) {
                return;
            }

            const jobIds = Object.keys(this.printJobs);
            if (jobIds.length === 0) {
                return;
            }

            try {
                const statuses = await this.getJobStatuses(jobIds.map(Number));

                for (const status of statuses) {
                    const jobId = status.id;
                    if (this.printJobs[jobId]) {
                        const oldStatus = this.printJobs[jobId].status;
                        const newStatus = status.status;

                        if (oldStatus !== newStatus) {
                            this.printJobs[jobId].status = newStatus;
                            this.printJobs[jobId].error_message = status.error_message;

                            // Show notification for terminal states
                            if (newStatus === 'done') {
                                this.notification.add(
                                    `Print job ${jobId} completed successfully`,
                                    { type: 'success' }
                                );
                                // Remove from monitoring after a delay
                                setTimeout(() => {
                                    if (this.printJobs[jobId]) {
                                        this.printJobs[jobId].monitoring = false;
                                    }
                                    this.cleanupJobs();
                                }, 30000);
                            } else if (newStatus === 'error') {
                                this.notification.add(
                                    `Print job ${jobId} failed: ${status.error_message || 'Unknown error'}`,
                                    { type: 'danger' }
                                );
                            }
                        }
                    }
                }
            } catch (error) {
                console.error('Status polling error:', error);
            }
        }, 5000); // Poll every 5 seconds
    }

    /**
     * Clean up completed jobs from monitoring
     */
    cleanupJobs() {
        const toRemove = [];
        for (const [id, job] of Object.entries(this.printJobs)) {
            if (job.monitoring === false) {
                toRemove.push(id);
            }
        }
        for (const id of toRemove) {
            delete this.printJobs[id];
        }
    }

    /**
     * Stop polling for job status
     */
    stopPolling() {
        this.pollingEnabled = false;
        if (this.statusPolling) {
            clearInterval(this.statusPolling);
            this.statusPolling = null;
        }
    }

    /**
     * Test connection to a print server
     * @param {number} serverId - Server ID
     * @returns {Promise<boolean>} True if connection successful
     */
    async testConnection(serverId) {
        try {
            const result = await this.orm.call(
                'smart.print.server',
                'test_connection',
                [[serverId]]
            );

            this.notification.add(
                'Connection test successful',
                { type: 'success' }
            );
            return true;
        } catch (error) {
            this.notification.add(
                `Connection test failed: ${error.message || 'Unknown error'}`,
                { type: 'danger' }
            );
            return false;
        }
    }

    /**
     * Sync printers from a server
     * @param {number} serverId - Server ID
     * @returns {Promise<Object>} Sync result
     */
    async syncPrinters(serverId) {
        try {
            const result = await this.orm.call(
                'smart.print.server',
                'sync_printers',
                [[serverId]]
            );
            return result;
        } catch (error) {
            this.notification.add(
                `Failed to sync printers: ${error.message || 'Unknown error'}`,
                { type: 'danger' }
            );
            throw error;
        }
    }

    /**
     * Get print preferences for the current user
     * @returns {Promise<Object>} User preferences
     */
    async getUserPreferences() {
        try {
            const user = await this.orm.searchRead(
                'res.users',
                [['id', '=', this.env.user.id]],
                ['default_printer_id', 'print_preference', 'auto_print_enabled', 'workstation_name']
            );
            return user[0] || {};
        } catch (error) {
            console.error('Failed to get user preferences:', error);
            return {};
        }
    }

    /**
     * Set user print preference
     * @param {string} preference - Print preference
     * @returns {Promise<void>}
     */
    async setPrintPreference(preference) {
        try {
            await this.orm.write(
                'res.users',
                [[this.env.user.id]],
                { print_preference: preference }
            );
            this.notification.add(
                'Print preference updated',
                { type: 'success' }
            );
        } catch (error) {
            console.error('Failed to set print preference:', error);
            throw error;
        }
    }

    /**
     * Destroy the service
     */
    destroy() {
        this.stopPolling();
        this.printJobs = null;
    }
}

export const printService = {
    dependencies: ['orm', 'notification', 'rpc'],
    start(env, services) {
        const service = new PrintService(env, services);
        service.init();
        return service;
    }
};

// Register the service
registry.category('services').add('smart_print', printService);
