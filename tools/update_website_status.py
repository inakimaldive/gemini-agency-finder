#!/usr/bin/env python3
"""
Script to automatically update agency types based on website status
Agencies with inactive/broken websites are marked as 'inactive' type.
"""

import sqlite3
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def update_types_based_on_website_status():
    """Update agency types based on their website status"""
    logging.info("Starting automatic type updates based on website status...")

    try:
        conn = sqlite3.connect('agencies.db')
        cursor = conn.cursor()

        # Get agencies with website status information (process recent entries first)
        cursor.execute('''
            SELECT id, name, type, website_status
            FROM agencies
            WHERE website_status IS NOT NULL AND website_status != ''
            ORDER BY id DESC
        ''')

        agencies = cursor.fetchall()
        logging.info(f"Found {len(agencies)} agencies with website status information")

        updated_count = 0
        inactive_count = 0

        for agency_id, name, current_type, website_status in agencies:
            new_type = current_type

            # Mark agencies with inactive/broken websites as 'inactive'
            if website_status.startswith(('inactive', 'connection_error', 'timeout', 'http_5', 'http_4')):
                if current_type != 'inactive':
                    new_type = 'inactive'
                    inactive_count += 1
                    logging.info(f"Marking '{name}' as inactive (website status: {website_status})")
                # Keep as inactive if already marked

            # Only update if type changed
            if new_type != current_type:
                cursor.execute('''
                    UPDATE agencies
                    SET type = ?
                    WHERE id = ?
                ''', (new_type, agency_id))
                updated_count += 1

        conn.commit()
        conn.close()

        logging.info(f"Successfully updated {updated_count} agencies based on website status")
        logging.info(f"Marked {inactive_count} agencies as inactive due to broken websites")

    except Exception as e:
        logging.error(f"Error during website status updates: {e}")

def show_status_summary():
    """Show a summary of website statuses and types"""
    try:
        conn = sqlite3.connect('agencies.db')
        cursor = conn.cursor()

        # Website status summary
        cursor.execute('''
            SELECT website_status, COUNT(*) as count
            FROM agencies
            WHERE website_status IS NOT NULL AND website_status != ''
            GROUP BY website_status
            ORDER BY count DESC
            LIMIT 10
        ''')

        status_results = cursor.fetchall()

        # Type distribution
        cursor.execute('''
            SELECT type, COUNT(*) as count
            FROM agencies
            GROUP BY type
            ORDER BY count DESC
        ''')

        type_results = cursor.fetchall()

        conn.close()

        logging.info("Website Status Summary:")
        for status, count in status_results:
            logging.info(f"  {status}: {count} agencies")

        logging.info("Agency Type Distribution:")
        for agency_type, count in type_results:
            logging.info(f"  {agency_type}: {count} agencies")

    except Exception as e:
        logging.error(f"Error generating status summary: {e}")

if __name__ == '__main__':
    update_types_based_on_website_status()
    show_status_summary()
