// E-ink Display Manager JavaScript
class EinkDisplayManager {
    constructor() {
        this.selectedFiles = new Set();
        this.selectionMode = false;
        this.files = [];
        
        this.init();
    }
    
    init() {
        this.bindEvents();
        this.loadFiles();
        this.checkServerStatus();
        
        // Check status periodically
        setInterval(() => this.checkServerStatus(), 30000);
    }
    
    bindEvents() {
        // File upload events
        const uploadArea = document.getElementById('upload-area');
        const fileInput = document.getElementById('file-input');
        
        uploadArea.addEventListener('click', () => fileInput.click());
        uploadArea.addEventListener('dragover', this.handleDragOver.bind(this));
        uploadArea.addEventListener('dragleave', this.handleDragLeave.bind(this));
        uploadArea.addEventListener('drop', this.handleDrop.bind(this));
        fileInput.addEventListener('change', this.handleFileSelect.bind(this));
        
        // Control buttons
        document.getElementById('clear-display').addEventListener('click', this.clearDisplay.bind(this));
        document.getElementById('clean-folder').addEventListener('click', this.cleanFolder.bind(this));
        document.getElementById('refresh-files').addEventListener('click', this.loadFiles.bind(this));
        document.getElementById('select-multiple').addEventListener('click', this.toggleSelectionMode.bind(this));
        
        // Selection controls
        document.getElementById('delete-selected').addEventListener('click', this.deleteSelected.bind(this));
        document.getElementById('cancel-selection').addEventListener('click', this.cancelSelection.bind(this));
        
        // Modal events
        document.getElementById('modal-cancel').addEventListener('click', this.hideModal.bind(this));
        document.getElementById('modal-confirm').addEventListener('click', this.confirmModal.bind(this));
        document.getElementById('modal-overlay').addEventListener('click', (e) => {
            if (e.target.id === 'modal-overlay') this.hideModal();
        });
        
        // Settings events
        document.getElementById('open-settings').addEventListener('click', this.openSettings.bind(this));
        document.getElementById('settings-cancel').addEventListener('click', this.closeSettings.bind(this));
        document.getElementById('settings-save').addEventListener('click', this.saveSettings.bind(this));
        document.getElementById('settings-modal').addEventListener('click', (e) => {
            if (e.target.id === 'settings-modal') this.closeSettings();
        });
        
        // Settings input events
        document.getElementById('thumbnail-quality').addEventListener('input', (e) => {
            document.getElementById('thumbnail-quality-value').textContent = e.target.value;
        });
    }
    
    // ============ DRAG & DROP HANDLING ============
    
    handleDragOver(e) {
        e.preventDefault();
        e.stopPropagation();
        document.getElementById('upload-area').classList.add('drag-over');
    }
    
    handleDragLeave(e) {
        e.preventDefault();
        e.stopPropagation();
        document.getElementById('upload-area').classList.remove('drag-over');
    }
    
    handleDrop(e) {
        e.preventDefault();
        e.stopPropagation();
        document.getElementById('upload-area').classList.remove('drag-over');
        
        const files = Array.from(e.dataTransfer.files);
        this.uploadFiles(files);
    }
    
    handleFileSelect(e) {
        const files = Array.from(e.target.files);
        this.uploadFiles(files);
        e.target.value = ''; // Reset input
    }
    
    // ============ FILE UPLOAD ============
    
    async uploadFiles(files) {
        if (files.length === 0) return;
        
        this.showUploadProgress();
        let uploadedCount = 0;
        let totalFiles = files.length;
        
        for (let i = 0; i < files.length; i++) {
            const file = files[i];
            try {
                await this.uploadSingleFile(file, i + 1, totalFiles);
                uploadedCount++;
                this.updateUploadProgress((i + 1) / totalFiles * 100, `Uploaded ${i + 1}/${totalFiles} files`);
            } catch (error) {
                console.error('Upload failed:', error);
                this.showToast(`Failed to upload ${file.name}: ${error.message}`, 'error');
            }
        }
        
        this.hideUploadProgress();
        
        if (uploadedCount > 0) {
            this.showToast(`Successfully uploaded ${uploadedCount} file(s)`, 'success');
            setTimeout(() => this.loadFiles(), 1000); // Refresh file list
        }
    }
    
    async uploadSingleFile(file, index, total) {
        const formData = new FormData();
        formData.append('file', file);
        
        const response = await fetch('/upload', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Upload failed');
        }
        
        return response.json();
    }
    
    showUploadProgress() {
        document.getElementById('upload-progress').style.display = 'flex';
        this.updateUploadProgress(0, 'Preparing upload...');
    }
    
    hideUploadProgress() {
        document.getElementById('upload-progress').style.display = 'none';
    }
    
    updateUploadProgress(percent, text) {
        document.getElementById('progress-fill').style.width = `${percent}%`;
        document.getElementById('progress-text').textContent = text;
    }
    
    // ============ FILE MANAGEMENT ============
    
    async loadFiles() {
        try {
            const response = await fetch('/api/files');
            const data = await response.json();
            
            this.files = data.files || [];
            this.renderFiles();
            this.updateFileStats();
            
        } catch (error) {
            console.error('Failed to load files:', error);
            this.showToast('Failed to load files', 'error');
        }
    }
    
    renderFiles() {
        const filesGrid = document.getElementById('files-grid');
        const emptyState = document.getElementById('empty-state');
        
        if (this.files.length === 0) {
            filesGrid.innerHTML = '';
            emptyState.style.display = 'block';
            return;
        }
        
        emptyState.style.display = 'none';
        
        filesGrid.innerHTML = this.files.map(file => this.createFileCard(file)).join('');
        
        // Bind file card events
        this.bindFileCardEvents();
    }
    
    createFileCard(file) {
        const fileSize = this.formatFileSize(file.size);
        const fileDate = new Date(file.modified * 1000).toLocaleDateString();
        const iconClass = this.getFileIconClass(file.type);
        
        return `
            <div class="file-card ${this.selectionMode ? 'selection-mode' : ''}" data-filename="${file.filename}">
                <div class="file-preview">
                    ${file.thumbnail ? 
                        `<img src="${file.thumbnail}" alt="${file.filename}">` : 
                        `<i class="fas ${iconClass} file-icon ${file.type}"></i>`
                    }
                    <input type="checkbox" class="file-checkbox" ${this.selectedFiles.has(file.filename) ? 'checked' : ''}>
                </div>
                <div class="file-info">
                    <div class="file-name">${file.filename}</div>
                    <div class="file-meta">
                        <span>${fileSize}</span>
                        <span>${fileDate}</span>
                    </div>
                    <div class="file-actions">
                        <button class="file-btn display" data-action="display">
                            <i class="fas fa-eye"></i> Display
                        </button>
                        <button class="file-btn delete" data-action="delete">
                            <i class="fas fa-trash"></i> Delete
                        </button>
                    </div>
                </div>
            </div>
        `;
    }
    
    bindFileCardEvents() {
        // File action buttons
        document.querySelectorAll('.file-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const action = btn.dataset.action;
                const filename = btn.closest('.file-card').dataset.filename;
                
                if (action === 'display') {
                    this.displayFile(filename);
                } else if (action === 'delete') {
                    this.deleteFile(filename);
                }
            });
        });
        
        // File selection checkboxes
        document.querySelectorAll('.file-checkbox').forEach(checkbox => {
            checkbox.addEventListener('change', (e) => {
                e.stopPropagation();
                const filename = checkbox.closest('.file-card').dataset.filename;
                
                if (checkbox.checked) {
                    this.selectedFiles.add(filename);
                    checkbox.closest('.file-card').classList.add('selected');
                } else {
                    this.selectedFiles.delete(filename);
                    checkbox.closest('.file-card').classList.remove('selected');
                }
                
                this.updateSelectionControls();
            });
        });
        
        // File card click (for selection mode)
        document.querySelectorAll('.file-card').forEach(card => {
            card.addEventListener('click', (e) => {
                if (this.selectionMode && !e.target.closest('.file-btn')) {
                    const checkbox = card.querySelector('.file-checkbox');
                    checkbox.checked = !checkbox.checked;
                    checkbox.dispatchEvent(new Event('change'));
                }
            });
        });
    }
    
    getFileIconClass(type) {
        const icons = {
            'image': 'fa-image',
            'text': 'fa-file-alt',
            'pdf': 'fa-file-pdf',
            'other': 'fa-file'
        };
        return icons[type] || icons.other;
    }
    
    formatFileSize(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    }
    
    updateFileStats() {
        const fileCount = this.files.length;
        const fileCountText = fileCount === 1 ? '1 file' : `${fileCount} files`;
        document.getElementById('file-stats').querySelector('.file-count').textContent = fileCountText;
    }
    
    // ============ FILE ACTIONS ============
    
    async displayFile(filename) {
        try {
            const response = await fetch('/display_file', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ filename })
            });
            
            const data = await response.json();
            
            if (response.ok) {
                this.showToast(`Displaying: ${filename}`, 'success');
            } else {
                throw new Error(data.error || 'Failed to display file');
            }
        } catch (error) {
            console.error('Display failed:', error);
            this.showToast(`Failed to display file: ${error.message}`, 'error');
        }
    }
    
    async deleteFile(filename) {
        this.showModal(
            'Delete File',
            `Are you sure you want to delete "${filename}"? This action cannot be undone.`,
            async () => {
                try {
                    const response = await fetch('/delete_file', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ filename })
                    });
                    
                    const data = await response.json();
                    
                    if (response.ok) {
                        this.showToast(`Deleted: ${filename}`, 'success');
                        this.loadFiles(); // Refresh file list
                    } else {
                        throw new Error(data.error || 'Failed to delete file');
                    }
                } catch (error) {
                    console.error('Delete failed:', error);
                    this.showToast(`Failed to delete file: ${error.message}`, 'error');
                }
            }
        );
    }
    
    // ============ BULK OPERATIONS ============
    
    toggleSelectionMode() {
        this.selectionMode = !this.selectionMode;
        
        if (this.selectionMode) {
            document.getElementById('select-multiple').innerHTML = '<i class="fas fa-times"></i> Cancel Selection';
            document.getElementById('select-multiple').classList.add('danger-btn');
            document.getElementById('select-multiple').classList.remove('select-btn');
        } else {
            this.cancelSelection();
        }
        
        this.renderFiles();
    }
    
    cancelSelection() {
        this.selectionMode = false;
        this.selectedFiles.clear();
        
        document.getElementById('select-multiple').innerHTML = '<i class="fas fa-check-square"></i> Select Multiple';
        document.getElementById('select-multiple').classList.remove('danger-btn');
        document.getElementById('select-multiple').classList.add('select-btn');
        document.getElementById('selection-controls').style.display = 'none';
        
        this.renderFiles();
    }
    
    updateSelectionControls() {
        const selectionControls = document.getElementById('selection-controls');
        const selectionCount = document.getElementById('selection-count');
        
        if (this.selectedFiles.size > 0) {
            selectionControls.style.display = 'flex';
            selectionCount.textContent = `${this.selectedFiles.size} selected`;
        } else {
            selectionControls.style.display = 'none';
        }
    }
    
    async deleteSelected() {
        const filenames = Array.from(this.selectedFiles);
        const count = filenames.length;
        
        this.showModal(
            'Delete Selected Files', 
            `Are you sure you want to delete ${count} file(s)? This action cannot be undone.`,
            async () => {
                try {
                    const response = await fetch('/delete_multiple', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ filenames })
                    });
                    
                    const data = await response.json();
                    
                    if (response.ok) {
                        this.showToast(data.message, 'success');
                        this.cancelSelection();
                        this.loadFiles();
                    } else {
                        throw new Error(data.error || 'Failed to delete files');
                    }
                } catch (error) {
                    console.error('Bulk delete failed:', error);
                    this.showToast(`Failed to delete files: ${error.message}`, 'error');
                }
            }
        );
    }
    
    // ============ SYSTEM CONTROLS ============
    
    async clearDisplay() {
        try {
            const response = await fetch('/clear_screen', {
                method: 'POST'
            });
            
            const data = await response.json();
            
            if (response.ok) {
                this.showToast('Display cleared', 'success');
            } else {
                throw new Error(data.error || 'Failed to clear display');
            }
        } catch (error) {
            console.error('Clear display failed:', error);
            this.showToast(`Failed to clear display: ${error.message}`, 'error');
        }
    }
    
    async cleanFolder() {
        this.showModal(
            'Clean Folder',
            'This will delete all files in the watched folder. Are you sure?',
            async () => {
                try {
                    const response = await fetch('/cleanup_old_files', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ keep_count: 0 }) // Delete all files
                    });
                    
                    const data = await response.json();
                    
                    if (response.ok) {
                        this.showToast('Folder cleaned', 'success');
                        this.loadFiles();
                    } else {
                        throw new Error(data.error || 'Failed to clean folder');
                    }
                } catch (error) {
                    console.error('Clean folder failed:', error);
                    this.showToast(`Failed to clean folder: ${error.message}`, 'error');
                }
            }
        );
    }
    
    // ============ SERVER STATUS ============
    
    async checkServerStatus() {
        try {
            const response = await fetch('/status');
            const statusIndicator = document.getElementById('status-indicator');
            const statusDot = statusIndicator.querySelector('.status-dot');
            const statusText = statusIndicator.querySelector('.status-text');
            
            if (response.ok) {
                statusDot.className = 'status-dot connected';
                statusText.textContent = 'Connected';
            } else {
                throw new Error('Server error');
            }
        } catch (error) {
            const statusIndicator = document.getElementById('status-indicator');
            const statusDot = statusIndicator.querySelector('.status-dot');
            const statusText = statusIndicator.querySelector('.status-text');
            
            statusDot.className = 'status-dot error';
            statusText.textContent = 'Connection Error';
        }
    }
    
    // ============ UI HELPERS ============
    
    showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.innerHTML = `
            <div>${message}</div>
        `;
        
        document.getElementById('toast-container').appendChild(toast);
        
        // Auto remove after 5 seconds
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 5000);
    }
    
    showModal(title, message, onConfirm) {
        document.getElementById('modal-title').textContent = title;
        document.getElementById('modal-message').textContent = message;
        document.getElementById('modal-overlay').style.display = 'flex';
        
        this.modalConfirmCallback = onConfirm;
    }
    
    hideModal() {
        document.getElementById('modal-overlay').style.display = 'none';
        this.modalConfirmCallback = null;
    }
    
    confirmModal() {
        if (this.modalConfirmCallback) {
            this.modalConfirmCallback();
        }
        this.hideModal();
    }
    
    // ============ SETTINGS MANAGEMENT ============
    
    async openSettings() {
        try {
            // Load current settings
            const response = await fetch('/settings');
            if (response.ok) {
                const settings = await response.json();
                this.currentSettings = settings; // Store for comparison
                this.populateSettingsForm(settings);
            } else {
                throw new Error('Failed to load settings');
            }
            
            // Show settings modal
            document.getElementById('settings-modal').style.display = 'flex';
            
        } catch (error) {
            console.error('Error opening settings:', error);
            this.showToast('Failed to load settings', 'error');
        }
    }
    
    closeSettings() {
        document.getElementById('settings-modal').style.display = 'none';
    }
    
    populateSettingsForm(settings) {
        // Set image crop mode
        document.getElementById('image-crop-mode').value = settings.image_crop_mode || 'center_crop';
        
        // Set auto display upload
        document.getElementById('auto-display-upload').checked = settings.auto_display_upload !== false;
        
        // Set thumbnail quality
        const qualitySlider = document.getElementById('thumbnail-quality');
        const qualityValue = document.getElementById('thumbnail-quality-value');
        qualitySlider.value = settings.thumbnail_quality || 85;
        qualityValue.textContent = qualitySlider.value;
        
        // Set timing features
        document.getElementById('disable-startup-timer').checked = settings.disable_startup_timer === true;
        document.getElementById('disable-refresh-timer').checked = settings.disable_refresh_timer === true;
        document.getElementById('startup-delay').value = settings.startup_delay_minutes || 1;
        document.getElementById('refresh-interval').value = settings.refresh_interval_hours || 24;
        document.getElementById('enable-manufacturer-timing').checked = settings.enable_manufacturer_timing === true;
        document.getElementById('enable-sleep-mode').checked = settings.enable_sleep_mode !== false;
        document.getElementById('orientation').value = settings.orientation || 'landscape';
    }
    
    async saveSettings() {
        try {
            const currentOrientation = this.currentSettings ? this.currentSettings.orientation : 'landscape';
            const newOrientation = document.getElementById('orientation').value;
            const orientationChanged = currentOrientation !== newOrientation;
            
            const settings = {
                image_crop_mode: document.getElementById('image-crop-mode').value,
                auto_display_upload: document.getElementById('auto-display-upload').checked,
                thumbnail_quality: parseInt(document.getElementById('thumbnail-quality').value),
                disable_startup_timer: document.getElementById('disable-startup-timer').checked,
                disable_refresh_timer: document.getElementById('disable-refresh-timer').checked,
                startup_delay_minutes: parseInt(document.getElementById('startup-delay').value),
                refresh_interval_hours: parseInt(document.getElementById('refresh-interval').value),
                enable_manufacturer_timing: document.getElementById('enable-manufacturer-timing').checked,
                enable_sleep_mode: document.getElementById('enable-sleep-mode').checked,
                orientation: newOrientation
            };
            
            const response = await fetch('/settings', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(settings)
            });
            
            if (response.ok) {
                const result = await response.json();
                this.currentSettings = result.settings; // Store current settings for comparison
                
                if (orientationChanged) {
                    this.showToast('Settings saved! Display orientation is being updated...', 'success');
                } else {
                    this.showToast('Settings saved successfully', 'success');
                }
                this.closeSettings();
            } else {
                const error = await response.json();
                throw new Error(error.error || 'Failed to save settings');
            }
            
        } catch (error) {
            console.error('Error saving settings:', error);
            this.showToast(`Failed to save settings: ${error.message}`, 'error');
        }
    }
}

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new EinkDisplayManager();
}); 