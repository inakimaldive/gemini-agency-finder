#!/usr/bin/env python3
"""
Script to clean up agency names by removing numbering prefixes like "1. " or "2. "
"""

import sqlite3
import re
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def clean_name_prefix(name):
    """Remove numbering prefixes like '1. ', '2. ', etc. from the beginning of names"""
    if not name:
        return name

    # Pattern to match: optional whitespace + digits + period + optional whitespace
    pattern = r'^\s*\d+\.\s*'
    cleaned_name = re.sub(pattern, '', name)

    return cleaned_name.strip()

def main():
    """Main function to clean agency names"""
    logging.info("Starting name cleaning for agencies...")

    try:
        conn = sqlite3.connect('agencies.db')
        cursor = conn.cursor()

        # Get all agencies
        cursor.execute('''
            SELECT id, name
            FROM agencies
            ORDER BY id
        ''')

        agencies = cursor.fetchall()
        logging.info(f"Found {len(agencies)} agencies to check for cleaning")

        updated_count = 0

        for agency_id, name in agencies:
            cleaned_name = clean_name_prefix(name)

            if cleaned_name != name:
                logging.info(f"Cleaning '{name}' -> '{cleaned_name}'")

                # Update the database
                cursor.execute('''
                    UPDATE agencies
                    SET name = ?
                    WHERE id = ?
                ''', (cleaned_name, agency_id))

                updated_count += 1

        conn.commit()
        conn.close()

        logging.info(f"Successfully cleaned {updated_count} agency names")

    except Exception as e:
        logging.error(f"Error during name cleaning: {e}")

if __name__ == '__main__':
    main()
