// E-ink Display Manager JavaScript
class EinkDisplayManager {
    constructor() {
        this.selectedFiles = new Set();
        this.selectionMode = false;
        this.files = [];
        this.currentlyDisplayedFile = null;
        this.displayMode = 'manual';
        this.playlistData = null;

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

        // Load playlist data
        await this.loadPlaylistData();

        // Start polling for updates
        this.startPolling();
    }

    startPolling() {
        // Check status periodically
        setInterval(() => this.checkServerStatus(), 30000);

        // Update currently displayed file periodically - faster in playlist mode
        setInterval(() => {
            if (this.playlistData && this.playlistData.enabled) {
                // More frequent polling when playlist is active
                this.loadCurrentlyDisplayedFile();
            }
        }, 2000); // Every 2 seconds when playlist is active

        // Regular polling for currently displayed file
        setInterval(() => this.loadCurrentlyDisplayedFile(), 8000); // Every 8 seconds normally

        // Poll for new files periodically (every 10 seconds)
        setInterval(() => this.pollForNewFiles(), 10000);

        // Poll for playlist updates periodically (every 30 seconds)
        setInterval(() => this.loadPlaylistData(), 30000);
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

        // Playlist events
        document.getElementById('open-playlist').addEventListener('click', this.openPlaylist.bind(this));
        document.getElementById('playlist-cancel').addEventListener('click', this.closePlaylist.bind(this));
        document.getElementById('playlist-save').addEventListener('click', this.savePlaylist.bind(this));
        document.getElementById('playlist-modal').addEventListener('click', (e) => {
            if (e.target.id === 'playlist-modal') this.closePlaylist();
        });
        document.getElementById('playlist-advance').addEventListener('click', this.advancePlaylist.bind(this));
        document.getElementById('playlist-toggle').addEventListener('click', this.togglePlaylist.bind(this));
        // debug force-sync removed

        // Playlist management events
        document.getElementById('current-playlist').addEventListener('change', this.switchPlaylist.bind(this));
        document.getElementById('create-playlist-btn').addEventListener('click', this.createPlaylist.bind(this));
        document.getElementById('rename-playlist-btn').addEventListener('click', this.renamePlaylist.bind(this));
        document.getElementById('delete-playlist-btn').addEventListener('click', this.deletePlaylist.bind(this));

        // Main playlist selector event
        document.getElementById('main-playlist-selector').addEventListener('change', this.switchPlaylistMain.bind(this));

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
                const previousDisplayMode = this.displayMode;

                this.currentlyDisplayedFile = data.filename;
                this.displayMode = data.display_mode || 'manual';

                // If the displayed file or mode changed, update the display
                if (previousDisplayedFile !== this.currentlyDisplayedFile || previousDisplayMode !== this.displayMode) {
                    console.log(`Currently displayed file changed from ${previousDisplayedFile} to ${this.currentlyDisplayedFile} (mode: ${this.displayMode})`);
                    this.renderFiles(); // Refresh to update badges and styling
                }
            } else {
                this.currentlyDisplayedFile = null;
                this.displayMode = 'manual';
            }
        } catch (error) {
            console.error('Failed to load currently displayed file:', error);
            this.currentlyDisplayedFile = null;
            this.displayMode = 'manual';
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
                this.displayMode = data.display_mode || 'manual';
                console.log(`Force refreshed currently displayed file: ${this.currentlyDisplayedFile} (mode: ${this.displayMode})`);

                // Always re-render to ensure badges are updated
                this.renderFiles();
                this.updateCurrentlyDisplayedImage();
            } else {
                this.currentlyDisplayedFile = null;
                this.displayMode = 'manual';
                this.renderFiles();
                this.updateCurrentlyDisplayedImage();
            }
        } catch (error) {
            console.error('Failed to force refresh displayed file:', error);
            this.currentlyDisplayedFile = null;
            this.displayMode = 'manual';
            this.renderFiles();
            this.updateCurrentlyDisplayedImage();
        }
    }

    async pollForNewFiles() {
        try {
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

        // Determine display mode styling
        let modeClass = '';
        let modeIndicator = '';

        if (isCurrentlyDisplayed) {
            if (this.displayMode === 'live') {
                modeClass = 'live-mode';
                modeIndicator = '<div class="live-indicator">OVERRIDE</div>';
            } else if (this.displayMode === 'playlist') {
                modeClass = 'playlist-mode';
            }
        }

        // Debug logging
        if (isCurrentlyDisplayed) {
            console.log(`File ${file.filename} is marked as currently displayed (mode: ${this.displayMode})`);
        }

        return `
            <div class="file-card ${this.selectionMode ? 'selection-mode' : ''} ${isCurrentlyDisplayed ? 'currently-displayed' : ''} ${modeClass}" data-filename="${file.filename}">
                <div class="file-preview">
                    ${file.thumbnail ?
                        `<img src="${file.thumbnail}" alt="${file.filename}">` :
                        `<i class="fas ${iconClass} file-icon ${file.type}"></i>`
                    }
                    <input type="checkbox" class="file-checkbox" ${this.selectedFiles.has(file.filename) ? 'checked' : ''}>
                    ${isCurrentlyDisplayed ? '<div class="currently-displayed-badge"><i class="fas fa-tv"></i> Currently Displayed</div>' : ''}
                    ${modeIndicator}
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

                // Backend treats manual display as OVERRIDE (live). Reflect that immediately.
                this.currentlyDisplayedFile = filename;
                this.displayMode = 'live';
                this.updateCurrentlyDisplayedImage();

                // Refresh displayed file from server to confirm
                await this.loadCurrentlyDisplayedFile();

                // Refresh playlist state (live timeout, status UI)
                await this.loadPlaylistData();

                // Update file cards
                this.renderFiles();
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

            // Get mode-specific context info
            let contextInfo = 'This image is currently being displayed on the e-ink screen.';
            let modeIndicator = '';

            if (this.displayMode === 'playlist' && this.playlistData) {
                const currentPlaylist = this.playlistData.playlists[this.playlistData.current_playlist_name];
                if (currentPlaylist && currentPlaylist.files) {
                    const currentIndex = currentPlaylist.current_index || 0;
                    const totalFiles = currentPlaylist.files.length;
                    const playlistName = currentPlaylist.name || this.playlistData.current_playlist_name;
                    const randomMode = currentPlaylist.randomize ? ' (Random)' : '';

                    // Verify that the displayed file matches the playlist current file
                    const expectedFile = currentPlaylist.files[currentIndex];
                    if (expectedFile && expectedFile !== this.currentlyDisplayedFile) {
                        console.warn(`Playlist sync issue: expected ${expectedFile}, but displaying ${this.currentlyDisplayedFile}. Forcing refresh...`);
                        // Force a refresh of the currently displayed file
                        setTimeout(() => this.loadCurrentlyDisplayedFile(), 100);
                    }

                    contextInfo = `Displaying from playlist "${playlistName}"${randomMode} (${currentIndex + 1}/${totalFiles})`;
                    modeIndicator = '<span class="mode-badge playlist-mode-badge">PLAYLIST</span>';
                }
            } else if (this.displayMode === 'live') {
                contextInfo = 'Override is being displayed.';
                modeIndicator = '<span class="mode-badge live-mode-badge">OVERRIDE</span>';
            } else if (this.displayMode === 'manual') {
                contextInfo = 'Manually selected image is being displayed.';
                modeIndicator = '<span class="mode-badge manual-mode-badge">MANUAL</span>';
            }

            info.innerHTML = `
                <div class="selected-image-card">
                    <div class="selected-image-preview">
                        <img src="/thumbnails/${this.currentlyDisplayedFile.replace(/\.[^/.]+$/, '')}_thumb.jpg"
                             alt="${this.currentlyDisplayedFile}"
                             onerror="this.style.display='none'">
                    </div>
                    <div class="selected-image-details">
                        <h4>${this.currentlyDisplayedFile} ${modeIndicator}</h4>
                        <p>${contextInfo}</p>
                    </div>
                </div>
            `;
        } else {
            section.style.display = 'none';
        }
    }

    // ============ PLAYLIST MANAGEMENT ============

    async loadPlaylistData() {
        try {
            const response = await fetch('/api/playlist');
            if (response.ok) {
                this.playlistData = await response.json();
                this.displayMode = this.playlistData.display_mode || 'manual';
                this.updatePlaylistStatus();
            } else {
                console.error('Failed to load playlist data');
                this.playlistData = null;
            }
        } catch (error) {
            console.error('Error loading playlist data:', error);
            this.playlistData = null;
        }
    }

    updatePlaylistStatus() {
        const section = document.getElementById('playlist-status-section');
        const info = document.getElementById('playlist-status-info');

        // Update toggle button state
        this.updatePlaylistToggleButton();

        // Update main playlist selector
        this.updateMainPlaylistSelector();

        // debug force-sync button removed

        if (!this.playlistData || (!this.playlistData.enabled && this.displayMode !== 'live')) {
            section.style.display = 'none';
            return;
        }

        section.style.display = 'block';

        // Handle live mode display
        if (this.displayMode === 'live') {
            const liveStartTime = this.playlistData.live_mode_start_time * 1000;
            const liveTimeoutMinutes = this.playlistData.live_mode_timeout_minutes;

            let timeoutInfo = '';
            if (liveTimeoutMinutes > 0) {
                const timeoutEnd = liveStartTime + (liveTimeoutMinutes * 60 * 1000);
                const timeUntilTimeout = Math.max(0, timeoutEnd - Date.now());
                const minutesUntilTimeout = Math.ceil(timeUntilTimeout / (60 * 1000));
                timeoutInfo = `<p>Returns to playlist in: ${minutesUntilTimeout} minute(s)</p>`;
            } else {
                timeoutInfo = '<p>No timeout - stays in live mode</p>';
            }

            const liveText = 'Override is being displayed';

            info.innerHTML = `
                <div class="playlist-icon">
                    <i class="fas fa-broadcast-tower" style="color: #ef4444;"></i>
                </div>
                <div class="playlist-status-details">
                    <h4>Override Active</h4>
                    <p>${liveText}</p>
                    ${timeoutInfo}
                    <p>Playlist: ${this.playlistData.current_playlist_name || 'default'}</p>
                </div>
            `;
            return;
        }

        // Handle playlist mode display
        const currentPlaylist = this.playlistData.playlists[this.playlistData.current_playlist_name] || {};
        const currentFile = currentPlaylist.files && currentPlaylist.files[currentPlaylist.current_index] || 'None';
        const totalFiles = currentPlaylist.files ? currentPlaylist.files.length : 0;
        const intervalMinutes = this.playlistData.interval_minutes;

        // Use backend-calculated timing information
        let timingText = 'Calculating...';
        if (this.playlistData.timing_info && this.playlistData.timing_info.next_change_in_minutes !== undefined) {
            const minutesUntilNext = Math.ceil(this.playlistData.timing_info.next_change_in_minutes);
            timingText = `${minutesUntilNext} minute(s)`;
        }

        info.innerHTML = `
            <div class="playlist-icon">
                <i class="fas fa-list"></i>
            </div>
            <div class="playlist-status-details">
                <h4>Playlist Active (${(currentPlaylist.current_index || 0) + 1}/${totalFiles})</h4>
                <p>Playlist: ${this.playlistData.current_playlist_name || 'default'}</p>
                <p>Current: ${currentFile}</p>
                <p>Next change in: ${timingText}</p>
                <p>Interval: ${intervalMinutes} minutes</p>
            </div>
        `;
    }

    async openPlaylist() {
        try {
            // Load current playlist data
            await this.loadPlaylistData();

            // Populate playlist form
            this.populatePlaylistForm();

            // Show playlist modal
            document.getElementById('playlist-modal').style.display = 'flex';

        } catch (error) {
            console.error('Error opening playlist:', error);
            this.showToast('Failed to load playlist', 'error');
        }
    }

    closePlaylist() {
        document.getElementById('playlist-modal').style.display = 'none';
    }

    populatePlaylistForm() {
        if (!this.playlistData) return;

        // Set playlist settings
        document.getElementById('playlist-enabled').checked = this.playlistData.enabled || false;
        document.getElementById('playlist-interval').value = this.playlistData.interval_minutes || 5;
        document.getElementById('live-timeout').value = this.playlistData.live_mode_timeout_minutes || 30;

        // Populate playlist selector
        const playlistSelect = document.getElementById('current-playlist');
        playlistSelect.innerHTML = '';

        const playlists = this.playlistData.playlists || {};
        const currentPlaylistName = this.playlistData.current_playlist_name || 'default';

        Object.keys(playlists).forEach(playlistName => {
            const option = document.createElement('option');
            option.value = playlistName;
            option.textContent = playlists[playlistName].name || (playlistName.charAt(0).toUpperCase() + playlistName.slice(1) + ' Playlist');
            if (playlistName === currentPlaylistName) {
                option.selected = true;
            }
            playlistSelect.appendChild(option);
        });

        // Get current playlist files and settings
        const currentPlaylist = playlists[currentPlaylistName] || {};
        const playlistFiles = currentPlaylist.files || [];

        // Set randomize checkbox
        document.getElementById('playlist-randomize').checked = currentPlaylist.randomize || false;

        // Populate available files (only images)
        const availableFilesList = document.getElementById('available-files-list');
        const playlistFilesList = document.getElementById('playlist-files-list');

        availableFilesList.innerHTML = '';
        playlistFilesList.innerHTML = '';

        const availableFiles = this.playlistData.available_files || [];

        // Add available files (not in current playlist)
        availableFiles.forEach(file => {
            if (!playlistFiles.includes(file.filename)) {
                const item = this.createFileListItem(file.filename, 'available');
                availableFilesList.appendChild(item);
            }
        });

        // Add playlist files in order
        playlistFiles.forEach(filename => {
            const item = this.createFileListItem(filename, 'playlist');
            playlistFilesList.appendChild(item);
        });

        // Bind playlist file management events
        this.bindPlaylistEvents();
    }

    createFileListItem(filename, type) {
        const item = document.createElement('div');
        item.className = 'file-list-item';
        item.dataset.filename = filename;

        // Find the file info for thumbnails
        const fileInfo = this.files.find(f => f.filename === filename) ||
                        (this.playlistData && this.playlistData.available_files.find(f => f.filename === filename));

        let thumbnailHtml = '';
        if (fileInfo && fileInfo.thumbnail) {
            thumbnailHtml = `<img src="${fileInfo.thumbnail}" alt="${filename}" class="file-list-thumbnail">`;
        } else {
            const iconClass = this.getFileIconClass('image');
            thumbnailHtml = `<i class="fas ${iconClass} file-icon"></i>`;
        }

        item.innerHTML = `
            ${thumbnailHtml}
            <span class="file-name">${filename}</span>
            ${type === 'playlist' ? '<i class="fas fa-grip-vertical drag-handle"></i>' : ''}
        `;

        return item;
    }

    bindPlaylistEvents() {
        // Remove existing event listeners to prevent duplicates
        const addBtn = document.getElementById('add-to-playlist');
        const removeBtn = document.getElementById('remove-from-playlist');

        // Clone buttons to remove all event listeners
        const newAddBtn = addBtn.cloneNode(true);
        const newRemoveBtn = removeBtn.cloneNode(true);
        addBtn.parentNode.replaceChild(newAddBtn, addBtn);
        removeBtn.parentNode.replaceChild(newRemoveBtn, removeBtn);

        // File selection for available files
        const availableItems = document.querySelectorAll('#available-files-list .file-list-item');
        availableItems.forEach((item, index) => {
            // Firefox-compatible event handling
            item.addEventListener('click', (e) => {
                e.stopPropagation();
                // Don't preventDefault on click for Firefox compatibility
                item.classList.toggle('selected');
            }, false);

            // Prevent text selection on mousedown (Firefox compatible)
            item.addEventListener('mousedown', (e) => {
                e.preventDefault();
            }, false);

            // Prevent drag start (Firefox compatible)
            item.addEventListener('dragstart', (e) => {
                e.preventDefault();
                return false;
            }, false);
        });

        // File selection for playlist files
        document.querySelectorAll('#playlist-files-list .file-list-item').forEach(item => {
            // Firefox-compatible event handling
            item.addEventListener('click', (e) => {
                e.stopPropagation();
                item.classList.toggle('selected');
            }, false);

            // Prevent text selection on mousedown (Firefox compatible)
            item.addEventListener('mousedown', (e) => {
                e.preventDefault();
            }, false);
        });

        // Add to playlist button
        newAddBtn.addEventListener('click', () => {
            const selected = document.querySelectorAll('#available-files-list .file-list-item.selected');
            const playlistList = document.getElementById('playlist-files-list');

            selected.forEach(item => {
                item.classList.remove('selected');
                const filename = item.dataset.filename;
                const newItem = this.createFileListItem(filename, 'playlist');

                // Add event listeners to the new playlist item
                this.addPlaylistItemEvents(newItem);

                playlistList.appendChild(newItem);
                item.remove();
            });

            // Re-initialize drag and drop for the updated playlist
            this.initPlaylistDragAndDrop();
        });

        // Remove from playlist button
        newRemoveBtn.addEventListener('click', () => {
            const selected = document.querySelectorAll('#playlist-files-list .file-list-item.selected');
            const availableList = document.getElementById('available-files-list');

            selected.forEach(item => {
                item.classList.remove('selected');
                const filename = item.dataset.filename;
                const newItem = this.createFileListItem(filename, 'available');

                // Add event listeners to the new available item
                this.addAvailableItemEvents(newItem);

                availableList.appendChild(newItem);
                item.remove();
            });

            // Re-initialize drag and drop for the updated playlist
            this.initPlaylistDragAndDrop();
        });

        // Add drag and drop functionality for playlist reordering
        this.initPlaylistDragAndDrop();
    }

    addAvailableItemEvents(item) {
        // Firefox-compatible event handling for available files
        item.addEventListener('click', (e) => {
            e.stopPropagation();
            item.classList.toggle('selected');
        }, false);

        // Prevent text selection on mousedown (Firefox compatible)
        item.addEventListener('mousedown', (e) => {
            e.preventDefault();
        }, false);

        // Prevent drag start (Firefox compatible)
        item.addEventListener('dragstart', (e) => {
            e.preventDefault();
            return false;
        }, false);
    }

    addPlaylistItemEvents(item) {
        // Firefox-compatible event handling for playlist files
        item.addEventListener('click', (e) => {
            e.stopPropagation();
            item.classList.toggle('selected');
        }, false);

        // Prevent text selection on mousedown (Firefox compatible)
        item.addEventListener('mousedown', (e) => {
            e.preventDefault();
        }, false);
    }

    initPlaylistDragAndDrop() {
        const playlistList = document.getElementById('playlist-files-list');
        let draggedElement = null;

        document.querySelectorAll('#playlist-files-list .file-list-item').forEach(item => {
            // Only make playlist items draggable (not available items)
            item.draggable = true;

            item.addEventListener('dragstart', (e) => {
                draggedElement = item;
                item.classList.add('dragging');
                e.dataTransfer.effectAllowed = 'move';
                // Firefox-compatible data transfer
                e.dataTransfer.setData('text/plain', item.dataset.filename);
            }, false);

            item.addEventListener('dragend', () => {
                item.classList.remove('dragging');
                draggedElement = null;
            }, false);

            item.addEventListener('dragover', (e) => {
                e.preventDefault();
                e.dataTransfer.dropEffect = 'move';
            }, false);

            item.addEventListener('drop', (e) => {
                e.preventDefault();
                if (draggedElement && draggedElement !== item) {
                    const rect = item.getBoundingClientRect();
                    const midpoint = rect.top + rect.height / 2;

                    if (e.clientY < midpoint) {
                        playlistList.insertBefore(draggedElement, item);
                    } else {
                        playlistList.insertBefore(draggedElement, item.nextSibling);
                    }
                }
            }, false);
        });
    }

    async savePlaylist() {
        try {
            const enabled = document.getElementById('playlist-enabled').checked;
            const interval = parseInt(document.getElementById('playlist-interval').value);
            const liveTimeout = parseInt(document.getElementById('live-timeout').value);
            const currentPlaylistName = document.getElementById('current-playlist').value;
            const randomize = document.getElementById('playlist-randomize').checked;

            // Get playlist files in order
            const playlistItems = document.querySelectorAll('#playlist-files-list .file-list-item');
            const files = Array.from(playlistItems).map(item => item.dataset.filename);

            const playlistConfig = {
                enabled: enabled,
                interval_minutes: interval,
                live_mode_timeout_minutes: liveTimeout,
                current_playlist_name: currentPlaylistName,
                playlist_name: currentPlaylistName, // For updating specific playlist files
                files: files,
                randomize: randomize
            };

            const response = await fetch('/api/playlist', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(playlistConfig)
            });

            if (response.ok) {
                const result = await response.json();
                this.showToast('Playlist saved successfully', 'success');
                this.closePlaylist();

                // Reload playlist data and update display
                await this.loadPlaylistData();
                await this.loadCurrentlyDisplayedFile();
                this.renderFiles(); // Update file cards with new mode indicators
            } else {
                const error = await response.json();
                throw new Error(error.error || 'Failed to save playlist');
            }

        } catch (error) {
            console.error('Error saving playlist:', error);
            this.showToast(`Failed to save playlist: ${error.message}`, 'error');
        }
    }

    async switchPlaylist() {
        try {
            const selectedPlaylistName = document.getElementById('current-playlist').value;

            // Switch playlist in the backend
            const response = await fetch('/api/playlist/switch', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: selectedPlaylistName })
            });

            if (response.ok) {
                // Reload playlist data and update the file lists
                await this.loadPlaylistData();
                this.populatePlaylistForm();

                this.showToast(`Switched to playlist "${selectedPlaylistName}"`, 'success');
            } else {
                const error = await response.json();
                console.error('Failed to switch playlist:', error);
                this.showToast(`Failed to switch playlist: ${error.error}`, 'error');
            }

        } catch (error) {
            console.error('Error switching playlist:', error);
            this.showToast(`Failed to switch playlist: ${error.message}`, 'error');
        }
    }

    async switchPlaylistMain() {
        try {
            const selectedPlaylistName = document.getElementById('main-playlist-selector').value;

            // Switch playlist in the backend
            const response = await fetch('/api/playlist/switch', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: selectedPlaylistName })
            });

            if (response.ok) {
                // Reload playlist data and update UI
                await this.loadPlaylistData();
                await this.loadCurrentlyDisplayedFile();
                this.renderFiles();

                this.showToast(`Switched to playlist "${selectedPlaylistName}"`, 'success');
            } else {
                const error = await response.json();
                console.error('Failed to switch playlist:', error);
                this.showToast(`Failed to switch playlist: ${error.error}`, 'error');
            }

        } catch (error) {
            console.error('Error switching playlist:', error);
            this.showToast(`Failed to switch playlist: ${error.message}`, 'error');
        }
    }

    async createPlaylist() {
        try {
            const playlistName = prompt('Enter playlist name:');
            if (!playlistName || !playlistName.trim()) {
                return;
            }

            const trimmedName = playlistName.trim();

            const response = await fetch('/api/playlist/create', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name: trimmedName,
                    display_name: trimmedName.charAt(0).toUpperCase() + trimmedName.slice(1) + ' Playlist'
                })
            });

            if (response.ok) {
                this.showToast(`Playlist "${trimmedName}" created successfully`, 'success');

                // Switch to the new playlist in the backend
                const switchResponse = await fetch('/api/playlist/switch', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ name: trimmedName })
                });

                if (switchResponse.ok) {
                    // Reload playlist data and update form
                    await this.loadPlaylistData();
                    this.populatePlaylistForm();

                    // Ensure the dropdown shows the new playlist
                    document.getElementById('current-playlist').value = trimmedName;
                } else {
                    const switchError = await switchResponse.json();
                    console.error('Failed to switch to new playlist:', switchError);
                }
            } else {
                const error = await response.json();
                throw new Error(error.error || 'Failed to create playlist');
            }

        } catch (error) {
            console.error('Error creating playlist:', error);
            this.showToast(`Failed to create playlist: ${error.message}`, 'error');
        }
    }

    async renamePlaylist() {
        try {
            const selectedPlaylistName = document.getElementById('current-playlist').value;

            if (selectedPlaylistName === 'default') {
                this.showToast('Cannot rename the default playlist', 'error');
                return;
            }

            const newName = prompt(`Enter new name for playlist "${selectedPlaylistName}":`, selectedPlaylistName);
            if (!newName || !newName.trim() || newName.trim() === selectedPlaylistName) {
                return;
            }

            const trimmedNewName = newName.trim();

            const requestData = {
                old_name: selectedPlaylistName,
                new_name: trimmedNewName,
                display_name: trimmedNewName.charAt(0).toUpperCase() + trimmedNewName.slice(1) + ' Playlist'
            };

            console.log('Sending rename request:', requestData);

            const response = await fetch('/api/playlist/rename', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(requestData)
            });

            if (response.ok) {
                this.showToast(`Playlist renamed to "${trimmedNewName}" successfully`, 'success');

                // Reload playlist data and update form
                await this.loadPlaylistData();
                this.populatePlaylistForm();

                // Select the renamed playlist
                document.getElementById('current-playlist').value = trimmedNewName;
            } else {
                let errorMessage = 'Failed to rename playlist';
                try {
                    const error = await response.json();
                    errorMessage = error.error || errorMessage;
                } catch (parseError) {
                    // If JSON parsing fails, use the response text
                    const errorText = await response.text();
                    console.error('Failed to parse error response:', parseError);
                    console.error('Response text:', errorText);
                    errorMessage = `Server error: ${response.status} ${response.statusText}`;
                }
                throw new Error(errorMessage);
            }

        } catch (error) {
            console.error('Error renaming playlist:', error);
            this.showToast(`Failed to rename playlist: ${error.message}`, 'error');
        }
    }

    async deletePlaylist() {
        try {
            const selectedPlaylistName = document.getElementById('current-playlist').value;

            if (selectedPlaylistName === 'default') {
                this.showToast('Cannot delete the default playlist', 'error');
                return;
            }

            if (!confirm(`Are you sure you want to delete playlist "${selectedPlaylistName}"? This action cannot be undone.`)) {
                return;
            }

            const response = await fetch('/api/playlist/delete', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: selectedPlaylistName })
            });

            if (response.ok) {
                this.showToast(`Playlist "${selectedPlaylistName}" deleted successfully`, 'success');

                // Reload playlist data and update form
                await this.loadPlaylistData();
                this.populatePlaylistForm();
            } else {
                const error = await response.json();
                throw new Error(error.error || 'Failed to delete playlist');
            }

        } catch (error) {
            console.error('Error deleting playlist:', error);
            this.showToast(`Failed to delete playlist: ${error.message}`, 'error');
        }
    }

    async advancePlaylist() {
        try {
            const response = await fetch('/api/playlist/advance', {
                method: 'POST'
            });

            if (response.ok) {
                this.showToast('Playlist advanced', 'success');

                // Refresh playlist data and currently displayed file
                await this.loadPlaylistData();
                await this.loadCurrentlyDisplayedFile();
                this.renderFiles();
            } else {
                const error = await response.json();
                throw new Error(error.error || 'Failed to advance playlist');
            }

        } catch (error) {
            console.error('Error advancing playlist:', error);
            this.showToast(`Failed to advance playlist: ${error.message}`, 'error');
        }
    }

    updatePlaylistToggleButton() {
        const toggleBtn = document.getElementById('playlist-toggle');
        const toggleIcon = toggleBtn.querySelector('i');
        const toggleText = toggleBtn.querySelector('.toggle-text');

        if (!this.playlistData) {
            // No data loaded yet
            toggleBtn.setAttribute('data-enabled', 'false');
            toggleBtn.disabled = true;
            toggleIcon.className = 'fas fa-spinner fa-spin';
            toggleText.textContent = 'Loading...';
            return;
        }

        const isEnabled = this.playlistData.enabled;
        toggleBtn.setAttribute('data-enabled', isEnabled.toString());
        toggleBtn.disabled = false;

        // If live override is active, offer to start playlist
        if (this.displayMode === 'live') {
            toggleIcon.className = 'fas fa-play';
            toggleText.textContent = 'Start Playlist';
            // When in live, clicking the toggle should resume playlist immediately
            toggleBtn.onclick = async () => {
                try {
                    const resp = await fetch('/api/playlist/resume', { method: 'POST' });
                    if (resp.ok) {
                        this.showToast('Playlist resumed', 'success');
                        await this.loadPlaylistData();
                        await this.loadCurrentlyDisplayedFile();
                        this.renderFiles();
                    } else {
                        const err = await resp.json();
                        throw new Error(err.error || 'Failed to resume playlist');
                    }
                } catch (e) {
                    this.showToast(`Failed to resume playlist: ${e.message}`, 'error');
                }
            };
            return;
        }

        // Default behavior: toggle enabled state
        toggleBtn.onclick = null;
        if (isEnabled) {
            toggleIcon.className = 'fas fa-stop';
            toggleText.textContent = 'Stop Playlist';
        } else {
            toggleIcon.className = 'fas fa-play';
            toggleText.textContent = 'Start Playlist';
        }
    }

    updateMainPlaylistSelector() {
        const selector = document.getElementById('main-playlist-selector');

        if (!this.playlistData) {
            // No data loaded yet
            selector.innerHTML = '<option value="default">Loading...</option>';
            selector.disabled = true;
            return;
        }

        // Clear existing options
        selector.innerHTML = '';

        // Populate with available playlists
        const playlists = this.playlistData.playlists || {};
        const currentPlaylistName = this.playlistData.current_playlist_name || 'default';

        Object.keys(playlists).forEach(playlistName => {
            const playlist = playlists[playlistName];
            const option = document.createElement('option');
            option.value = playlistName;
            option.textContent = playlist.name || playlistName;

            if (playlistName === currentPlaylistName) {
                option.selected = true;
            }

            selector.appendChild(option);
        });

        selector.disabled = false;
    }

    async togglePlaylist() {
        try {
            if (!this.playlistData) {
                this.showToast('Please wait for playlist data to load', 'warning');
                return;
            }

            const newEnabled = !this.playlistData.enabled;

            // Update playlist enabled status
            const response = await fetch('/api/playlist', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    playlist_enabled: newEnabled,
                    playlist_interval_minutes: this.playlistData.interval_minutes,
                    live_mode_timeout_minutes: this.playlistData.live_mode_timeout_minutes,
                    playlist_current_name: this.playlistData.current_playlist_name,
                    playlist_files: this.playlistData.playlists[this.playlistData.current_playlist_name]?.files || []
                })
            });

            if (response.ok) {
                this.showToast(newEnabled ? 'Playlist started' : 'Playlist stopped', 'success');

                // Refresh playlist data and UI
                await this.loadPlaylistData();
                await this.loadCurrentlyDisplayedFile();
                this.renderFiles();
            } else {
                const error = await response.json();
                throw new Error(error.error || 'Failed to toggle playlist');
            }

        } catch (error) {
            console.error('Error toggling playlist:', error);
            this.showToast(`Failed to toggle playlist: ${error.message}`, 'error');
        }
    }

    // debug force-sync logic removed

}





// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new EinkDisplayManager();
});
