// Data Dictionary Application - Public View (Read-Only)
class DataDictionary {
    constructor() {
        this.entries = [];
        this.init();
    }

    init() {
        // Load data from localStorage
        this.loadData();
        
        // Bind event listeners
        this.bindEvents();
        
        // Render initial table
        this.renderTable();
    }

    bindEvents() {
        const searchInput = document.getElementById('search-input');

        searchInput.addEventListener('input', () => this.renderTable());
    }

    filterEntries() {
        const searchTerm = document.getElementById('search-input').value.toLowerCase();

        return this.entries.filter(entry => {
            // Search filter
            const matchesSearch = !searchTerm || 
                entry.term.toLowerCase().includes(searchTerm) ||
                entry.definition.toLowerCase().includes(searchTerm) ||
                (entry.abbreviation && entry.abbreviation.toLowerCase().includes(searchTerm)) ||
                (entry.variations && entry.variations.toLowerCase().includes(searchTerm));

            return matchesSearch;
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

        filteredEntries.forEach((entry) => {
            const row = document.createElement('tr');
            
            row.innerHTML = `
                <td><strong>${this.escapeHtml(entry.term)}</strong></td>
                <td>${this.escapeHtml(entry.definition)}</td>
                <td>${entry.abbreviation ? this.escapeHtml(entry.abbreviation) : '<span class="text-muted">—</span>'}</td>
                <td>${entry.inputFormat ? `<code>${this.escapeHtml(entry.inputFormat)}</code>` : '<span class="text-muted">—</span>'}</td>
                <td>${entry.variations ? this.escapeHtml(entry.variations) : '<span class="text-muted">—</span>'}</td>
            `;

            tbody.appendChild(row);
        });
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
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
        // Don't save in public view - data is read-only
    }
}

// Initialize the application
const dictionary = new DataDictionary();
