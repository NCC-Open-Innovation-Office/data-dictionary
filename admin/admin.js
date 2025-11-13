// Data Dictionary Application - Admin Interface
class DataDictionary {
    constructor() {
        this.entries = [];
        this.editingIndex = -1;
        this.changeHistory = [];
        this.init();
    }

    init() {
        // Load data from localStorage
        this.loadData();
        this.loadChangeHistory();
        
        // Bind event listeners
        this.bindEvents();
        
        // Render initial table
        this.renderTable();
    }

    bindEvents() {
        const form = document.getElementById('dictionary-form');
        const searchInput = document.getElementById('search-input');
        const filterType = document.getElementById('filter-type');
        const cancelBtn = document.getElementById('cancel-btn');
        const downloadExcelBtn = document.getElementById('download-excel-btn');
        const historyBtn = document.getElementById('view-history-btn');
        const closeHistoryBtn = document.getElementById('close-history-btn');

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
    }

    logChange(action, entryTerm, oldData, newData) {
        const change = {
            timestamp: new Date().toISOString(),
            action: action, // 'create', 'update', 'delete'
            term: entryTerm,
            oldData: oldData,
            newData: newData,
            user: 'Admin' // Will be replaced with actual user when Cloudflare Access is set up
        };
        
        this.changeHistory.unshift(change); // Add to beginning
        this.saveChangeHistory();
    }

    handleSubmit() {
        const formData = {
            term: document.getElementById('term').value.trim(),
            definition: document.getElementById('definition').value.trim(),
            abbreviation: document.getElementById('abbreviation').value.trim(),
            dataType: document.getElementById('dataType').value,
            inputFormat: document.getElementById('inputFormat').value.trim(),
            variations: document.getElementById('variations').value.trim(),
            createdAt: this.editingIndex === -1 ? new Date().toISOString() : this.entries[this.editingIndex].createdAt,
            updatedAt: new Date().toISOString()
        };

        if (this.editingIndex === -1) {
            // Add new entry
            this.entries.push(formData);
            this.logChange('create', formData.term, null, formData);
        } else {
            // Update existing entry
            const oldData = {...this.entries[this.editingIndex]};
            this.entries[this.editingIndex] = formData;
            this.logChange('update', formData.term, oldData, formData);
            this.editingIndex = -1;
            document.getElementById('form-title').textContent = 'Add New Entry';
            document.getElementById('submit-btn').textContent = 'Add Entry';
            document.getElementById('cancel-btn').style.display = 'none';
        }

        this.saveData();
        this.renderTable();
        this.resetForm();
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

        // Update UI
        document.getElementById('form-title').textContent = 'Edit Entry';
        document.getElementById('submit-btn').textContent = 'Update Entry';
        document.getElementById('cancel-btn').style.display = 'inline-block';

        // Scroll to form
        document.querySelector('.form-section').scrollIntoView({ behavior: 'smooth' });
    }

    deleteEntry(index) {
        if (confirm('Are you sure you want to delete this entry?')) {
            const deletedEntry = {...this.entries[index]};
            this.entries.splice(index, 1);
            this.logChange('delete', deletedEntry.term, deletedEntry, null);
            this.saveData();
            this.renderTable();
        }
    }

    cancelEdit() {
        this.editingIndex = -1;
        this.resetForm();
        document.getElementById('form-title').textContent = 'Add New Entry';
        document.getElementById('submit-btn').textContent = 'Add Entry';
        document.getElementById('cancel-btn').style.display = 'none';
    }

    resetForm() {
        document.getElementById('dictionary-form').reset();
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
            
            row.innerHTML = `
                <td><strong>${this.escapeHtml(entry.term)}</strong></td>
                <td>${this.escapeHtml(entry.definition)}</td>
                <td>${entry.abbreviation ? this.escapeHtml(entry.abbreviation) : '<span class="text-muted">—</span>'}</td>
                <td>${entry.dataType ? `<span class="badge">${this.escapeHtml(entry.dataType)}</span>` : '<span class="text-muted">—</span>'}</td>
                <td>${entry.inputFormat ? `<code>${this.escapeHtml(entry.inputFormat)}</code>` : '<span class="text-muted">—</span>'}</td>
                <td>${entry.variations ? this.escapeHtml(entry.variations) : '<span class="text-muted">—</span>'}</td>
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

    saveData() {
        localStorage.setItem('dataDictionary', JSON.stringify(this.entries));
    }

    loadData() {
        const saved = localStorage.getItem('dataDictionary');
        if (saved) {
            try {
                this.entries = JSON.parse(saved);
            } catch (e) {
                console.error('Error loading data:', e);
                this.entries = [];
            }
        } else {
            // Load sample data if no data exists
            this.loadSampleData();
        }
    }

    loadSampleData() {
        this.entries = [
            {
                term: 'API',
                definition: 'Application Programming Interface - a set of protocols and tools for building software applications',
                abbreviation: 'API',
                dataType: 'String',
                inputFormat: '',
                variations: 'Application Programming Interface, Web API, REST API',
                createdAt: new Date().toISOString(),
                updatedAt: new Date().toISOString()
            },
            {
                term: 'Customer ID',
                definition: 'Unique identifier assigned to each customer in the system',
                abbreviation: 'CID',
                dataType: 'Integer',
                inputFormat: '######',
                variations: 'Customer Identifier, CustID, Client ID',
                createdAt: new Date().toISOString(),
                updatedAt: new Date().toISOString()
            }
        ];
        this.saveData();
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
        // Escape double quotes and wrap in quotes if contains comma, quote, or newline
        if (str.includes(',') || str.includes('"') || str.includes('\n')) {
            return `"${str.replace(/"/g, '""')}"`;
        }
        return str;
    }

    saveChangeHistory() {
        localStorage.setItem('dictionaryChangeHistory', JSON.stringify(this.changeHistory));
    }

    loadChangeHistory() {
        const saved = localStorage.getItem('dictionaryChangeHistory');
        if (saved) {
            try {
                this.changeHistory = JSON.parse(saved);
            } catch (e) {
                console.error('Error loading change history:', e);
                this.changeHistory = [];
            }
        }
    }

    showHistory() {
        const modal = document.getElementById('history-modal');
        modal.style.display = 'flex';
        this.renderHistory();
    }

    hideHistory() {
        document.getElementById('history-modal').style.display = 'none';
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
                    if (key !== 'updatedAt' && key !== 'createdAt' && change.oldData[key] !== change.newData[key]) {
                        changedFields.push(key);
                    }
                }
                changes = changedFields.length > 0 ? `Modified: ${changedFields.join(', ')}` : 'No changes detected';
            }

            row.innerHTML = `
                <td>${timestamp}</td>
                <td>${actionBadge}</td>
                <td><strong>${this.escapeHtml(change.term)}</strong></td>
                <td>${changes}</td>
                <td>${this.escapeHtml(change.user)}</td>
                <td><button class="btn btn-small" onclick="dictionary.viewChangeDetail(${index})">View Details</button></td>
            `;
            tbody.appendChild(row);
        });
    }

    viewChangeDetail(index) {
        const change = this.changeHistory[index];
        let detail = `Change Details\n\n`;
        detail += `Timestamp: ${new Date(change.timestamp).toLocaleString()}\n`;
        detail += `Action: ${change.action.toUpperCase()}\n`;
        detail += `Term: ${change.term}\n`;
        detail += `User: ${change.user}\n\n`;

        if (change.action === 'create' && change.newData) {
            detail += `New Data:\n`;
            detail += JSON.stringify(change.newData, null, 2);
        } else if (change.action === 'delete' && change.oldData) {
            detail += `Deleted Data:\n`;
            detail += JSON.stringify(change.oldData, null, 2);
        } else if (change.action === 'update') {
            detail += `Changes:\n`;
            for (let key in change.newData) {
                if (key !== 'updatedAt' && key !== 'createdAt' && change.oldData[key] !== change.newData[key]) {
                    detail += `\n${key}:\n`;
                    detail += `  Old: ${change.oldData[key] || '(empty)'}\n`;
                    detail += `  New: ${change.newData[key] || '(empty)'}\n`;
                }
            }
        }

        alert(detail);
    }
}

// Initialize the application
const dictionary = new DataDictionary();
