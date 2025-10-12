#!/usr/bin/env python3
"""
Script to move agencies with no useful information to a separate 'undefined' table
"""

import sqlite3
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def create_undefined_table():
    """Create the undefined table with the same schema as agencies"""
    return """
    CREATE TABLE IF NOT EXISTS undefined (
        id INTEGER PRIMARY KEY,
        name TEXT,
        type TEXT,
        website TEXT,
        phone TEXT,
        address TEXT,
        description TEXT,
        additional_info TEXT,
        website_status TEXT
    );
    """

def is_empty_field(field):
    """Check if a field is empty (None, empty string, or whitespace only)"""
    return field is None or str(field).strip() == ""

def main():
    """Main function to move undefined agencies"""
    logging.info("Starting to move undefined agencies to separate table...")

    try:
        conn = sqlite3.connect('agencies.db')
        cursor = conn.cursor()

        # Create the undefined table
        cursor.execute(create_undefined_table())
        logging.info("Created 'undefined' table")

        # Find agencies with no useful information that haven't been processed yet
        cursor.execute('''
            SELECT id, name, type, website, phone, address, description, additional_info, website_status
            FROM agencies
            WHERE (website IS NULL OR website = '')
            AND (phone IS NULL OR phone = '')
            AND (address IS NULL OR address = '')
            AND (description IS NULL OR description = '')
            AND (cleanup_status != 'undefined' OR cleanup_status IS NULL)
        ''')

        undefined_agencies = cursor.fetchall()
        logging.info(f"Found {len(undefined_agencies)} agencies with no useful information")

        if undefined_agencies:
            # Check which agencies are not already in undefined table
            existing_ids = set()
            cursor.execute('SELECT id FROM undefined')
            existing_ids = set(row[0] for row in cursor.fetchall())

            # Filter out agencies that are already in undefined
            new_undefined_agencies = [agency for agency in undefined_agencies if agency[0] not in existing_ids]

            if new_undefined_agencies:
                # Insert into undefined table (without preserving original IDs to avoid conflicts)
                cursor.executemany('''
                    INSERT INTO undefined (name, type, website, phone, address, description, additional_info, website_status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', [agency[1:] for agency in new_undefined_agencies])  # Skip the ID field

                # Get the IDs to delete from agencies table
                undefined_ids = [agency[0] for agency in new_undefined_agencies]

                # Delete from agencies table
                cursor.execute(f'''
                    DELETE FROM agencies
                    WHERE id IN ({','.join('?' * len(undefined_ids))})
                ''', undefined_ids)

                logging.info(f"Moved {len(new_undefined_agencies)} agencies to 'undefined' table")

                # Show some examples
                for agency in new_undefined_agencies[:5]:
                    logging.info(f"Moved: '{agency[1]}' (ID: {agency[0]})")
            else:
                logging.info("No new agencies to move (all candidates already in undefined table)")

        conn.commit()
        conn.close()

        logging.info("Successfully completed moving undefined agencies")

    except Exception as e:
        logging.error(f"Error during moving undefined agencies: {e}")

if __name__ == '__main__':
    main()
