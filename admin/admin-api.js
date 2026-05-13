// Data Dictionary Application - Admin Interface with API
class DataDictionary {
    constructor() {
        this.entries = [];
        this.editingIndex = -1;
        this.changeHistory = [];
        this.tags = [];
        this.currentEntryTags = [];
        this.currentEntryLinks = [];
        this.currentReportDefinitions = [];
        this.allowDdIdEdit = false; // Configuration from API
        this.sortColumn = 'term'; // Default sort column
        this.sortDirection = 'asc'; // Default sort direction (asc or desc)
        this.apiBase = '/api';
        this.init();
    }

    async init() {
        // Load configuration first
        await this.loadConfig();
        
        // Load data from API
        await this.loadData();
        await this.loadChangeHistory();
        await this.loadTags();
        await this.loadOwners();
        await this.loadStewards();
        
        // Apply DD ID field configuration
        this.configureDdIdField();
        
        // Bind event listeners
        this.bindEvents();
        
        // Render initial table
        this.renderTable();
        this.populateTagSelect();
        this.populateReportDefTagSelect();
        this.populateLinkSelect();
    }

    bindEvents() {
        const form = document.getElementById('dictionary-form');
        const searchInput = document.getElementById('search-input');
        const filterType = document.getElementById('filter-type');
        const cancelBtn = document.getElementById('cancel-btn');
        const historyBtn = document.getElementById('view-history-btn');
        const closeHistoryBtn = document.getElementById('close-history-btn');
        const closeDetailBtn = document.getElementById('close-detail-btn');
        const addTagBtn = document.getElementById('add-tag-btn');
        const manageTagsBtn = document.getElementById('manage-tags-btn');
        const closeTagModalBtn = document.getElementById('close-tag-modal-btn');
        const createTagBtn = document.getElementById('create-tag-btn');
        const addLinkBtn = document.getElementById('add-link-btn');

        // Report definitions button
        const addReportDefBtn = document.getElementById('add-report-def-btn');

        // JSON backup/restore buttons
        const jsonBackupBtn = document.getElementById('json-backup-btn');
        const jsonRestoreBtn = document.getElementById('json-restore-btn');
        const jsonFileInput = document.getElementById('json-file-input');

        form.addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleSubmit();
        });

        searchInput.addEventListener('input', () => {
            this.saveFilterState();
            this.renderTable();
        });
        filterType.addEventListener('change', () => {
            this.saveFilterState();
            this.renderTable();
        });
        cancelBtn.addEventListener('click', () => this.cancelEdit());
        historyBtn.addEventListener('click', () => this.showHistory());
        closeHistoryBtn.addEventListener('click', () => this.hideHistory());
        closeDetailBtn.addEventListener('click', () => this.hideDetail());
        addTagBtn.addEventListener('click', () => this.addTagToEntry());
        document.getElementById('tag-select').addEventListener('change', () => this.addTagToEntry());
        manageTagsBtn.addEventListener('click', () => this.showTagManagement());
        closeTagModalBtn.addEventListener('click', () => this.hideTagManagement());
        createTagBtn.addEventListener('click', () => this.createTag());
        addLinkBtn.addEventListener('click', () => this.addLinkToEntry());
        addReportDefBtn.addEventListener('click', () => this.addReportDefinition());
        jsonBackupBtn.addEventListener('click', () => this.downloadJsonBackup());
        jsonRestoreBtn.addEventListener('click', () => jsonFileInput.click());
        jsonFileInput.addEventListener('change', (e) => this.handleJsonRestore(e));
        
        // Add event listeners for sortable column headers
        document.querySelectorAll('.sortable').forEach(th => {
            th.addEventListener('click', () => {
                const sortColumn = th.getAttribute('data-sort');
                if (sortColumn) {
                    this.setSortColumn(sortColumn);
                }
            });
        });
        
        // Initialize sort indicators
        this.updateSortIndicators();
        
        // Clear filters button
        const clearFiltersBtn = document.getElementById('clear-filters-btn');
        if (clearFiltersBtn) {
            clearFiltersBtn.addEventListener('click', () => this.clearFilters());
        }
        
        // Load saved filter state
        this.loadFilterState();
    }

    async handleSubmit() {
        const formData = {
            term: document.getElementById('term').value.trim(),
            definition: document.getElementById('definition').value.trim(),
            abbreviation: document.getElementById('abbreviation').value.trim(),
            dataType: document.getElementById('dataType').value,
            inputFormat: document.getElementById('inputFormat').value.trim(),
            variations: document.getElementById('variations').value.trim(),
            owner: document.getElementById('owner').value.trim(),
            stewards: document.getElementById('stewards').value.trim(),
            classification: document.getElementById('classification').value,
            discussion: document.getElementById('discussion').value.trim(),
            user: 'Admin'  // Will be replaced with Cloudflare Access user
        };

        // Include ddId only if editing is allowed
        if (this.allowDdIdEdit) {
            const ddId = document.getElementById('ddId').value.trim();
            if (ddId) {
                formData.ddId = ddId;
            }
        }

        try {
            let entryId;
            
            if (this.editingIndex === -1) {
                // Create new entry
                const response = await fetch(`${this.apiBase}/entries`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(formData)
                });

                if (!response.ok) throw new Error('Failed to create entry');
                
                const newEntry = await response.json();
                entryId = newEntry.id;
                
                // Sync tags and links for new entry
                await this.syncEntryTags(entryId);
                await this.syncEntryLinks(entryId);
                await this.syncReportDefinitions(entryId);
                
                alert('Entry created successfully!');
            } else {
                // Update existing entry
                entryId = this.entries[this.editingIndex].id;
                const response = await fetch(`${this.apiBase}/entries/${entryId}`, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(formData)
                });

                if (!response.ok) throw new Error('Failed to update entry');
                
                // Sync tags for existing entry (links are synced in real-time)
                await this.syncEntryTags(entryId);
                await this.syncReportDefinitions(entryId);
                
                alert('Entry updated successfully!');
                this.editingIndex = -1;
                document.getElementById('form-title').textContent = 'Add New Entry';
                document.getElementById('submit-btn').textContent = 'Add Entry';
                document.getElementById('cancel-btn').style.display = 'none';
            }

            await this.loadData();
            this.renderTable();
            this.resetForm();
        } catch (error) {
            console.error('Error:', error);
            alert('Error saving entry: ' + error.message);
        }
    }

    editEntry(index) {
        const entry = this.entries[index];
        this.editingIndex = index;

        // Populate form
        document.getElementById('ddId').value = entry.ddId || '';
        document.getElementById('term').value = entry.term;
        document.getElementById('definition').value = entry.definition;
        document.getElementById('abbreviation').value = entry.abbreviation || '';
        document.getElementById('dataType').value = entry.dataType || '';
        document.getElementById('inputFormat').value = entry.inputFormat || '';
        document.getElementById('variations').value = entry.variations || '';
        document.getElementById('owner').value = entry.owner || '';
        document.getElementById('stewards').value = entry.stewards || '';
        document.getElementById('classification').value = entry.classification || 'public';
        document.getElementById('discussion').value = entry.discussion || '';
        
        // Load tags (copy to avoid mutating the entry's tags array in this.entries)
        this.currentEntryTags = [...(entry.tags || [])];
        this.renderEntryTags();

        // Load report-specific definitions
        this.currentReportDefinitions = (entry.report_definitions || []).map(d => ({...d}));
        this.renderReportDefinitions();
        this.populateReportDefTagSelect();

        // Load links
        this.currentEntryLinks = entry.links || [];
        this.renderEntryLinks();
        this.populateLinkSelect(entry.id);

        // Update UI
        document.getElementById('form-title').textContent = 'Edit Entry';
        document.getElementById('submit-btn').textContent = 'Update Entry';
        document.getElementById('cancel-btn').style.display = 'inline-block';

        // Scroll to form
        document.querySelector('.form-section').scrollIntoView({ behavior: 'smooth' });
    }

    async deleteEntry(index) {
        const discussion = prompt('Optional: Provide a reason for deleting this entry (for change history):');
        if (confirm('Are you sure you want to delete this entry?')) {
            try {
                const entryId = this.entries[index].id;
                const response = await fetch(`${this.apiBase}/entries/${entryId}`, {
                    method: 'DELETE',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ user: 'Admin', discussion: discussion || '' })
                });

                if (!response.ok) throw new Error('Failed to delete entry');
                
                alert('Entry deleted successfully!');
                await this.loadData();
                this.renderTable();
            } catch (error) {
                console.error('Error:', error);
                alert('Error deleting entry: ' + error.message);
            }
        }
    }

    cancelEdit() {
        this.editingIndex = -1;
        this.currentEntryTags = [];
        this.currentEntryLinks = [];
        this.currentReportDefinitions = [];
        this.renderEntryTags();
        this.renderEntryLinks();
        this.renderReportDefinitions();
        this.resetForm();
        document.getElementById('form-title').textContent = 'Add New Entry';
        document.getElementById('submit-btn').textContent = 'Add Entry';
        document.getElementById('cancel-btn').style.display = 'none';
    }

    resetForm() {
        document.getElementById('dictionary-form').reset();
        document.getElementById('classification').value = 'public'; // Reset to default
        this.currentEntryTags = [];
        this.currentEntryLinks = [];
        this.currentReportDefinitions = [];
        this.renderEntryTags();
        this.renderEntryLinks();
        this.renderReportDefinitions();
        this.populateLinkSelect(); // Refresh the link dropdown
    }

    filterEntries() {
        const searchTerm = document.getElementById('search-input').value.toLowerCase();
        const filterType = document.getElementById('filter-type').value;

        let filtered = this.entries.filter(entry => {
            // Search filter
            const matchesSearch = !searchTerm || 
                entry.term.toLowerCase().includes(searchTerm) ||
                entry.definition.toLowerCase().includes(searchTerm) ||
                (entry.abbreviation && entry.abbreviation.toLowerCase().includes(searchTerm)) ||
                (entry.variations && entry.variations.toLowerCase().includes(searchTerm));

            // Type filter
            const matchesType = !filterType || entry.dataType === filterType;

            return matchesSearch && matchesType;
        });

        // Apply sorting
        return this.sortEntries(filtered);
    }

    sortEntries(entries) {
        return entries.sort((a, b) => {
            let aVal, bVal;
            
            // Get values based on sort column
            switch (this.sortColumn) {
                case 'ddId':
                    aVal = a.ddId || '';
                    bVal = b.ddId || '';
                    // Natural sort for DD IDs (e.g., DD2, DD10, DD100)
                    const aNum = parseInt((aVal.match(/\d+/) || ['0'])[0]);
                    const bNum = parseInt((bVal.match(/\d+/) || ['0'])[0]);
                    return this.sortDirection === 'asc' ? aNum - bNum : bNum - aNum;
                case 'term':
                    aVal = a.term.toLowerCase();
                    bVal = b.term.toLowerCase();
                    break;
                case 'abbreviation':
                    aVal = (a.abbreviation || '').toLowerCase();
                    bVal = (b.abbreviation || '').toLowerCase();
                    break;
                case 'dataType':
                    aVal = (a.dataType || '').toLowerCase();
                    bVal = (b.dataType || '').toLowerCase();
                    break;
                case 'owner':
                    aVal = (a.owner || '').toLowerCase();
                    bVal = (b.owner || '').toLowerCase();
                    break;
                case 'classification':
                    aVal = (a.classification || '').toLowerCase();
                    bVal = (b.classification || '').toLowerCase();
                    break;
                default:
                    aVal = '';
                    bVal = '';
            }
            
            // Compare values
            if (aVal < bVal) return this.sortDirection === 'asc' ? -1 : 1;
            if (aVal > bVal) return this.sortDirection === 'asc' ? 1 : -1;
            return 0;
        });
    }

    setSortColumn(column) {
        // Toggle direction if same column, otherwise reset to ascending
        if (this.sortColumn === column) {
            this.sortDirection = this.sortDirection === 'asc' ? 'desc' : 'asc';
        } else {
            this.sortColumn = column;
            this.sortDirection = 'asc';
        }
        this.updateSortIndicators();
        this.renderTable();
    }

    updateSortIndicators() {
        // Remove all sort indicators
        document.querySelectorAll('.sortable').forEach(th => {
            th.classList.remove('sort-asc', 'sort-desc');
        });
        
        // Add indicator to current sort column
        const currentHeader = document.querySelector(`[data-sort="${this.sortColumn}"]`);
        if (currentHeader) {
            currentHeader.classList.add(this.sortDirection === 'asc' ? 'sort-asc' : 'sort-desc');
        }
    }

    saveFilterState() {
        const searchInput = document.getElementById('search-input');
        const filterType = document.getElementById('filter-type');
        
        const filterState = {
            searchTerm: searchInput.value,
            dataType: filterType.value
        };
        
        localStorage.setItem('dataDictionary_filters', JSON.stringify(filterState));
    }

    loadFilterState() {
        try {
            const saved = localStorage.getItem('dataDictionary_filters');
            if (saved) {
                const filterState = JSON.parse(saved);
                const searchInput = document.getElementById('search-input');
                const filterType = document.getElementById('filter-type');
                
                if (filterState.searchTerm) {
                    searchInput.value = filterState.searchTerm;
                }
                if (filterState.dataType) {
                    filterType.value = filterState.dataType;
                }
                
                // Re-render table with loaded filters
                this.renderTable();
            }
        } catch (error) {
            console.error('Error loading filter state:', error);
        }
    }

    clearFilters() {
        const searchInput = document.getElementById('search-input');
        const filterType = document.getElementById('filter-type');
        
        searchInput.value = '';
        filterType.value = '';
        
        localStorage.removeItem('dataDictionary_filters');
        this.renderTable();
    }

    renderTable() {
        const tbody = document.getElementById('dictionary-tbody');
        const noEntries = document.getElementById('no-entries');
        const filteredEntries = this.filterEntries();

        tbody.innerHTML = '';

        if (filteredEntries.length === 0) {
            noEntries.style.display = 'block';
            return;
        }

        noEntries.style.display = 'none';

        filteredEntries.forEach((entry, index) => {
            const actualIndex = this.entries.indexOf(entry);
            const row = document.createElement('tr');
            
            // Render tags
            let tagsHtml = '';
            if (entry.tags && entry.tags.length > 0) {
                tagsHtml = entry.tags.map(tag => 
                    `<span class="tag" style="background-color: ${tag.color}">${this.escapeHtml(tag.name)}</span>`
                ).join(' ');
            }
            
            row.innerHTML = `
                <td>${entry.ddId ? `<span class="badge" style="background-color: #6c757d; font-family: monospace;">${this.escapeHtml(entry.ddId)}</span>` : '<span class="text-muted">—</span>'}</td>
                <td>
                    <strong>${this.escapeHtml(entry.term)}</strong>
                    ${tagsHtml ? `<div style="margin-top: 5px;">${tagsHtml}</div>` : ''}
                </td>
                <td>${this.escapeHtml(entry.definition)}</td>
                <td>${entry.abbreviation ? this.escapeHtml(entry.abbreviation) : '<span class="text-muted">—</span>'}</td>
                <td>${entry.dataType ? `<span class="badge">${this.escapeHtml(entry.dataType)}</span>` : '<span class="text-muted">—</span>'}</td>
                <td>${entry.inputFormat ? `<code>${this.escapeHtml(entry.inputFormat)}</code>` : '<span class="text-muted">—</span>'}</td>
                <td>${entry.variations ? this.escapeHtml(entry.variations) : '<span class="text-muted">—</span>'}</td>
                <td>${entry.owner ? this.escapeHtml(entry.owner) : '<span class="text-muted">—</span>'}</td>
                <td>${entry.stewards ? this.escapeHtml(entry.stewards) : '<span class="text-muted">—</span>'}</td>
                <td>${entry.classification ? `<span class="classification-${entry.classification}">${this.escapeHtml(entry.classification.charAt(0).toUpperCase() + entry.classification.slice(1))}</span>` : '<span class="text-muted">—</span>'}</td>
                <td>
                    <div class="actions-cell">
                        <button class="btn btn-edit" onclick="dictionary.editEntry(${actualIndex})">✏️ Edit</button>
                        <button class="btn btn-delete" onclick="dictionary.deleteEntry(${actualIndex})">🗑️ Delete</button>
                    </div>
                </td>
            `;

            tbody.appendChild(row);
        });
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    async loadConfig() {
        try {
            const response = await fetch(`${this.apiBase}/config`);
            if (!response.ok) throw new Error('Failed to load config');
            const config = await response.json();
            this.allowDdIdEdit = config.allowDdIdEdit || false;
            console.log(`DD ID editing is ${this.allowDdIdEdit ? 'enabled' : 'disabled'}`);
        } catch (error) {
            console.error('Error loading config:', error);
            this.allowDdIdEdit = false; // Default to disabled on error
        }
    }

    configureDdIdField() {
        const ddIdField = document.getElementById('ddId');
        if (ddIdField) {
            if (this.allowDdIdEdit) {
                ddIdField.removeAttribute('readonly');
                ddIdField.style.backgroundColor = '';
                ddIdField.style.cursor = '';
                ddIdField.placeholder = 'e.g., DD1';
                const helpText = ddIdField.parentElement.querySelector('small');
                if (helpText) {
                    helpText.textContent = '⚠️ DD ID editing is enabled - use with caution';
                    helpText.style.color = '#d97706';
                }
            } else {
                ddIdField.setAttribute('readonly', 'readonly');
                ddIdField.style.backgroundColor = '#f5f5f5';
                ddIdField.style.cursor = 'not-allowed';
                ddIdField.placeholder = 'Auto-assigned';
                const helpText = ddIdField.parentElement.querySelector('small');
                if (helpText) {
                    helpText.textContent = 'DD IDs can only be modified directly in the database';
                    helpText.style.color = '#666';
                }
            }
        }
    }

    async loadData() {
        try {
            const response = await fetch(`${this.apiBase}/entries`);
            if (!response.ok) throw new Error('Failed to load data');
            this.entries = await response.json();
        } catch (error) {
            console.error('Error loading data:', error);
            alert('Error loading data from server. Please check if the API is running.');
            this.entries = [];
        }
    }

    async loadChangeHistory() {
        try {
            const response = await fetch(`${this.apiBase}/history`);
            if (!response.ok) throw new Error('Failed to load history');
            this.changeHistory = await response.json();
        } catch (error) {
            console.error('Error loading history:', error);
            this.changeHistory = [];
        }
    }

    async showHistory() {
        await this.loadChangeHistory();
        const modal = document.getElementById('history-modal');
        modal.style.display = 'flex';
        this.renderHistory();
    }

    hideHistory() {
        document.getElementById('history-modal').style.display = 'none';
    }

    hideDetail() {
        document.getElementById('detail-modal').style.display = 'none';
    }

    renderHistory() {
        const tbody = document.getElementById('history-tbody');
        tbody.innerHTML = '';

        if (this.changeHistory.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" style="text-align:center; padding:40px;">No changes recorded yet.</td></tr>';
            return;
        }

        this.changeHistory.forEach((change, index) => {
            const row = document.createElement('tr');
            const timestamp = new Date(change.timestamp).toLocaleString();
            
            let actionBadge = '';
            if (change.action === 'create') {
                actionBadge = '<span class="badge badge-create">Created</span>';
            } else if (change.action === 'update') {
                actionBadge = '<span class="badge badge-update">Updated</span>';
            } else if (change.action === 'delete') {
                actionBadge = '<span class="badge badge-delete">Deleted</span>';
            } else if (change.action === 'tag_added') {
                actionBadge = '<span class="badge badge-create">Tag Added</span>';
            } else if (change.action === 'tag_removed') {
                actionBadge = '<span class="badge badge-delete">Tag Removed</span>';
            } else if (change.action === 'report_def_added') {
                actionBadge = '<span class="badge badge-create">Definition Added</span>';
            } else if (change.action === 'report_def_updated') {
                actionBadge = '<span class="badge badge-update">Definition Updated</span>';
            } else if (change.action === 'report_def_removed') {
                actionBadge = '<span class="badge badge-delete">Definition Removed</span>';
            }

            let changes = '';
            if (change.action === 'create') {
                changes = 'New entry created';
            } else if (change.action === 'delete') {
                changes = 'Entry deleted';
            } else if (change.action === 'update' && change.oldData && change.newData) {
                const changedFields = [];
                for (let key in change.newData) {
                    if (key !== 'updatedAt' && key !== 'createdAt' && key !== 'user' && key !== 'discussion' && change.oldData[key] !== change.newData[key]) {
                        changedFields.push(key);
                    }
                }
                changes = changedFields.length > 0 ? `Modified: ${changedFields.join(', ')}` : 'No changes detected';
            } else if (change.action === 'tag_added' && change.newData) {
                changes = `Report added: ${this.escapeHtml(change.newData.tag_name)}`;
            } else if (change.action === 'tag_removed' && change.oldData) {
                changes = `Report removed: ${this.escapeHtml(change.oldData.tag_name)}`;
            } else if (change.action === 'report_def_added' && change.newData) {
                changes = `Definition added for: ${this.escapeHtml(change.newData.tag_name)}`;
            } else if (change.action === 'report_def_updated' && change.newData) {
                changes = `Definition updated for: ${this.escapeHtml(change.newData.tag_name)}`;
            } else if (change.action === 'report_def_removed' && change.oldData) {
                changes = `Definition removed for: ${this.escapeHtml(change.oldData.tag_name)}`;
            }

            // Add discussion indicator if present
            const discussionIndicator = change.discussion ? ' 💬' : '';

            row.innerHTML = `
                <td>${timestamp}</td>
                <td>${actionBadge}</td>
                <td><strong>${this.escapeHtml(change.term)}</strong>${discussionIndicator}</td>
                <td>${changes}</td>
                <td>${this.escapeHtml(change.user)}</td>
                <td><button class="btn btn-small" onclick="dictionary.viewChangeDetail(${index})">View Details</button></td>
            `;
            tbody.appendChild(row);
        });
    }

    viewChangeDetail(index) {
        const change = this.changeHistory[index];
        const modal = document.getElementById('detail-modal');
        const content = document.getElementById('detail-content');
        
        let html = '';

        // Header section with basic info
        html += `
            <div class="detail-section">
                <h3>Change Information</h3>
                <div class="detail-info">
                    <div class="detail-label">Timestamp:</div>
                    <div class="detail-value">${new Date(change.timestamp).toLocaleString()}</div>
                    
                    <div class="detail-label">Action:</div>
                    <div class="detail-value">
                        ${change.action === 'create' ? '<span class="badge badge-create">Created</span>' : ''}
                        ${change.action === 'update' ? '<span class="badge badge-update">Updated</span>' : ''}
                        ${change.action === 'delete' ? '<span class="badge badge-delete">Deleted</span>' : ''}
                        ${change.action === 'tag_added' ? '<span class="badge badge-create">Tag Added</span>' : ''}
                        ${change.action === 'tag_removed' ? '<span class="badge badge-delete">Tag Removed</span>' : ''}
                        ${change.action === 'report_def_added' ? '<span class="badge badge-create">Definition Added</span>' : ''}
                        ${change.action === 'report_def_updated' ? '<span class="badge badge-update">Definition Updated</span>' : ''}
                        ${change.action === 'report_def_removed' ? '<span class="badge badge-delete">Definition Removed</span>' : ''}
                    </div>
                    
                    <div class="detail-label">Term:</div>
                    <div class="detail-value"><strong>${this.escapeHtml(change.term)}</strong></div>
                    
                    <div class="detail-label">User:</div>
                    <div class="detail-value">${this.escapeHtml(change.user)}</div>
                </div>
                ${change.discussion ? `
                    <div class="discussion-box">
                        <strong>💬 Discussion:</strong><br>
                        ${this.escapeHtml(change.discussion)}
                    </div>
                ` : ''}
            </div>
        `;

        // Data changes section
        if (change.action === 'create' && change.newData) {
            const data = typeof change.newData === 'string' ? JSON.parse(change.newData) : change.newData;
            html += `
                <div class="detail-section">
                    <h3>New Entry Data</h3>
                    <div class="change-column change-column-new">
                        ${this.formatFieldData(data)}
                    </div>
                </div>
            `;
        } else if (change.action === 'delete' && change.oldData) {
            const data = typeof change.oldData === 'string' ? JSON.parse(change.oldData) : change.oldData;
            html += `
                <div class="detail-section">
                    <h3>Deleted Entry Data</h3>
                    <div class="change-column change-column-old">
                        ${this.formatFieldData(data)}
                    </div>
                </div>
            `;
        } else if (change.action === 'update' && change.oldData && change.newData) {
            const oldData = typeof change.oldData === 'string' ? JSON.parse(change.oldData) : change.oldData;
            const newData = typeof change.newData === 'string' ? JSON.parse(change.newData) : change.newData;
            
            const changedFields = [];
            for (let key in newData) {
                if (key !== 'updatedAt' && key !== 'createdAt' && key !== 'user' && key !== 'discussion' && key !== 'id' && oldData[key] !== newData[key]) {
                    changedFields.push({
                        field: key,
                        oldValue: oldData[key],
                        newValue: newData[key]
                    });
                }
            }

            if (changedFields.length > 0) {
                html += `
                    <div class="detail-section">
                        <h3>Field Changes</h3>
                        <div class="change-comparison">
                            <div class="change-column change-column-old">
                                <h4>Before</h4>
                                ${changedFields.map(f => `
                                    <div class="field-change">
                                        <div class="field-name">${this.escapeHtml(f.field)}</div>
                                        <div class="field-value ${!f.oldValue ? 'empty-value' : ''}">
                                            ${f.oldValue ? this.escapeHtml(String(f.oldValue)) : '(empty)'}
                                        </div>
                                    </div>
                                `).join('')}
                            </div>
                            <div class="change-column change-column-new">
                                <h4>After</h4>
                                ${changedFields.map(f => `
                                    <div class="field-change">
                                        <div class="field-name">${this.escapeHtml(f.field)}</div>
                                        <div class="field-value ${!f.newValue ? 'empty-value' : ''}">
                                            ${f.newValue ? this.escapeHtml(String(f.newValue)) : '(empty)'}
                                        </div>
                                    </div>
                                `).join('')}
                            </div>
                        </div>
                    </div>
                `;
            } else {
                html += '<div class="no-changes">No field changes detected</div>';
            }
        } else if (['tag_added', 'tag_removed', 'report_def_added', 'report_def_updated', 'report_def_removed'].includes(change.action)) {
            const isAdded = change.action === 'tag_added' || change.action === 'report_def_added';
            const isRemoved = change.action === 'tag_removed' || change.action === 'report_def_removed';
            const isUpdated = change.action === 'report_def_updated';
            const isTag = change.action === 'tag_added' || change.action === 'tag_removed';

            if (isUpdated && change.oldData && change.newData) {
                html += `
                    <div class="detail-section">
                        <h3>Definition Change — ${this.escapeHtml(change.newData.tag_name)}</h3>
                        <div class="change-comparison">
                            <div class="change-column change-column-old">
                                <h4>Before</h4>
                                <div class="field-change">
                                    <div class="field-name">definition</div>
                                    <div class="field-value ${!change.oldData.definition ? 'empty-value' : ''}">
                                        ${change.oldData.definition ? this.escapeHtml(change.oldData.definition) : '(empty)'}
                                    </div>
                                </div>
                            </div>
                            <div class="change-column change-column-new">
                                <h4>After</h4>
                                <div class="field-change">
                                    <div class="field-name">definition</div>
                                    <div class="field-value ${!change.newData.definition ? 'empty-value' : ''}">
                                        ${change.newData.definition ? this.escapeHtml(change.newData.definition) : '(empty)'}
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                `;
            } else {
                const data = isAdded ? change.newData : change.oldData;
                const colClass = isAdded ? 'change-column-new' : 'change-column-old';
                const heading = isTag
                    ? (isAdded ? 'Report Added' : 'Report Removed')
                    : (isAdded ? 'Definition Added' : 'Definition Removed');
                html += `
                    <div class="detail-section">
                        <h3>${heading}</h3>
                        <div class="change-column ${colClass}">
                            <div class="field-change">
                                <div class="field-name">report</div>
                                <div class="field-value">${this.escapeHtml(data.tag_name)}</div>
                            </div>
                            ${!isTag && data.definition !== undefined ? `
                                <div class="field-change">
                                    <div class="field-name">definition</div>
                                    <div class="field-value ${!data.definition ? 'empty-value' : ''}">
                                        ${data.definition ? this.escapeHtml(data.definition) : '(empty)'}
                                    </div>
                                </div>
                            ` : ''}
                        </div>
                    </div>
                `;
            }
        }

        content.innerHTML = html;
        modal.style.display = 'flex';
    }

    formatFieldData(data) {
        const fields = ['term', 'definition', 'abbreviation', 'dataType', 'inputFormat', 'variations'];
        return fields.map(field => {
            if (data[field] !== undefined && data[field] !== null && data[field] !== '') {
                return `
                    <div class="field-change">
                        <div class="field-name">${this.escapeHtml(field)}</div>
                        <div class="field-value">${this.escapeHtml(String(data[field]))}</div>
                    </div>
                `;
            }
            return '';
        }).join('');
    }

    // Tag Management Methods
    async loadTags() {
        try {
            const response = await fetch(`${this.apiBase}/tags`);
            if (!response.ok) throw new Error('Failed to load tags');
            this.tags = await response.json();
        } catch (error) {
            console.error('Error loading tags:', error);
            this.tags = [];
        }
    }

    populateTagSelect() {
        const select = document.getElementById('tag-select');
        select.innerHTML = '<option value="">-- Select a report --</option>';
        this.tags.forEach(tag => {
            const option = document.createElement('option');
            option.value = tag.id;
            option.textContent = tag.name;
            select.appendChild(option);
        });
    }

    renderEntryTags() {
        const container = document.getElementById('entry-tags-container');
        container.innerHTML = '';
        
        this.currentEntryTags.forEach(tag => {
            const tagEl = document.createElement('span');
            tagEl.className = 'tag';
            tagEl.style.backgroundColor = tag.color;
            tagEl.innerHTML = `
                ${this.escapeHtml(tag.name)}
                <button class="tag-remove" onclick="dictionary.removeTagFromEntry(${tag.id})">×</button>
            `;
            container.appendChild(tagEl);
        });
    }

    addTagToEntry() {
        const select = document.getElementById('tag-select');
        const tagId = parseInt(select.value);
        
        if (!tagId) return;

        const tag = this.tags.find(t => t.id === tagId);
        if (!tag) return;

        // Check if tag already added
        if (this.currentEntryTags.find(t => t.id === tagId)) return;

        this.currentEntryTags.push(tag);
        this.renderEntryTags();
        select.value = '';
    }

    removeTagFromEntry(tagId) {
        this.currentEntryTags = this.currentEntryTags.filter(t => t.id !== tagId);
        this.renderEntryTags();
    }

    async syncEntryTags(entryId) {
        try {
            // Get current tags from server
            const entry = this.entries.find(e => e.id === entryId);
            const serverTagIds = new Set((entry?.tags || []).map(t => t.id));
            const clientTagIds = new Set(this.currentEntryTags.map(t => t.id));

            // Add new tags
            for (const tag of this.currentEntryTags) {
                if (!serverTagIds.has(tag.id)) {
                    await fetch(`${this.apiBase}/entries/${entryId}/tags`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ tag_id: tag.id })
                    });
                }
            }

            // Remove old tags
            for (const tag of (entry?.tags || [])) {
                if (!clientTagIds.has(tag.id)) {
                    await fetch(`${this.apiBase}/entries/${entryId}/tags/${tag.id}`, {
                        method: 'DELETE'
                    });
                }
            }
        } catch (error) {
            console.error('Error syncing tags:', error);
        }
    }

    showTagManagement() {
        document.getElementById('tag-modal').style.display = 'flex';
        this.renderTagsList();
    }

    hideTagManagement() {
        document.getElementById('tag-modal').style.display = 'none';
    }

    async createTag() {
        const name = document.getElementById('new-tag-name').value.trim();
        const color = document.getElementById('new-tag-color').value;

        if (!name) {
            alert('Please enter a report name');
            return;
        }

        try {
            const response = await fetch(`${this.apiBase}/tags`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, color })
            });

            if (!response.ok) throw new Error('Failed to create tag');

            document.getElementById('new-tag-name').value = '';
            document.getElementById('new-tag-color').value = '#004C8E';
            
            await this.loadTags();
            this.populateTagSelect();
            this.populateReportDefTagSelect();
            this.renderTagsList();
            alert('Report created successfully!');
        } catch (error) {
            console.error('Error creating tag:', error);
            alert('Error creating report: ' + error.message);
        }
    }

    async deleteTag(tagId) {
        if (!confirm('Are you sure you want to delete this report? It will be removed from all entries.')) {
            return;
        }

        try {
            const response = await fetch(`${this.apiBase}/tags/${tagId}`, {
                method: 'DELETE'
            });

            if (!response.ok) throw new Error('Failed to delete tag');

            await this.loadTags();
            await this.loadData();
            this.populateTagSelect();
            this.populateReportDefTagSelect();
            this.renderTagsList();
            this.renderTable();
            alert('Report deleted successfully!');
        } catch (error) {
            console.error('Error deleting tag:', error);
            alert('Error deleting report: ' + error.message);
        }
    }

    renderTagsList() {
        const list = document.getElementById('tags-list');
        list.innerHTML = '';

        if (this.tags.length === 0) {
            list.innerHTML = '<p style="text-align:center; color:#999;">No tags created yet.</p>';
            return;
        }

        this.tags.forEach(tag => {
            const item = document.createElement('div');
            item.className = 'tag-item';
            item.innerHTML = `
                <div class="tag-item-info">
                    <div class="tag-color-box" style="background-color: ${tag.color}"></div>
                    <strong>${this.escapeHtml(tag.name)}</strong>
                </div>
                <button class="btn btn-delete btn-small" onclick="dictionary.deleteTag(${tag.id})">Delete</button>
            `;
            list.appendChild(item);
        });
    }

    async loadOwners() {
        try {
            const response = await fetch(`${this.apiBase}/owners`);
            if (!response.ok) throw new Error('Failed to load owners');
            const owners = await response.json();
            this.populateDatalist('owner-suggestions', owners);
        } catch (error) {
            console.error('Error loading owners:', error);
        }
    }

    async loadStewards() {
        try {
            const response = await fetch(`${this.apiBase}/stewards`);
            if (!response.ok) throw new Error('Failed to load stewards');
            const stewards = await response.json();
            this.populateDatalist('steward-suggestions', stewards);
        } catch (error) {
            console.error('Error loading stewards:', error);
        }
    }

    populateDatalist(datalistId, options) {
        const datalist = document.getElementById(datalistId);
        if (!datalist) return;
        
        datalist.innerHTML = '';
        options.forEach(option => {
            const optionElement = document.createElement('option');
            optionElement.value = option;
            datalist.appendChild(optionElement);
        });
    }

    // Link Management Functions
    async populateLinkSelect(currentEntryId = null) {
        const select = document.getElementById('link-select');
        if (!select) return;
        
        select.innerHTML = '<option value="">Select an entry to link...</option>';
        
        // Filter out the current entry if editing
        const availableEntries = this.entries.filter(e => e.id !== currentEntryId);
        
        availableEntries.forEach(entry => {
            const option = document.createElement('option');
            option.value = entry.id;
            option.textContent = entry.term;
            select.appendChild(option);
        });
    }

    renderEntryLinks() {
        const container = document.getElementById('entry-links-container');
        if (!container) return;
        
        container.innerHTML = '';
        
        if (this.currentEntryLinks.length === 0) {
            container.innerHTML = '<p style="color:#999; font-size:0.9em;">No linked entries yet.</p>';
            return;
        }

        this.currentEntryLinks.forEach(link => {
            const linkDiv = document.createElement('div');
            linkDiv.className = 'entry-link-item';
            linkDiv.style.cssText = 'display:flex; align-items:center; gap:10px; padding:8px; background:#f5f5f5; border-radius:4px; margin-bottom:8px;';
            linkDiv.innerHTML = `
                <span style="flex:1;">${this.escapeHtml(link.target_term)}</span>
                <button class="btn btn-delete btn-small" onclick="dictionary.removeLinkFromEntry(${link.link_id || link.target_entry_id})">Remove</button>
            `;
            container.appendChild(linkDiv);
        });
    }

    async addLinkToEntry() {
        const select = document.getElementById('link-select');
        const targetEntryId = parseInt(select.value);
        
        if (!targetEntryId) {
            alert('Please select an entry to link');
            return;
        }

        // Check if link already added
        if (this.currentEntryLinks.find(l => l.target_entry_id === targetEntryId)) {
            alert('Entry already linked');
            return;
        }

        // Find the target entry to get its term
        const targetEntry = this.entries.find(e => e.id === targetEntryId);
        if (!targetEntry) return;

        // If editing existing entry, save immediately
        if (this.editingIndex !== -1) {
            const sourceEntryId = this.entries[this.editingIndex].id;
            
            try {
                const response = await fetch(`${this.apiBase}/entries/${sourceEntryId}/links`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ 
                        target_entry_id: targetEntryId,
                        link_type: 'see_also'
                    })
                });

                if (!response.ok) throw new Error('Failed to add link');
                
                const newLink = await response.json();
                this.currentEntryLinks.push(newLink);
                this.renderEntryLinks();
                select.value = '';
                
                // Reload data to update links
                await this.loadData();
                this.renderTable();
            } catch (error) {
                console.error('Error adding link:', error);
                alert('Error adding link: ' + error.message);
            }
        } else {
            // For new entries, just add to array (will be saved with entry)
            this.currentEntryLinks.push({
                target_entry_id: targetEntryId,
                target_term: targetEntry.term,
                link_type: 'see_also'
            });
            this.renderEntryLinks();
            select.value = '';
        }
    }

    async removeLinkFromEntry(linkId) {
        // If editing existing entry, delete from server
        if (this.editingIndex !== -1) {
            const sourceEntryId = this.entries[this.editingIndex].id;
            
            try {
                const response = await fetch(`${this.apiBase}/entries/${sourceEntryId}/links/${linkId}`, {
                    method: 'DELETE'
                });

                if (!response.ok) throw new Error('Failed to remove link');
                
                this.currentEntryLinks = this.currentEntryLinks.filter(l => 
                    (l.link_id || l.target_entry_id) !== linkId
                );
                this.renderEntryLinks();
                
                // Reload data to update links
                await this.loadData();
                this.renderTable();
            } catch (error) {
                console.error('Error removing link:', error);
                alert('Error removing link: ' + error.message);
            }
        } else {
            // For new entries, just remove from array
            this.currentEntryLinks = this.currentEntryLinks.filter(l => l.target_entry_id !== linkId);
            this.renderEntryLinks();
        }
    }

    async syncEntryLinks(entryId) {
        try {
            // For new entries, add all links
            for (const link of this.currentEntryLinks) {
                // Skip if it already has a link_id (already exists on server)
                if (link.link_id) continue;
                
                await fetch(`${this.apiBase}/entries/${entryId}/links`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ 
                        target_entry_id: link.target_entry_id,
                        link_type: link.link_type || 'see_also'
                    })
                });
            }
        } catch (error) {
            console.error('Error syncing links:', error);
        }
    }

    // Report-Specific Definitions Methods
    populateReportDefTagSelect() {
        const select = document.getElementById('report-def-tag-select');
        if (!select) return;
        select.innerHTML = '<option value="">-- Select a report --</option>';
        this.tags.forEach(tag => {
            // Only show tags not yet having a definition
            const hasDefinition = this.currentReportDefinitions.some(d => d.tag_id === tag.id);
            if (!hasDefinition) {
                const option = document.createElement('option');
                option.value = tag.id;
                option.textContent = tag.name;
                select.appendChild(option);
            }
        });
    }

    renderReportDefinitions() {
        const container = document.getElementById('report-definitions-container');
        if (!container) return;
        container.innerHTML = '';

        if (this.currentReportDefinitions.length === 0) {
            container.innerHTML = '<p style="color:#999; font-size:0.9em;">No report-specific definitions yet. The default definition above will be used for all reports.</p>';
            return;
        }

        this.currentReportDefinitions.forEach((def, index) => {
            const div = document.createElement('div');
            div.style.cssText = 'border: 1px solid #ddd; border-radius: 4px; padding: 10px; margin-bottom: 8px; background: #f8f9fa;';
            
            const tag = this.tags.find(t => t.id === def.tag_id);
            const tagColor = tag ? tag.color : '#004C8E';
            const tagName = def.tag_name || (tag ? tag.name : 'Unknown Report');
            
            div.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <span class="tag" style="background-color: ${tagColor}">${this.escapeHtml(tagName)}</span>
                    <button type="button" class="btn btn-delete btn-small" onclick="dictionary.removeReportDefinition(${index})">Remove</button>
                </div>
                <textarea rows="2" style="width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; resize: vertical;"
                    onchange="dictionary.updateReportDefinitionText(${index}, this.value)">${this.escapeHtml(def.definition || '')}</textarea>
            `;
            container.appendChild(div);
        });
    }

    addReportDefinition() {
        const select = document.getElementById('report-def-tag-select');
        const tagId = parseInt(select.value);

        if (!tagId) {
            alert('Please select a report');
            return;
        }

        const tag = this.tags.find(t => t.id === tagId);
        if (!tag) return;

        // Check if already exists
        if (this.currentReportDefinitions.some(d => d.tag_id === tagId)) {
            alert('A definition for this report already exists');
            return;
        }

        this.currentReportDefinitions.push({
            tag_id: tagId,
            tag_name: tag.name,
            tag_color: tag.color,
            definition: '',
            _isNew: true
        });
        this.renderReportDefinitions();
        this.populateReportDefTagSelect();
        select.value = '';
    }

    removeReportDefinition(index) {
        this.currentReportDefinitions.splice(index, 1);
        this.renderReportDefinitions();
        this.populateReportDefTagSelect();
    }

    updateReportDefinitionText(index, text) {
        if (this.currentReportDefinitions[index]) {
            this.currentReportDefinitions[index].definition = text;
        }
    }

    async syncReportDefinitions(entryId) {
        try {
            // Get current definitions from server
            const response = await fetch(`${this.apiBase}/entries/${entryId}/definitions`);
            const serverDefs = response.ok ? await response.json() : [];
            
            const serverTagIds = new Set(serverDefs.map(d => d.tag_id));
            const clientTagIds = new Set(this.currentReportDefinitions.map(d => d.tag_id));

            // Add or update definitions
            for (const def of this.currentReportDefinitions) {
                await fetch(`${this.apiBase}/entries/${entryId}/definitions`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ tag_id: def.tag_id, definition: def.definition })
                });
            }

            // Remove definitions no longer present
            for (const serverDef of serverDefs) {
                if (!clientTagIds.has(serverDef.tag_id)) {
                    await fetch(`${this.apiBase}/entries/${entryId}/definitions/${serverDef.id}`, {
                        method: 'DELETE'
                    });
                }
            }
        } catch (error) {
            console.error('Error syncing report definitions:', error);
        }
    }

    // JSON Backup/Restore Methods
    async downloadJsonBackup() {
        try {
            const response = await fetch(`${this.apiBase}/backup`);
            if (!response.ok) throw new Error('Failed to create backup');
            
            const backup = await response.json();
            const jsonContent = JSON.stringify(backup, null, 2);
            const blob = new Blob([jsonContent], { type: 'application/json;charset=utf-8;' });
            const url = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = `data-dictionary-backup-${new Date().toISOString().split('T')[0]}.json`;
            link.click();
            URL.revokeObjectURL(url);
        } catch (error) {
            console.error('Error creating backup:', error);
            alert('Error creating backup: ' + error.message);
        }
    }

    async handleJsonRestore(event) {
        const file = event.target.files[0];
        if (!file) return;

        try {
            const text = await file.text();
            const backup = JSON.parse(text);

            if (!backup.entries) {
                alert('Invalid backup file: missing entries data');
                event.target.value = '';
                return;
            }

            const confirmed = confirm(
                `This will REPLACE ALL current data with the backup.\n\n` +
                `Backup contains:\n` +
                `• ${backup.entries.length} entries\n` +
                `• ${(backup.tags || []).length} reports/tags\n` +
                `• ${(backup.entry_definitions || []).length} report-specific definitions\n` +
                `• ${(backup.entry_links || []).length} entry links\n` +
                `• ${(backup.change_history || []).length} change history records\n\n` +
                `Do you want to proceed?`
            );

            if (!confirmed) {
                event.target.value = '';
                return;
            }

            const response = await fetch(`${this.apiBase}/restore`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(backup)
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Restore failed');
            }

            const result = await response.json();
            alert(
                `Restore completed!\n\n` +
                `✅ Entries: ${result.entries}\n` +
                `🏷️ Tags: ${result.tags}\n` +
                `📝 Report definitions: ${result.entry_definitions}\n` +
                `🔗 Entry links: ${result.entry_links}\n` +
                `📋 Change history records: ${result.change_history}`
            );

            // Reload everything
            await this.loadData();
            await this.loadTags();
            this.populateTagSelect();
            this.populateReportDefTagSelect();
            this.renderTable();
            event.target.value = '';

        } catch (error) {
            console.error('Error restoring backup:', error);
            alert('Error restoring backup: ' + error.message);
            event.target.value = '';
        }
    }
}

// Initialize the application
const dictionary = new DataDictionary();
