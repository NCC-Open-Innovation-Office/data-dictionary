# Word Linking Feature

## Overview
The word linking feature allows administrators to create navigable relationships between dictionary entries. When entries are linked, the public view automatically displays "See [term]" links that allow users to jump directly to related terms.

## How It Works

### Admin Panel
1. **Creating/Editing an Entry**: When in the admin panel, you'll see a "Linked Entries" section in the form
2. **Adding a Link**: 
   - Select an entry from the "Link to Entry" dropdown
   - Click "Add Link" button
   - The linked entry will appear below with a "Remove" button
3. **Removing a Link**:
   - Click the "Remove" button next to any linked entry
   - The link will be deleted immediately (for existing entries)

### Public View
- When viewing the dictionary, entries with links will display "See [term]" below the definition
- Clicking on the linked term will:
  - Scroll smoothly to that entry in the dictionary
  - Highlight the entry with a yellow background for 2 seconds
  - Center the entry in the viewport

## Technical Details

### Database Schema
- Table: `entry_links`
- Columns:
  - `id`: Primary key
  - `source_entry_id`: The entry containing the link (foreign key to entries)
  - `target_entry_id`: The entry being linked to (foreign key to entries)
  - `link_type`: Type of link (currently "see_also")
  - `createdAt`: Timestamp of link creation

### API Endpoints
- `GET /api/entries/<id>/links` - Get all links for an entry
- `POST /api/entries/<id>/links` - Create a new link
  - Body: `{"target_entry_id": <id>, "link_type": "see_also"}`
- `DELETE /api/entries/<id>/links/<link_id>` - Remove a link

### Frontend Implementation
- **admin-api.js**: Manages link creation, removal, and syncing
  - `populateLinkSelect()`: Populates dropdown with available entries
  - `renderEntryLinks()`: Displays current links with remove buttons
  - `addLinkToEntry()`: Creates new link (saved immediately for existing entries)
  - `removeLinkFromEntry()`: Deletes link (saved immediately for existing entries)
  - `syncEntryLinks()`: Saves all links when creating new entry

- **public-api.js**: Displays links in public view
  - `renderTable()`: Adds "See [term]" links below definitions
  - `scrollToEntry()`: Handles smooth scrolling and highlighting

### Styling
- Entry links styled in blue (`#004C8E`) with hover effect to orange (`#FC5000`)
- Smooth scroll animation when jumping to linked entries
- Temporary yellow highlight (`#fff3cd`) for 2 seconds after jumping

## Use Cases
- Link deprecated terms to their replacements
- Connect related concepts in the data dictionary
- Point users to more detailed or alternative definitions
- Create a knowledge graph of interconnected terms

## Future Enhancements
- Support for different link types (e.g., "deprecated", "see also", "related")
- Bi-directional linking (show reverse links)
- Visual graph view of linked terms
- Link descriptions/notes
