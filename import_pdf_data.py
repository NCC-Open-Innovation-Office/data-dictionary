#!/usr/bin/env python3
"""
One-off script to import terms from a PDF spreadsheet into the data dictionary.

Column mapping:
- "Plain English Entry" -> term
- "Definition" -> definition
- "Criteria" -> variations
- "Usage Notes" -> discussion (backend notes)
- "Potential Values" -> inputFormat
"""

import sqlite3
import pdfplumber
from datetime import datetime
import sys
import os

# Use the correct database path
DATABASE = os.environ.get('DATABASE', 'data/dictionary.db')

def extract_tables_from_pdf(pdf_path):
    """Extract tables from PDF using pdfplumber"""
    tables = []
    
    print(f"Opening PDF: {pdf_path}")
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, 1):
            print(f"Processing page {page_num}...")
            page_tables = page.extract_tables()
            if page_tables:
                tables.extend(page_tables)
                print(f"  Found {len(page_tables)} table(s) on page {page_num}")
    
    return tables

def parse_table_data(tables):
    """Parse the tables and map columns to database fields"""
    entries = []
    
    # Expected column names (case-insensitive matching)
    column_mapping = {
        'plain english entry': 'term',
        'definition': 'definition',
        'criteria': 'variations',
        'usage notes': 'discussion',
        'potential values': 'inputFormat',
        'and potential values': 'inputFormat',  # Handle variation
    }
    
    for table_idx, table in enumerate(tables):
        if not table or len(table) < 2:  # Need at least header + 1 row
            continue
        
        print(f"\nProcessing table {table_idx + 1}...")
        
        # First row is header
        headers = [str(h).strip().lower() if h else '' for h in table[0]]
        print(f"Headers found: {headers}")
        
        # Map header indices to our fields
        field_indices = {}
        for idx, header in enumerate(headers):
            for key, field in column_mapping.items():
                if key in header:
                    field_indices[field] = idx
                    break
        
        print(f"Mapped fields: {list(field_indices.keys())}")
        
        # Process data rows
        for row_idx, row in enumerate(table[1:], 1):
            # Skip empty rows
            if not any(cell for cell in row if cell):
                continue
            
            entry = {}
            for field, col_idx in field_indices.items():
                value = row[col_idx] if col_idx < len(row) else ''
                entry[field] = str(value).strip() if value else ''
            
            # Must have at least a term
            if entry.get('term'):
                entries.append(entry)
                print(f"  Row {row_idx}: Added term '{entry['term'][:50]}...'")
            else:
                print(f"  Row {row_idx}: Skipped (no term)")
    
    return entries

def import_to_database(entries):
    """Import parsed entries into the SQLite database"""
    if not entries:
        print("No entries to import!")
        return
    
    print(f"\n{'='*60}")
    print(f"Importing {len(entries)} entries into database...")
    print(f"{'='*60}\n")
    
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    now = datetime.utcnow().isoformat()
    imported = 0
    skipped = 0
    
    for entry in entries:
        term = entry.get('term', '')
        
        if not term:
            skipped += 1
            continue
        
        # Check if term already exists
        cursor.execute('SELECT id FROM entries WHERE term = ?', (term,))
        existing = cursor.fetchone()
        
        if existing:
            print(f"⚠️  Skipping '{term}' - already exists")
            skipped += 1
            continue
        
        # Insert new entry
        cursor.execute('''
            INSERT INTO entries (
                term, definition, variations, discussion, inputFormat,
                abbreviation, dataType, owner, stewards, classification,
                createdAt, updatedAt
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            entry.get('term', ''),
            entry.get('definition', ''),
            entry.get('variations', ''),
            entry.get('discussion', ''),
            entry.get('inputFormat', ''),
            '',  # abbreviation
            '',  # dataType
            '',  # owner
            '',  # stewards
            'public',  # classification
            now,
            now
        ))
        
        print(f"✓ Imported: {term}")
        imported += 1
    
    conn.commit()
    conn.close()
    
    print(f"\n{'='*60}")
    print(f"Import complete!")
    print(f"  Imported: {imported}")
    print(f"  Skipped:  {skipped}")
    print(f"{'='*60}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python import_pdf_data.py <path-to-pdf>")
        print("\nThis script will:")
        print("  1. Extract tables from the PDF")
        print("  2. Map columns: Plain English Entry -> Term, Definition -> Definition")
        print("     Criteria -> Variations, Usage Notes -> Discussion (backend notes)")
        print("     Potential Values -> Input Format")
        print("  3. Import the data into dictionary.db")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    if not os.path.exists(pdf_path):
        print(f"Error: PDF file not found: {pdf_path}")
        sys.exit(1)
    
    print("=" * 60)
    print("Data Dictionary PDF Import Tool")
    print("=" * 60)
    
    # Extract tables from PDF
    tables = extract_tables_from_pdf(pdf_path)
    
    if not tables:
        print("No tables found in PDF!")
        sys.exit(1)
    
    print(f"\nExtracted {len(tables)} table(s) from PDF")
    
    # Parse the data
    entries = parse_table_data(tables)
    
    if not entries:
        print("\nNo valid entries found!")
        sys.exit(1)
    
    print(f"\nParsed {len(entries)} entries")
    
    # Ask for confirmation
    response = input("\nProceed with import? (y/n): ")
    if response.lower() != 'y':
        print("Import cancelled")
        sys.exit(0)
    
    # Import to database
    import_to_database(entries)

if __name__ == '__main__':
    main()
