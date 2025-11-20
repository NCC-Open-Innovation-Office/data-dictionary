from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import json
from datetime import datetime
import os

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend access

DATABASE = os.environ.get('DATABASE', 'dictionary.db')

def get_db():
    """Create a database connection"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  # Return rows as dictionaries
    return conn

def init_db():
    """Initialize the database with required tables"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Create entries table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            term TEXT NOT NULL,
            definition TEXT NOT NULL,
            abbreviation TEXT,
            dataType TEXT,
            inputFormat TEXT,
            variations TEXT,
            owner TEXT,
            stewards TEXT,
            classification TEXT DEFAULT 'public',
            discussion TEXT,
            createdAt TEXT NOT NULL,
            updatedAt TEXT NOT NULL
        )
    ''')
    
    # Add new columns if they don't exist (for existing databases)
    try:
        cursor.execute('ALTER TABLE entries ADD COLUMN owner TEXT')
    except sqlite3.OperationalError:
        pass
    
    try:
        cursor.execute('ALTER TABLE entries ADD COLUMN stewards TEXT')
    except sqlite3.OperationalError:
        pass
    
    try:
        cursor.execute('ALTER TABLE entries ADD COLUMN classification TEXT DEFAULT "public"')
    except sqlite3.OperationalError:
        pass
    
    # Create change_history table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS change_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            action TEXT NOT NULL,
            term TEXT NOT NULL,
            oldData TEXT,
            newData TEXT,
            discussion TEXT,
            user TEXT NOT NULL
        )
    ''')
    
    # Create tags table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            color TEXT DEFAULT '#004C8E',
            createdAt TEXT NOT NULL
        )
    ''')
    
    # Create entry_tags junction table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS entry_tags (
            entry_id INTEGER NOT NULL,
            tag_id INTEGER NOT NULL,
            PRIMARY KEY (entry_id, tag_id),
            FOREIGN KEY (entry_id) REFERENCES entries(id) ON DELETE CASCADE,
            FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
        )
    ''')
    
    # Create entry_links table for word linking feature
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS entry_links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_entry_id INTEGER NOT NULL,
            target_entry_id INTEGER NOT NULL,
            link_type TEXT DEFAULT 'see_also',
            createdAt TEXT NOT NULL,
            FOREIGN KEY (source_entry_id) REFERENCES entries(id) ON DELETE CASCADE,
            FOREIGN KEY (target_entry_id) REFERENCES entries(id) ON DELETE CASCADE
        )
    ''')
    
    conn.commit()
    conn.close()

# Initialize database on startup
init_db()

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'ok', 'message': 'API is running'})

@app.route('/api/entries', methods=['GET'])
def get_entries():
    """Get all dictionary entries with their tags (public endpoint)"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Get all entries
        cursor.execute('SELECT * FROM entries ORDER BY term ASC')
        entries = [dict(row) for row in cursor.fetchall()]
        
        # Get tags for each entry
        for entry in entries:
            cursor.execute('''
                SELECT t.id, t.name, t.color 
                FROM tags t
                JOIN entry_tags et ON t.id = et.tag_id
                WHERE et.entry_id = ?
                ORDER BY t.name
            ''', (entry['id'],))
            entry['tags'] = [dict(row) for row in cursor.fetchall()]
            
            # Get links for each entry
            cursor.execute('''
                SELECT el.id as link_id, el.target_entry_id, el.link_type, 
                       e.term as target_term
                FROM entry_links el
                JOIN entries e ON el.target_entry_id = e.id
                WHERE el.source_entry_id = ?
            ''', (entry['id'],))
            entry['links'] = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        return jsonify(entries)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/entries/<int:entry_id>', methods=['GET'])
def get_entry(entry_id):
    """Get a single entry by ID"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM entries WHERE id = ?', (entry_id,))
        entry = cursor.fetchone()
        conn.close()
        
        if entry:
            return jsonify(dict(entry))
        else:
            return jsonify({'error': 'Entry not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/entries', methods=['POST'])
def create_entry():
    """Create a new entry (admin only)"""
    try:
        data = request.json
        now = datetime.utcnow().isoformat()
        
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO entries (term, definition, abbreviation, dataType, 
                               inputFormat, variations, owner, stewards, 
                               classification, discussion, createdAt, updatedAt)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['term'],
            data['definition'],
            data.get('abbreviation', ''),
            data.get('dataType', ''),
            data.get('inputFormat', ''),
            data.get('variations', ''),
            data.get('owner', ''),
            data.get('stewards', ''),
            data.get('classification', 'public'),
            data.get('discussion', ''),
            now,
            now
        ))
        
        entry_id = cursor.lastrowid
        
        # Log the change
        cursor.execute('''
            INSERT INTO change_history (timestamp, action, term, oldData, newData, discussion, user)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            now,
            'create',
            data['term'],
            None,
            json.dumps(data),
            data.get('discussion', ''),
            data.get('user', 'Admin')
        ))
        
        conn.commit()
        conn.close()
        
        return jsonify({'id': entry_id, 'message': 'Entry created successfully'}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/entries/<int:entry_id>', methods=['PUT'])
def update_entry(entry_id):
    """Update an existing entry (admin only)"""
    try:
        data = request.json
        now = datetime.utcnow().isoformat()
        
        conn = get_db()
        cursor = conn.cursor()
        
        # Get old data for change tracking
        cursor.execute('SELECT * FROM entries WHERE id = ?', (entry_id,))
        old_entry = cursor.fetchone()
        
        if not old_entry:
            conn.close()
            return jsonify({'error': 'Entry not found'}), 404
        
        old_data = dict(old_entry)
        
        # Update the entry
        cursor.execute('''
            UPDATE entries
            SET term = ?, definition = ?, abbreviation = ?, dataType = ?, 
                inputFormat = ?, variations = ?, owner = ?, stewards = ?,
                classification = ?, discussion = ?, updatedAt = ?
            WHERE id = ?
        ''', (
            data['term'],
            data['definition'],
            data.get('abbreviation', ''),
            data.get('dataType', ''),
            data.get('inputFormat', ''),
            data.get('variations', ''),
            data.get('owner', ''),
            data.get('stewards', ''),
            data.get('classification', 'public'),
            data.get('discussion', ''),
            now,
            entry_id
        ))
        
        # Log the change
        cursor.execute('''
            INSERT INTO change_history (timestamp, action, term, oldData, newData, discussion, user)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            now,
            'update',
            data['term'],
            json.dumps(old_data),
            json.dumps(data),
            data.get('discussion', ''),
            data.get('user', 'Admin')
        ))
        
        conn.commit()
        conn.close()
        
        return jsonify({'message': 'Entry updated successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/entries/<int:entry_id>', methods=['DELETE'])
def delete_entry(entry_id):
    """Delete an entry (admin only)"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Get entry data before deletion for logging
        cursor.execute('SELECT * FROM entries WHERE id = ?', (entry_id,))
        entry = cursor.fetchone()
        
        if not entry:
            conn.close()
            return jsonify({'error': 'Entry not found'}), 404
        
        entry_data = dict(entry)
        now = datetime.utcnow().isoformat()
        
        # Delete the entry
        cursor.execute('DELETE FROM entries WHERE id = ?', (entry_id,))
        
        # Log the change
        cursor.execute('''
            INSERT INTO change_history (timestamp, action, term, oldData, newData, discussion, user)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            now,
            'delete',
            entry_data['term'],
            json.dumps(entry_data),
            None,
            request.json.get('discussion', '') if request.json else '',
            request.json.get('user', 'Admin') if request.json else 'Admin'
        ))
        
        conn.commit()
        conn.close()
        
        return jsonify({'message': 'Entry deleted successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/history', methods=['GET'])
def get_history():
    """Get change history (admin only)"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM change_history ORDER BY timestamp DESC')
        history = [dict(row) for row in cursor.fetchall()]
        
        # Parse JSON strings back to objects
        for item in history:
            if item['oldData']:
                item['oldData'] = json.loads(item['oldData'])
            if item['newData']:
                item['newData'] = json.loads(item['newData'])
        
        conn.close()
        return jsonify(history)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Tag management endpoints
@app.route('/api/tags', methods=['GET'])
def get_tags():
    """Get all tags"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM tags ORDER BY name ASC')
        tags = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return jsonify(tags)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/tags', methods=['POST'])
def create_tag():
    """Create a new tag (admin only)"""
    try:
        data = request.json
        now = datetime.utcnow().isoformat()
        
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO tags (name, color, createdAt)
            VALUES (?, ?, ?)
        ''', (
            data['name'],
            data.get('color', '#004C8E'),
            now
        ))
        
        tag_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return jsonify({'id': tag_id, 'message': 'Tag created successfully'}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/tags/<int:tag_id>', methods=['DELETE'])
def delete_tag(tag_id):
    """Delete a tag (admin only)"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM tags WHERE id = ?', (tag_id,))
        conn.commit()
        conn.close()
        return jsonify({'message': 'Tag deleted successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/entries/<int:entry_id>/tags', methods=['POST'])
def add_entry_tag(entry_id):
    """Add a tag to an entry (admin only)"""
    try:
        data = request.json
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR IGNORE INTO entry_tags (entry_id, tag_id)
            VALUES (?, ?)
        ''', (entry_id, data['tag_id']))
        
        conn.commit()
        conn.close()
        return jsonify({'message': 'Tag added to entry'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/entries/<int:entry_id>/tags/<int:tag_id>', methods=['DELETE'])
def remove_entry_tag(entry_id, tag_id):
    """Remove a tag from an entry (admin only)"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM entry_tags WHERE entry_id = ? AND tag_id = ?', (entry_id, tag_id))
        conn.commit()
        conn.close()
        return jsonify({'message': 'Tag removed from entry'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/owners', methods=['GET'])
def get_owners():
    """Get unique list of owners for autocomplete"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT DISTINCT owner FROM entries WHERE owner IS NOT NULL AND owner != "" ORDER BY owner')
        owners = [row[0] for row in cursor.fetchall()]
        conn.close()
        return jsonify(owners)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/stewards', methods=['GET'])
def get_stewards():
    """Get unique list of stewards for autocomplete"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT DISTINCT stewards FROM entries WHERE stewards IS NOT NULL AND stewards != "" ORDER BY stewards')
        stewards = [row[0] for row in cursor.fetchall()]
        conn.close()
        return jsonify(stewards)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/entries/<int:entry_id>/links', methods=['GET'])
def get_entry_links(entry_id):
    """Get all links for an entry"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT el.id as link_id, el.target_entry_id, el.link_type,
                   e.term as target_term
            FROM entry_links el
            JOIN entries e ON el.target_entry_id = e.id
            WHERE el.source_entry_id = ?
        ''', (entry_id,))
        links = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return jsonify(links)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/entries/<int:entry_id>/links', methods=['POST'])
def add_entry_link(entry_id):
    """Add a link to an entry"""
    try:
        data = request.json
        now = datetime.utcnow().isoformat()
        
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO entry_links (source_entry_id, target_entry_id, link_type, createdAt)
            VALUES (?, ?, ?, ?)
        ''', (entry_id, data['target_entry_id'], data.get('link_type', 'see_also'), now))
        
        link_id = cursor.lastrowid
        
        # Get the target entry term
        cursor.execute('SELECT term FROM entries WHERE id = ?', (data['target_entry_id'],))
        target_term = cursor.fetchone()[0]
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'link_id': link_id,
            'target_entry_id': data['target_entry_id'],
            'target_term': target_term,
            'link_type': data.get('link_type', 'see_also')
        }), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/entries/<int:entry_id>/links/<int:link_id>', methods=['DELETE'])
def remove_entry_link(entry_id, link_id):
    """Remove a link from an entry"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM entry_links WHERE id = ? AND source_entry_id = ?', (link_id, entry_id))
        conn.commit()
        conn.close()
        return jsonify({'message': 'Link removed successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/entries/bulk-import', methods=['POST'])
def bulk_import_entries():
    """Bulk import entries from CSV data (for Excel restore functionality)"""
    try:
        data = request.json
        entries = data.get('entries', [])
        
        if not entries:
            return jsonify({'error': 'No entries provided'}), 400
        
        conn = get_db()
        cursor = conn.cursor()
        
        imported = 0
        updated = 0
        skipped = 0
        errors = []
        
        for entry in entries:
            try:
                term = entry.get('term', '').strip()
                if not term:
                    skipped += 1
                    continue
                
                # Check if entry exists
                cursor.execute('SELECT id FROM entries WHERE term = ?', (term,))
                existing = cursor.fetchone()
                
                now = datetime.utcnow().isoformat()
                
                if existing:
                    # Update existing entry
                    cursor.execute('''
                        UPDATE entries 
                        SET definition = ?, abbreviation = ?, dataType = ?,
                            inputFormat = ?, variations = ?, owner = ?,
                            stewards = ?, classification = ?, discussion = ?,
                            updatedAt = ?
                        WHERE term = ?
                    ''', (
                        entry.get('definition', ''),
                        entry.get('abbreviation', ''),
                        entry.get('dataType', ''),
                        entry.get('inputFormat', ''),
                        entry.get('variations', ''),
                        entry.get('owner', ''),
                        entry.get('stewards', ''),
                        entry.get('classification', 'public'),
                        entry.get('discussion', ''),
                        now,
                        term
                    ))
                    updated += 1
                else:
                    # Insert new entry
                    cursor.execute('''
                        INSERT INTO entries (term, definition, abbreviation, dataType, 
                                           inputFormat, variations, owner, stewards, 
                                           classification, discussion, createdAt, updatedAt)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        term,
                        entry.get('definition', ''),
                        entry.get('abbreviation', ''),
                        entry.get('dataType', ''),
                        entry.get('inputFormat', ''),
                        entry.get('variations', ''),
                        entry.get('owner', ''),
                        entry.get('stewards', ''),
                        entry.get('classification', 'public'),
                        entry.get('discussion', ''),
                        now,
                        now
                    ))
                    imported += 1
                    
            except Exception as e:
                errors.append(f"Error with term '{term}': {str(e)}")
                skipped += 1
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'message': 'Import completed',
            'imported': imported,
            'updated': updated,
            'skipped': skipped,
            'errors': errors
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=False)
