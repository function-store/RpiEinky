// E-ink Display Manager JavaScript
class EinkDisplayManager {
    constructor() {
        this.selectedFiles = new Set();
        this.selectionMode = false;
        this.files = [];
        this.currentlyDisplayedFile = null;
        
        this.init();
    }
    
    async init() {
        // Bind events first
        this.bindEvents();
        
        // Initial status check
        await this.checkServerStatus();
        
        // Load display info
        await this.loadDisplayInfo();
        
        // Load initial files
        await this.loadFiles();
        
        // Start polling for updates
        this.startPolling();
    }
    
    startPolling() {
        // Check status periodically
        setInterval(() => this.checkServerStatus(), 30000);
        
        // Update currently displayed file periodically
        setInterval(() => this.loadCurrentlyDisplayedFile(), 5000); // Every 5 seconds
        
        // Poll for new files periodically (every 10 seconds)
        setInterval(() => this.pollForNewFiles(), 10000);
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
        document.getElementById('refresh-files').addEventListener('click', this.refreshFiles.bind(this));
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
        
        // Selected image events

        
        // Settings input events
        document.getElementById('thumbnail-quality').addEventListener('input', (e) => {
            document.getElementById('thumbnail-quality-value').textContent = e.target.value;
        });
        
        // Bind refresh timer checkbox to control interval field state
        document.getElementById('enable-refresh-timer').addEventListener('change', () => {
            this.updateRefreshIntervalFieldState();
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
        
        if (uploadedCount > 0) {
            this.showToast(`Successfully uploaded ${uploadedCount} file(s)`, 'success');
            
            // Wait a moment for the server to process the upload
            setTimeout(async () => {
                // Show progress for auto-display check
                this.updateUploadProgress(90, 'Checking auto-display settings...');
                
                // First, refresh the file list to get the new files
                await this.loadFiles();
                
                // Then force refresh the currently displayed file status
                await this.forceRefreshDisplayedFile();
                
                // If auto-display is enabled, the latest uploaded file should now be displayed
                // The server handles this automatically based on settings
                this.updateUploadProgress(100, 'Upload complete!');
                
                setTimeout(() => {
                    this.hideUploadProgress();
                }, 500);
            }, 1500); // Increased delay to ensure server has time to process
        } else {
            this.hideUploadProgress();
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
            
            // Get currently displayed file info and update the display
            await this.loadCurrentlyDisplayedFile();
            
            this.renderFiles();
            this.updateFileStats();
            
        } catch (error) {
            console.error('Failed to load files:', error);
            this.showToast('Failed to load files', 'error');
        }
    }
    
    async refreshFiles() {
        try {
            console.log('Manual refresh triggered');
            await this.loadFiles();
            await this.forceRefreshDisplayedFile();
            this.showToast('Files refreshed', 'success');
        } catch (error) {
            console.error('Failed to refresh files:', error);
            this.showToast('Failed to refresh files', 'error');
        }
    }
    
    async loadCurrentlyDisplayedFile() {
        try {
            const response = await fetch('/displayed_file');
            if (response.ok) {
                const data = await response.json();
                const previousDisplayedFile = this.currentlyDisplayedFile;
                this.currentlyDisplayedFile = data.filename;
                
                // If the displayed file changed, update the display
                if (previousDisplayedFile !== this.currentlyDisplayedFile) {
                    console.log(`Currently displayed file changed from ${previousDisplayedFile} to ${this.currentlyDisplayedFile}`);
                    this.renderFiles(); // Refresh to update badges
                }
            } else {
                this.currentlyDisplayedFile = null;
            }
        } catch (error) {
            console.error('Failed to load currently displayed file:', error);
            this.currentlyDisplayedFile = null;
        }
        
        // Update the display after loading
        this.updateCurrentlyDisplayedImage();
        

    }
    
    async forceRefreshDisplayedFile() {
        try {
            const response = await fetch('/displayed_file');
            if (response.ok) {
                const data = await response.json();
                this.currentlyDisplayedFile = data.filename;
                console.log(`Force refreshed currently displayed file: ${this.currentlyDisplayedFile}`);
                
                // Always re-render to ensure badges are updated
                this.renderFiles();
                this.updateCurrentlyDisplayedImage();
            } else {
                this.currentlyDisplayedFile = null;
                this.renderFiles();
                this.updateCurrentlyDisplayedImage();
            }
        } catch (error) {
            console.error('Failed to force refresh displayed file:', error);
            this.currentlyDisplayedFile = null;
            this.renderFiles();
            this.updateCurrentlyDisplayedImage();
        }
    }
    
    async pollForNewFiles() {
        try {
            // Show polling indicator
            const pollingIndicator = document.getElementById('polling-indicator');
            pollingIndicator.style.display = 'flex';
            
            const response = await fetch('/api/files');
            const data = await response.json();
            
            const newFiles = data.files || [];
            const currentFileCount = this.files.length;
            const newFileCount = newFiles.length;
            
            // Check if we have new files or if file list has changed
            let filesChanged = false;
            
            if (newFileCount !== currentFileCount) {
                filesChanged = true;
            } else {
                // Check if any files have been modified or if the list has changed
                const currentFilenames = this.files.map(f => f.filename).sort();
                const newFilenames = newFiles.map(f => f.filename).sort();
                
                if (JSON.stringify(currentFilenames) !== JSON.stringify(newFilenames)) {
                    filesChanged = true;
                }
            }
            
            if (filesChanged) {
                console.log(`File list changed, refreshing display...`);
                this.files = newFiles;
                this.renderFiles();
                this.updateFileStats();
                
                // Also check currently displayed file in case it changed
                await this.loadCurrentlyDisplayedFile();
                
                // Show notification if files were added
                if (newFileCount > currentFileCount) {
                    this.showToast(`Found ${newFileCount - currentFileCount} new file(s)`, 'info');
                }
            }
        } catch (error) {
            console.error('Failed to poll for new files:', error);
        } finally {
            // Hide polling indicator
            const pollingIndicator = document.getElementById('polling-indicator');
            pollingIndicator.style.display = 'none';
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
        const isCurrentlyDisplayed = this.currentlyDisplayedFile === file.filename;
        
        // Debug logging
        if (isCurrentlyDisplayed) {
            console.log(`File ${file.filename} is marked as currently displayed`);
        }
        
        return `
            <div class="file-card ${this.selectionMode ? 'selection-mode' : ''} ${isCurrentlyDisplayed ? 'currently-displayed' : ''}" data-filename="${file.filename}">
                <div class="file-preview">
                    ${file.thumbnail ? 
                        `<img src="${file.thumbnail}" alt="${file.filename}">` : 
                        `<i class="fas ${iconClass} file-icon ${file.type}"></i>`
                    }
                    <input type="checkbox" class="file-checkbox" ${this.selectedFiles.has(file.filename) ? 'checked' : ''}>
                    ${isCurrentlyDisplayed ? '<div class="currently-displayed-badge"><i class="fas fa-tv"></i> Currently Displayed</div>' : ''}
                </div>
                <div class="file-info">
                    <div class="file-name">${file.filename}</div>
                    <div class="file-meta">
                        <span>${fileSize}</span>
                        <span>${fileDate}</span>
                    </div>
                    <div class="file-actions">
                                        <button class="file-btn display" data-action="display">
                    <i class="fas fa-eye"></i> ${isCurrentlyDisplayed ? 'Refresh Display' : 'Display'}
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
        
        // Update currently displayed info
        const currentlyDisplayedInfo = document.getElementById('currently-displayed-info');
        const currentlyDisplayedFilename = document.getElementById('currently-displayed-filename');
        
        if (this.currentlyDisplayedFile) {
            currentlyDisplayedFilename.textContent = this.currentlyDisplayedFile;
            currentlyDisplayedInfo.style.display = 'flex';
        } else {
            currentlyDisplayedInfo.style.display = 'none';
        }
    }
    
    // ============ FILE ACTIONS ============
    
    async displayFile(filename) {
        try {
            const response = await fetch(`/display_file`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ filename })
            });

            if (response.ok) {
                this.showToast(`Displaying ${filename}...`, 'success');
                
                // Immediately update displayed file
                this.currentlyDisplayedFile = filename;
                this.updateCurrentlyDisplayedImage();
                
                // Refresh the file list to update the "currently displayed" badges
                await this.loadFiles();
            } else {
                const error = await response.json();
                throw new Error(error.error || 'Failed to display file');
            }
        } catch (error) {
            this.showToast(`Failed to display file: ${error}`, 'error');
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
                
                // Refresh the currently displayed file info since display is now cleared
                await this.loadCurrentlyDisplayedFile();
                this.renderFiles();
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
            if (response.ok) {
                const status = await response.json();
                this.updateStatusIndicator('connected');
                return true;
            } else {
                this.updateStatusIndicator('error');
                return false;
            }
        } catch (error) {
            console.error('Server status check failed:', error);
            this.updateStatusIndicator('error');
            return false;
        }
    }
    
    updateStatusIndicator(status) {
        const statusIndicator = document.getElementById('status-indicator');
        const statusDot = statusIndicator.querySelector('.status-dot');
        const statusText = statusIndicator.querySelector('.status-text');
        
        if (status === 'connected') {
            statusDot.className = 'status-dot connected';
            statusText.textContent = 'Connected';
        } else if (status === 'error') {
            statusDot.className = 'status-dot error';
            statusText.textContent = 'Connection Error';
        } else {
            statusDot.className = 'status-dot';
            statusText.textContent = 'Connecting...';
        }
    }
    
    async loadDisplayInfo() {
        try {
            const response = await fetch('/display_info');
            if (response.ok) {
                const displayInfo = await response.json();
                const resolutionElement = document.getElementById('display-resolution');
                const displayInfoElement = document.getElementById('display-info');
                
                if (resolutionElement && displayInfoElement) {
                    const { resolution, display_type } = displayInfo;
                    resolutionElement.textContent = `${resolution.width}×${resolution.height}`;
                    displayInfoElement.style.display = 'flex';
                    
                    // Add tooltip with more details
                    displayInfoElement.title = `${display_type} display (${resolution.width}×${resolution.height} landscape)`;
                }
            }
        } catch (error) {
            console.error('Failed to load display info:', error);
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
        document.getElementById('enable-startup-timer').checked = settings.enable_startup_timer === true;
        document.getElementById('enable-refresh-timer').checked = settings.enable_refresh_timer === true;
        document.getElementById('startup-delay').value = settings.startup_delay_minutes || 1;
        document.getElementById('refresh-interval').value = settings.refresh_interval_hours || 24;
        document.getElementById('enable-manufacturer-timing').checked = settings.enable_manufacturer_timing === true;
        document.getElementById('enable-sleep-mode').checked = settings.enable_sleep_mode !== false;
        document.getElementById('orientation').value = settings.orientation || 'landscape';
        
        // Update refresh interval field state based on refresh timer setting
        this.updateRefreshIntervalFieldState();
        
        // Update selected image display

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
                enable_startup_timer: document.getElementById('enable-startup-timer').checked,
                enable_refresh_timer: document.getElementById('enable-refresh-timer').checked,
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
    
    updateRefreshIntervalFieldState() {
        const refreshTimerCheckbox = document.getElementById('enable-refresh-timer');
        const refreshIntervalField = document.getElementById('refresh-interval');
        const refreshIntervalLabel = refreshIntervalField.previousElementSibling;
        
        if (refreshTimerCheckbox.checked) {
            // Refresh timer is enabled - enable the interval field
            refreshIntervalField.disabled = false;
            refreshIntervalField.style.opacity = '1';
            refreshIntervalLabel.style.opacity = '1';
        } else {
            // Refresh timer is disabled - disable the interval field
            refreshIntervalField.disabled = true;
            refreshIntervalField.style.opacity = '0.5';
            refreshIntervalLabel.style.opacity = '0.5';
        }
    }
    
    updateCurrentlyDisplayedImage() {
        const section = document.getElementById('currently-displayed-section');
        const info = document.getElementById('currently-displayed-info');
        
        if (this.currentlyDisplayedFile) {
            section.style.display = 'block';
            info.innerHTML = `
                <div class="selected-image-card">
                    <div class="selected-image-preview">
                        <img src="/thumbnails/${this.currentlyDisplayedFile.replace(/\.[^/.]+$/, '')}_thumb.jpg" 
                             alt="${this.currentlyDisplayedFile}" 
                             onerror="this.style.display='none'">
                    </div>
                    <div class="selected-image-details">
                        <h4>${this.currentlyDisplayedFile}</h4>
                        <p>This image is currently being displayed on the e-ink screen.</p>
                    </div>
                </div>
            `;
        } else {
            section.style.display = 'none';
        }
    }

}
    

    


// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new EinkDisplayManager();
}); 