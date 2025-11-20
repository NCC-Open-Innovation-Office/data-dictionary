#!/usr/bin/env python3
"""
Fix field mapping in the database where data ended up in wrong columns
from the PDF import.

Issue: The PDF import put:
- Definition data → variations field
- Variations data → inputFormat field  
- "Potential Values" data → inputFormat field (correct)

This script will remap the fields correctly.
"""

import sqlite3
import sys
from datetime import datetime

DATABASE = 'data/dictionary.db'

def fix_field_mapping():
    """Fix the incorrectly mapped fields from PDF import"""
    
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Get all entries with empty definitions but data in variations
    cursor.execute('''
        SELECT id, term, definition, variations, inputFormat, discussion
        FROM entries 
        WHERE (definition IS NULL OR definition = '')
        AND (variations IS NOT NULL AND variations != '')
    ''')
    
    entries_to_fix = cursor.fetchall()
    
    if not entries_to_fix:
        print("No entries found that need fixing.")
        conn.close()
        return
    
    print(f"Found {len(entries_to_fix)} entries with empty definitions but data in variations")
    print("\nSample entries that will be fixed:")
    for entry in entries_to_fix[:3]:
        print(f"\n  Term: {entry[1]}")
        print(f"    Current definition: '{entry[2]}'")
        print(f"    Current variations: '{entry[3][:80]}...'")
    
    response = input(f"\nFix {len(entries_to_fix)} entries? (y/n): ")
    if response.lower() != 'y':
        print("Cancelled")
        conn.close()
        return
    
    now = datetime.utcnow().isoformat()
    fixed = 0
    
    for entry_id, term, definition, variations, inputFormat, discussion in entries_to_fix:
        try:
            # For entries from the PDF import:
            # - variations actually contains the definition/criteria
            # - Keep inputFormat as is (it's correct)
            # - Keep discussion as is (backend notes)
            
            # The "variations" field should actually be the definition
            new_definition = variations
            
            # Clear variations since we don't have real variation data
            new_variations = ''
            
            cursor.execute('''
                UPDATE entries
                SET definition = ?,
                    variations = ?,
                    updatedAt = ?
                WHERE id = ?
            ''', (new_definition, new_variations, now, entry_id))
            
            fixed += 1
            
        except Exception as e:
            print(f"Error fixing '{term}': {e}")
    
    conn.commit()
    conn.close()
    
    print(f"\n✅ Fixed {fixed} entries")
    print("You can now export and import the data correctly!")

if __name__ == '__main__':
    print("=" * 60)
    print("Data Dictionary Field Mapping Fix")
    print("=" * 60)
    print("\nThis will:")
    print("  1. Find entries with empty 'definition' but data in 'variations'")
    print("  2. Move data from 'variations' to 'definition'")
    print("  3. Clear the 'variations' field")
    print()
    
    fix_field_mapping()
