/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useState } from "@odoo/owl";

export class DocumentAnalytics extends Component {
    setup() {
        this.orm = useService("orm");
        this.state = useState({
            stats: {
                totalDocuments: 0,
                totalSize: 0,
                totalDownloads: 0,
                totalViews: 0,
                duplicateCount: 0,
            },
            categoryData: [],
            recentUploads: [],
        });

        onWillStart(async () => {
            await this.loadAnalytics();
        });
    }

    async loadAnalytics() {
        // Get document counts
        const documentCount = await this.orm.searchCount('smart.document', []);
        const duplicateCount = await this.orm.searchCount('smart.document', [('is_duplicate', '=', true)]);

        // Get aggregated stats
        const docs = await this.orm.searchRead('smart.document', [], ['file_size', 'download_count', 'view_count']);
        const totalSize = docs.reduce((sum, d) => sum + (d.file_size || 0), 0);
        const totalDownloads = docs.reduce((sum, d) => sum + (d.download_count || 0), 0);
        const totalViews = docs.reduce((sum, d) => sum + (d.view_count || 0), 0);

        this.state.stats = {
            totalDocuments: documentCount,
            totalSize: this._formatSize(totalSize),
            totalDownloads,
            totalViews,
            duplicateCount,
        };
    }

    _formatSize(bytes) {
        if (bytes === 0) return '0 B';
        const units = ['B', 'KB', 'MB', 'GB'];
        let i = 0;
        while (bytes >= 1024 && i < units.length - 1) {
            bytes /= 1024;
            i++;
        }
        return `${bytes.toFixed(1)} ${units[i]}`;
    }
}

DocumentAnalytics.template = "smart_document_ai.DocumentAnalytics";
