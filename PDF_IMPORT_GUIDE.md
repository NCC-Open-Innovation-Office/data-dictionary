# PDF Import Guide

This is a one-off script to import terms from a PDF spreadsheet into the data dictionary.

## Column Mapping

The script maps PDF columns to database fields as follows:

- **"Plain English Entry"** → `term`
- **"Definition"** → `definition`
- **"Criteria"** → `variations`
- **"Usage Notes"** → `discussion` (backend notes)
- **"And Potential Values"** → `inputFormat`

## Usage

1. **Install the required library:**
   ```bash
   pip install -r import-requirements.txt
   ```

2. **Run the import script:**
   ```bash
   python import_pdf_data.py path/to/your/spreadsheet.pdf
   ```

3. **Review the output** - the script will:
   - Extract all tables from the PDF
   - Show you what columns it found
   - Display how many entries it parsed
   - Ask for confirmation before importing
   - Skip any terms that already exist in the database

## Example

```bash
# Install dependencies
pip install pdfplumber

# Import your PDF
python import_pdf_data.py ~/Downloads/data-dictionary-terms.pdf
```

## What the script does

1. Opens the PDF and extracts all tables
2. Identifies columns by matching header names (case-insensitive)
3. Parses each row and maps data to the correct fields
4. Shows a preview of what will be imported
5. Asks for confirmation
6. Imports entries into the SQLite database (skips duplicates)

## Notes

- The script will **not** overwrite existing entries
- Empty rows are automatically skipped
- Only entries with a valid "term" are imported
- The script is flexible with column names (case-insensitive matching)
