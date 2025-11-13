# Data Dictionary Platform

A comprehensive web-based data dictionary platform for organizations to document and manage their data standards, terminology, and definitions.

## 📋 Features

- **Term Management**: Add, edit, and delete dictionary entries with full CRUD operations
- **Rich Metadata**: Track terms, definitions, abbreviations, data types, input formats, and variations
- **Tag System**: Create custom tags with colors to organize and categorize entries
- **Change Tracking**: Complete audit trail with before/after comparisons and discussion notes
- **Search & Filter**: Advanced filtering by text search, data type, and tags
- **Public/Admin Split**: Separate read-only public view and full-featured admin interface
- **API Backend**: RESTful Flask API with SQLite database for persistent storage
- **Responsive Design**: Works seamlessly on desktop and mobile devices
- **Excel Export**: Download dictionary data as CSV for use in Excel

## 🚀 Getting Started

### Quick Start with Docker (Recommended)

1. **Prerequisites**: Install [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/install/)

2. **Run the application**:
   ```bash
   ./start.sh
   ```

3. **Access the application**:
   - Public view: http://localhost:8000
   - Admin view: http://localhost:8000/admin/
   - API: http://localhost:5001/api

4. **Stop the application**:
   ```bash
   docker-compose down
   ```

### Manual Installation

#### Backend (API)
```bash
cd api
pip install -r requirements.txt
python app.py
```

#### Frontend
```bash
python -m http.server 8000
```

## 🐳 Docker Deployment

See [DOCKER.md](DOCKER.md) for detailed Docker deployment instructions.

### Usage

1. **View entries**: Browse the public dictionary at http://localhost:8000
2. **Add/Edit entries**: Access admin interface at http://localhost:8000/admin/
3. **Create tags**: Click "Manage Tags" in admin to create colored tags
4. **Add discussion**: Use the discussion field to document why definitions were chosen
5. **View history**: Click "View Change History" to see all changes with details
6. **Filter by tags**: Use tag dropdown in public view to filter entries
7. **Export data**: Click "Download Excel" to export as CSV

## 📊 Data Fields

Each dictionary entry includes the following fields:

- **Term** (required): The name of the data element or concept
- **Definition** (required): A clear, concise explanation of the term
- **Abbreviation**: Common shortened form or acronym
- **Data Type**: Technical data type (String, Number, Boolean, Date, etc.)
- **Input Format**: Expected format for data entry (e.g., YYYY-MM-DD)
- **Variations**: Alternative names, spellings, or related terms

## 🛠️ Technology Stack

- **HTML5**: Structure and semantic markup
- **CSS3**: Modern styling with gradients, flexbox, and grid
- **Vanilla JavaScript**: Client-side functionality with no dependencies
- **localStorage**: Browser-based data persistence

## 📁 File Structure

```
data-dictionary/
├── index.html      # Main HTML structure
├── styles.css      # Styling and layout
├── app.js          # Application logic and data management
├── README.md       # Documentation
└── LICENSE         # GPL-3.0 License
```

## 💡 Use Cases

Perfect for:
- Data governance teams documenting organizational data standards
- Development teams maintaining technical glossaries
- Business analysts creating shared terminology
- Compliance teams tracking regulated data elements
- Data stewards managing data catalogs

## 🔒 Data Privacy

All data is stored locally in your browser's localStorage. No data is sent to any external servers. Your dictionary entries remain private and under your control.

## 🤝 Contributing

Contributions are welcome! Feel free to submit issues or pull requests to improve the platform.

## 📄 License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

For questions, issues, or feature requests, please open an issue on the GitHub repository.

---

**Note**: This is a client-side application. All data is stored in your browser's localStorage. To preserve your data when clearing browser data, consider implementing export/import functionality.