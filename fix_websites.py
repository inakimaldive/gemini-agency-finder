#!/usr/bin/env python3
"""
Script to fix missing website information for gemini_discovered agencies
by extracting URLs from their description fields.
"""

import sqlite3
import re
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def extract_urls_from_text(text):
    """Extract URLs and email-based websites from text using regex"""
    if not text:
        return []

    urls = []

    # First, look for actual URLs
    url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
    found_urls = re.findall(url_pattern, text, re.IGNORECASE)
    for url in found_urls:
        url = re.sub(r'[.,;]$', '', url)
        urls.append(url)

    # Then, look for email addresses and deduce websites from them
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    emails = re.findall(email_pattern, text)

    for email in emails:
        domain = email.split('@')[1]
        # Convert domain to potential website
        if not domain.startswith('www.'):
            website = f"https://www.{domain}"
        else:
            website = f"https://{domain}"

        # Only add if we don't already have a URL
        if not urls:
            urls.append(website)

    return urls

def main():
    """Main function to fix missing websites"""
    logging.info("Starting website extraction for gemini_discovered agencies...")

    try:
        conn = sqlite3.connect('agencies.db')
        cursor = conn.cursor()

        # Get all gemini_discovered agencies with missing website
        cursor.execute('''
            SELECT id, name, description
            FROM agencies
            WHERE type = 'gemini_discovered'
            AND (website IS NULL OR website = '')
            ORDER BY id
        ''')

        agencies = cursor.fetchall()
        logging.info(f"Found {len(agencies)} agencies with missing website info")

        updated_count = 0

        for agency_id, name, description in agencies:
            urls = extract_urls_from_text(description)

            if urls:
                # Take the first URL found
                website = urls[0]
                logging.info(f"Found website for '{name}': {website}")

                # Update the database
                cursor.execute('''
                    UPDATE agencies
                    SET website = ?
                    WHERE id = ?
                ''', (website, agency_id))

                updated_count += 1
            else:
                logging.debug(f"No URL found in description for '{name}'")

        conn.commit()
        conn.close()

        logging.info(f"Successfully updated {updated_count} agencies with website information")

    except Exception as e:
        logging.error(f"Error during website extraction: {e}")

if __name__ == '__main__':
    main()
