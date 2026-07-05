/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState } from "@odoo/owl";

export class DocumentPreview extends Component {
    setup() {
        this.orm = useService("orm");
        this.state = useState({
            loading: true,
            error: null,
        });
    }

    get previewUrl() {
        return `/smart_document/preview/${this.props.documentId}`;
    }

    get isImage() {
        const ext = this.props.fileExtension?.toLowerCase();
        return ['jpg', 'jpeg', 'png', 'gif', 'tiff'].includes(ext);
    }

    get isPdf() {
        return this.props.fileExtension?.toLowerCase() === 'pdf';
    }
}

DocumentPreview.template = "smart_document_ai.DocumentPreview";
DocumentPreview.props = {
    documentId: Number,
    fileName: String,
    fileExtension: { type: String, optional: true },
};
