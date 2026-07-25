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

import sys

from api.db import Database
from api.models import Entry


database = Database()


def utcnow_iso():
    from datetime import datetime

    return datetime.utcnow().isoformat()

def fix_field_mapping():
    """Fix the incorrectly mapped fields from PDF import"""

    with database.session_scope() as session:
        entries_to_fix = (
            session.query(Entry)
            .filter((Entry.definition.is_(None)) | (Entry.definition == ''))
            .filter(Entry.variations.isnot(None), Entry.variations != '')
            .all()
        )

        if not entries_to_fix:
            print("No entries found that need fixing.")
            return

        print(
            f"Found {len(entries_to_fix)} entries with empty definitions but data in variations"
        )
        print("\nSample entries that will be fixed:")
        for entry in entries_to_fix[:3]:
            print(f"\n  Term: {entry.term}")
            print(f"    Current definition: '{entry.definition}'")
            print(f"    Current variations: '{entry.variations[:80]}...'")

        response = input(f"\nFix {len(entries_to_fix)} entries? (y/n): ")
        if response.lower() != 'y':
            print("Cancelled")
            return

        now = utcnow_iso()
        fixed = 0

        for entry in entries_to_fix:
            try:
                entry.definition = entry.variations
                entry.variations = ''
                entry.updatedAt = now
                fixed += 1
            except Exception as exc:
                print(f"Error fixing '{entry.term}': {exc}")
    
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
