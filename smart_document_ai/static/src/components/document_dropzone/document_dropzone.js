/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onMounted, onWillUnmount } from "@odoo/owl";

export class DocumentDropzone extends Component {
    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.state = useState({
            isDragging: false,
            uploadProgress: 0,
        });

        onMounted(() => {
            this._setupDragListeners();
        });

        onWillUnmount(() => {
            this._removeDragListeners();
        });
    }

    _setupDragListeners() {
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            document.body.addEventListener(eventName, this._preventDefaults, false);
        });

        const dropzone = document.querySelector('.o_document_dropzone');
        if (dropzone) {
            dropzone.addEventListener('dragenter', this._handleDragEnter.bind(this));
            dropzone.addEventListener('dragleave', this._handleDragLeave.bind(this));
            dropzone.addEventListener('drop', this._handleDrop.bind(this));
        }
    }

    _removeDragListeners() {
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            document.body.removeEventListener(eventName, this._preventDefaults, false);
        });
    }

    _preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    _handleDragEnter(e) {
        this.state.isDragging = true;
    }

    _handleDragLeave(e) {
        this.state.isDragging = false;
    }

    async _handleDrop(e) {
        this.state.isDragging = false;
        const files = e.dataTransfer.files;

        if (!files.length) return;

        this.notification.add(
            `Uploading ${files.length} document(s)...`,
            { type: 'info' }
        );

        for (const file of files) {
            const reader = new FileReader();
            reader.onload = async (event) => {
                const base64 = event.target.result.split(',')[1];
                await this.orm.create('smart.document', [{
                    name: file.name.split('.')[0].replace(/[_-]/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
                    file: base64,
                    file_name: file.name,
                }]);
            };
            reader.readAsDataURL(file);
        }

        this.notification.add(
            'Documents uploaded successfully! AI categorization in progress...',
            { type: 'success' }
        );

        this.env.services.action.doAction({
            type: 'ir.actions.client',
            tag: 'reload',
        });
    }
}

DocumentDropzone.template = "smart_document_ai.DocumentDropzone";
