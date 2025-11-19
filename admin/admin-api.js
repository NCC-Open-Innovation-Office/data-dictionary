// Data Dictionary Application - Admin Interface with API
class DataDictionary {
    constructor() {
        this.entries = [];
        this.editingIndex = -1;
        this.changeHistory = [];
        this.tags = [];
        this.currentEntryTags = [];
        this.currentEntryLinks = [];
        // API URL configuration for both local and Docker environments
        const isLocalDev = window.location.port === '8000' && window.location.hostname === 'localhost';
        this.apiBase = isLocalDev ? 'http://localhost:5001/api' : '/api';
        this.init();
    }

    async init() {
        // Load data from API
        await this.loadData();
        await this.loadChangeHistory();
        await this.loadTags();
        await this.loadOwners();
        await this.loadStewards();
        
        // Bind event listeners
        this.bindEvents();
        
        // Render initial table
        this.renderTable();
        this.populateTagSelect();
        this.populateLinkSelect();
    }

    bindEvents() {
        const form = document.getElementById('dictionary-form');
        const searchInput = document.getElementById('search-input');
        const filterType = document.getElementById('filter-type');
        const cancelBtn = document.getElementById('cancel-btn');
        const downloadExcelBtn = document.getElementById('download-excel-btn');
        const historyBtn = document.getElementById('view-history-btn');
        const closeHistoryBtn = document.getElementById('close-history-btn');
        const closeDetailBtn = document.getElementById('close-detail-btn');
        const addTagBtn = document.getElementById('add-tag-btn');
        const manageTagsBtn = document.getElementById('manage-tags-btn');
        const closeTagModalBtn = document.getElementById('close-tag-modal-btn');
        const createTagBtn = document.getElementById('create-tag-btn');
        const addLinkBtn = document.getElementById('add-link-btn');

        form.addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleSubmit();
        });

        searchInput.addEventListener('input', () => this.renderTable());
        filterType.addEventListener('change', () => this.renderTable());
        cancelBtn.addEventListener('click', () => this.cancelEdit());
        downloadExcelBtn.addEventListener('click', () => this.downloadExcel());
        historyBtn.addEventListener('click', () => this.showHistory());
        closeHistoryBtn.addEventListener('click', () => this.hideHistory());
        closeDetailBtn.addEventListener('click', () => this.hideDetail());
        addTagBtn.addEventListener('click', () => this.addTagToEntry());
        manageTagsBtn.addEventListener('click', () => this.showTagManagement());
        closeTagModalBtn.addEventListener('click', () => this.hideTagManagement());
        createTagBtn.addEventListener('click', () => this.createTag());
        addLinkBtn.addEventListener('click', () => this.addLinkToEntry());
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
        
        // Load tags
        this.currentEntryTags = entry.tags || [];
        this.renderEntryTags();

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
        this.renderEntryTags();
        this.renderEntryLinks();
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
        this.renderEntryTags();
        this.renderEntryLinks();
        this.populateLinkSelect(); // Refresh the link dropdown
    }

    filterEntries() {
        const searchTerm = document.getElementById('search-input').value.toLowerCase();
        const filterType = document.getElementById('filter-type').value;

        return this.entries.filter(entry => {
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

    downloadExcel() {
        // Create CSV data (Excel can open CSV files)
        const headers = ['Term', 'Definition', 'Abbreviation', 'Data Type', 'Input Format', 'Variations', 'Created At', 'Updated At'];
        const csvRows = [headers.join(',')];

        this.entries.forEach(entry => {
            const row = [
                this.escapeCsv(entry.term),
                this.escapeCsv(entry.definition),
                this.escapeCsv(entry.abbreviation || ''),
                this.escapeCsv(entry.dataType || ''),
                this.escapeCsv(entry.inputFormat || ''),
                this.escapeCsv(entry.variations || ''),
                this.escapeCsv(entry.createdAt ? new Date(entry.createdAt).toLocaleString() : ''),
                this.escapeCsv(entry.updatedAt ? new Date(entry.updatedAt).toLocaleString() : '')
            ];
            csvRows.push(row.join(','));
        });

        const csvContent = csvRows.join('\n');
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `data-dictionary-${new Date().toISOString().split('T')[0]}.csv`;
        link.click();
        URL.revokeObjectURL(url);
    }

    escapeCsv(text) {
        if (text === null || text === undefined) return '';
        const str = String(text);
        if (str.includes(',') || str.includes('"') || str.includes('\n')) {
            return `"${str.replace(/"/g, '""')}"`;
        }
        return str;
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
        
        if (!tagId) {
            alert('Please select a tag');
            return;
        }

        const tag = this.tags.find(t => t.id === tagId);
        if (!tag) return;

        // Check if tag already added
        if (this.currentEntryTags.find(t => t.id === tagId)) {
            alert('Report already added');
            return;
        }

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
}

// Initialize the application
const dictionary = new DataDictionary();
