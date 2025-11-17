// Data Dictionary Application - Public View with API
class DataDictionary {
    constructor() {
        this.entries = [];
        this.tags = [];
        // API URL configuration for both local and Docker environments
        const isLocalDev = window.location.port === '8000' && window.location.hostname === 'localhost';
        this.apiBase = isLocalDev ? 'http://localhost:5001/api' : '/api';
        this.init();
    }

    async init() {
        // Load data from API
        await this.loadData();
        await this.loadTags();
        
        // Bind event listeners
        this.bindEvents();
        
        // Render initial table
        this.renderTable();
        this.populateTagFilter();
    }

    bindEvents() {
        const searchInput = document.getElementById('search-input');
        const filterType = document.getElementById('filter-type');
        const filterTag = document.getElementById('filter-tag');

        searchInput.addEventListener('input', () => this.renderTable());
        filterType.addEventListener('change', () => this.renderTable());
        filterTag.addEventListener('change', () => this.renderTable());
    }

    filterEntries() {
        const searchTerm = document.getElementById('search-input').value.toLowerCase();
        const filterType = document.getElementById('filter-type').value;
        const filterTag = document.getElementById('filter-tag').value;

        return this.entries.filter(entry => {
            // Search filter
            const matchesSearch = !searchTerm || 
                entry.term.toLowerCase().includes(searchTerm) ||
                entry.definition.toLowerCase().includes(searchTerm) ||
                (entry.abbreviation && entry.abbreviation.toLowerCase().includes(searchTerm)) ||
                (entry.variations && entry.variations.toLowerCase().includes(searchTerm));

            // Type filter
            const matchesType = !filterType || entry.dataType === filterType;
            
            // Tag filter
            const matchesTag = !filterTag || (entry.tags && entry.tags.some(tag => tag.id === parseInt(filterTag)));

            return matchesSearch && matchesType && matchesTag;
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

    populateTagFilter() {
        const select = document.getElementById('filter-tag');
        select.innerHTML = '<option value="">All Reports</option>';
        this.tags.forEach(tag => {
            const option = document.createElement('option');
            option.value = tag.id;
            option.textContent = tag.name;
            select.appendChild(option);
        });
    }
}

// Initialize the application
const dictionary = new DataDictionary();
