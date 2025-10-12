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
    """Remove various problematic prefixes and formatting from agency names"""
    if not name:
        return name

    # Apply multiple cleaning patterns in sequence
    patterns = [
        # Remove numbering prefixes like '1. ', '2. ', etc.
        (r'^\s*\d+\.\s*', ''),
        # Remove leading quotes
        (r'^"', ''),
        # Remove "A real estate agency *" patterns and similar
        (r'^A real estate agency \*.*$', ''),
        (r'^Agencies Specializing \*.*\*.*$', ''),
        # Remove letter prefixes like a) b) c)
        (r'^[a-zA-Z]\)\s*', ''),
        # Remove "Discovered" date patterns
        (r"'Discovered'\s*Oct\s*\d+", ''),
        (r"'Discovered'\s*[A-Za-z]{3}\s*\d+", ''),
        # Remove markdown bold formatting
        (r'\*\*([^*]+)\*\*', r'\1'),
        # Remove markdown italic formatting
        (r'\*([^*]+)\*', r'\1'),
        # Remove any remaining asterisks at start/end
        (r'^\*+|\*+$', ''),
    ]

    cleaned_name = name
    for pattern, replacement in patterns:
        cleaned_name = re.sub(pattern, replacement, cleaned_name, flags=re.IGNORECASE)

    return cleaned_name.strip()

def main():
    """Main function to clean agency names"""
    logging.info("Starting name cleaning for agencies...")

    try:
        conn = sqlite3.connect('agencies.db')
        cursor = conn.cursor()

        # Get agencies that need name cleaning (pending or not yet processed)
        cursor.execute('''
            SELECT id, name
            FROM agencies
            WHERE cleanup_status != 'cleaned' OR cleanup_status IS NULL
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
                    SET name = ?, cleanup_status = 'cleaned'
                    WHERE id = ?
                ''', (cleaned_name, agency_id))

                updated_count += 1
            else:
                # Mark as cleaned even if no change was needed
                cursor.execute('''
                    UPDATE agencies
                    SET cleanup_status = 'cleaned'
                    WHERE id = ?
                ''', (agency_id,))

        conn.commit()
        conn.close()

        logging.info(f"Successfully cleaned {updated_count} agency names")

    except Exception as e:
        logging.error(f"Error during name cleaning: {e}")

if __name__ == '__main__':
    main()
