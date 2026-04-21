// Data Dictionary Application
class DataDictionary {
    constructor() {
        this.entries = [];
        this.editingIndex = -1;
        this.isAuthenticated = false;
        this.init();
    }

    init() {
        // Check authentication state
        this.checkAuth();
        
        // Load data from localStorage
        this.loadData();
        
        // Bind event listeners
        this.bindEvents();
        
        // Render initial table
        this.renderTable();
    }

    checkAuth() {
        const authState = localStorage.getItem('isAuthenticated');
        this.isAuthenticated = authState === 'true';
        this.updateUIForAuth();
    }

    updateUIForAuth() {
        const adminElements = document.querySelectorAll('.admin-only');
        const loginBtn = document.getElementById('login-btn');
        const logoutBtn = document.getElementById('logout-btn');
        
        adminElements.forEach(el => {
            el.style.display = this.isAuthenticated ? 'block' : 'none';
        });
        
        loginBtn.style.display = this.isAuthenticated ? 'none' : 'inline-block';
        logoutBtn.style.display = this.isAuthenticated ? 'inline-block' : 'none';
        
        // Re-render table to show/hide action buttons
        this.renderTable();
    }

    bindEvents() {
        const form = document.getElementById('dictionary-form');
        const searchInput = document.getElementById('search-input');
        const filterType = document.getElementById('filter-type');
        const cancelBtn = document.getElementById('cancel-btn');
        const loginBtn = document.getElementById('login-btn');
        const logoutBtn = document.getElementById('logout-btn');
        const loginForm = document.getElementById('login-form');
        const cancelLoginBtn = document.getElementById('cancel-login-btn');
        const downloadExcelBtn = document.getElementById('download-excel-btn');

        form.addEventListener('submit', (e) => {
            e.preventDefault();
            this.handleSubmit();
        });

        searchInput.addEventListener('input', () => this.renderTable());
        filterType.addEventListener('change', () => this.renderTable());
        cancelBtn.addEventListener('click', () => this.cancelEdit());
        
        loginBtn.addEventListener('click', () => this.showLoginModal());
        logoutBtn.addEventListener('click', () => this.logout());
        loginForm.addEventListener('submit', (e) => this.handleLogin(e));
        cancelLoginBtn.addEventListener('click', () => this.hideLoginModal());
        downloadExcelBtn.addEventListener('click', () => this.downloadExcel());
    }

    showLoginModal() {
        document.getElementById('login-modal').style.display = 'flex';
    }

    hideLoginModal() {
        document.getElementById('login-modal').style.display = 'none';
        document.getElementById('login-form').reset();
    }

    handleLogin(e) {
        e.preventDefault();
        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;
        
        // Simple authentication - in production, this should be server-side
        if (username === 'admin' && password === 'admin123') {
            this.isAuthenticated = true;
            localStorage.setItem('isAuthenticated', 'true');
            this.updateUIForAuth();
            this.hideLoginModal();
            alert('Login successful!');
        } else {
            alert('Invalid credentials. Please try again.');
        }
    }

    logout() {
        this.isAuthenticated = false;
        localStorage.removeItem('isAuthenticated');
        this.updateUIForAuth();
        this.cancelEdit();
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
        } else {
            // Update existing entry
            this.entries[this.editingIndex] = formData;
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
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    deleteEntry(index) {
        if (confirm('Are you sure you want to delete this entry?')) {
            this.entries.splice(index, 1);
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
            
            const actionsHtml = this.isAuthenticated ? `
                <td>
                    <div class="actions-cell">
                        <button class="btn btn-edit" onclick="dictionary.editEntry(${actualIndex})">✏️ Edit</button>
                        <button class="btn btn-delete" onclick="dictionary.deleteEntry(${actualIndex})">🗑️ Delete</button>
                    </div>
                </td>
            ` : '';
            
            row.innerHTML = `
                <td><strong>${this.escapeHtml(entry.term)}</strong></td>
                <td>${this.escapeHtml(entry.definition)}</td>
                <td>${entry.abbreviation ? this.escapeHtml(entry.abbreviation) : '<span class="text-muted">—</span>'}</td>
                <td>${entry.dataType ? `<span class="badge">${this.escapeHtml(entry.dataType)}</span>` : '<span class="text-muted">—</span>'}</td>
                <td>${entry.inputFormat ? `<code>${this.escapeHtml(entry.inputFormat)}</code>` : '<span class="text-muted">—</span>'}</td>
                <td>${entry.variations ? this.escapeHtml(entry.variations) : '<span class="text-muted">—</span>'}</td>
                ${actionsHtml}
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
                definition: 'Application Programming Interface - A set of protocols and tools for building software applications',
                abbreviation: 'API',
                dataType: 'Other',
                inputFormat: '',
                variations: 'Application Programming Interface, Web API, REST API',
                createdAt: new Date().toISOString(),
                updatedAt: new Date().toISOString()
            },
            {
                term: 'Customer ID',
                definition: 'Unique identifier assigned to each customer in the system',
                abbreviation: 'CUST_ID',
                dataType: 'String',
                inputFormat: 'CUST-######',
                variations: 'CustID, Customer Identifier, Client ID',
                createdAt: new Date().toISOString(),
                updatedAt: new Date().toISOString()
            },
            {
                term: 'Transaction Date',
                definition: 'The date and time when a transaction was processed',
                abbreviation: 'TXN_DATE',
                dataType: 'DateTime',
                inputFormat: 'YYYY-MM-DD HH:MM:SS',
                variations: 'Transaction DateTime, TXN Date, Processing Date',
                createdAt: new Date().toISOString(),
                updatedAt: new Date().toISOString()
            },
            {
                term: 'Email Address',
                definition: 'Electronic mail address for communication with users',
                abbreviation: '',
                dataType: 'String',
                inputFormat: 'user@domain.com',
                variations: 'Email, E-mail, Electronic Mail',
                createdAt: new Date().toISOString(),
                updatedAt: new Date().toISOString()
            },
            {
                term: 'Active Status',
                definition: 'Boolean flag indicating whether an account or record is currently active',
                abbreviation: '',
                dataType: 'Boolean',
                inputFormat: 'true/false or 1/0',
                variations: 'IsActive, Status, Account Status',
                createdAt: new Date().toISOString(),
                updatedAt: new Date().toISOString()
            }
        ];
        this.saveData();
    }

    exportData() {
        const dataStr = JSON.stringify(this.entries, null, 2);
        const dataBlob = new Blob([dataStr], { type: 'application/json' });
        const url = URL.createObjectURL(dataBlob);
        const link = document.createElement('a');
        link.href = url;
        link.download = 'data-dictionary-export.json';
        link.click();
        URL.revokeObjectURL(url);
    }

    importData(file) {
        const reader = new FileReader();
        reader.onload = (e) => {
            try {
                const imported = JSON.parse(e.target.result);
                if (Array.isArray(imported)) {
                    this.entries = imported;
                    this.saveData();
                    this.renderTable();
                    alert('Data imported successfully!');
                } else {
                    alert('Invalid data format');
                }
            } catch (error) {
                alert('Error importing data: ' + error.message);
            }
        };
        reader.readAsText(file);
    }

    downloadExcel() {
        if (!this.isAuthenticated) {
            alert('You must be logged in to download data.');
            return;
        }

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
}

// Initialize the application
const dictionary = new DataDictionary();
