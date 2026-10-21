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

import pdfplumber
import sys
import os

from api.db import Database
from api.models import Entry

# Absolute path so the target database does not depend on the working
# directory the script happens to be launched from.
project_root = os.path.dirname(os.path.abspath(__file__))
os.environ.setdefault(
    'DATABASE',
    os.path.join(project_root, 'data', 'dictionary.db'),
)
database = Database()


def utcnow_iso():
    from datetime import datetime

    return datetime.utcnow().isoformat()

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
    
    for table in tables:
        if not table or len(table) < 2:
            continue
            
        headers = [str(h).strip() if h else '' for h in table[0]]
        header_map = {}
        for index, header in enumerate(headers):
            header_map[header.lower()] = index
        
        for row in table[1:]:
            if not row:
                continue
            
            def get_value(*names):
                for name in names:
                    if name in header_map:
                        index = header_map[name]
                        if index < len(row) and row[index]:
                            return str(row[index]).strip()
                return ''
            
            entry = {
                'term': get_value('plain english entry', 'term', 'entry'),
                'definition': get_value('definition', 'criteria', 'description'),
                'abbreviation': get_value('abbreviation', 'abbrev', 'abbr'),
                'dataType': get_value('data type', 'datatype', 'type'),
                'inputFormat': get_value(
                    'potential values', 'input format', 'values'
                ),
                'variations': get_value('variations', 'variation'),
            }
            
            if entry['term']:
                entries.append(entry)
    
    return entries

def create_entries(entries):
    """Create entries in the database"""
    created = 0
    skipped = 0
    
    with database.session_scope() as session:
        for item in entries:
            existing = session.query(Entry).filter(
                Entry.term == item['term']
            ).first()
            
            if existing:
                skipped += 1
                continue
            
            entry = Entry(
                term=item['term'],
                definition=item['definition'],
                abbreviation=item['abbreviation'],
                dataType=item['dataType'],
                inputFormat=item['inputFormat'],
                variations=item['variations'],
                classification='public',
                createdAt=utcnow_iso(),
                updatedAt=utcnow_iso(),
            )
            session.add(entry)
            created += 1
    
    print(f"\nCreated {created} entries, skipped {skipped} duplicates")
    return created

def main():
    if len(sys.argv) < 2:
        print("Usage: python import_pdf_data.py <path-to-pdf>")
        print("\nExample: python import_pdf_data.py ~/Downloads/terms.pdf")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    if not os.path.exists(pdf_path):
        print(f"Error: File not found: {pdf_path}")
        sys.exit(1)
    
    print("=" * 60)
    print("Importing PDF Data Dictionary")
    print("=" * 60)
    print()
    
    tables = extract_tables_from_pdf(pdf_path)
    print(f"\nExtracted {len(tables)} tables")
    
    entries = parse_table_data(tables)
    print(f"Parsed {len(entries)} entries")
    
    if not entries:
        print("No entries found. Check the PDF format.")
        sys.exit(1)
    
    print("\nFirst 3 entries:")
    for entry in entries[:3]:
        print(f"  - {entry['term']}")
    
    create_entries(entries)
    
    print("\nDone!")

if __name__ == '__main__':
    main()
