# Data Dictionary Platform

A comprehensive web-based data dictionary platform for organizations to document and manage their data standards, terminology, and definitions.

## 📋 Features

- **Term Management**: Add, edit, and delete dictionary entries
- **Rich Metadata**: Track terms, definitions, abbreviations, data types, input formats, and variations
- **Search & Filter**: Quickly find entries using search and type filtering
- **Persistent Storage**: Data is saved locally in your browser using localStorage
- **Sample Data**: Pre-loaded with example entries to demonstrate functionality
- **Responsive Design**: Works seamlessly on desktop and mobile devices
- **Export/Import**: (Future feature) Export and import dictionary data as JSON

## 🚀 Getting Started

### Installation

No installation required! This is a client-side web application that runs entirely in your browser.

### Usage

1. **Open the application**: Simply open `index.html` in any modern web browser
2. **View existing entries**: The dictionary table shows all current entries
3. **Add new entry**: Fill out the form at the top and click "Add Entry"
4. **Edit entry**: Click the "✏️ Edit" button on any entry
5. **Delete entry**: Click the "🗑️ Delete" button on any entry
6. **Search**: Use the search bar to filter entries by term, definition, or abbreviation
7. **Filter by type**: Use the dropdown to filter entries by data type

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