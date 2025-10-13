#!/usr/bin/env python3
"""
Script to clean up malformed website URLs in the agencies database.
Handles issues like trailing punctuation, markdown link syntax, and other URL formatting problems.
"""

import sqlite3
import re
import logging
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def is_valid_url(url):
    """Check if URL is properly formatted"""
    if not url:
        return False
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

def clean_website_url(url):
    """Clean up malformed website URLs"""
    if not url or not isinstance(url, str):
        return url

    original_url = url.strip()

    # Handle markdown-style links: [text](url) -> url
    markdown_match = re.search(r'\[([^\]]*)\]\(([^)]+)\)', original_url)
    if markdown_match:
        url = markdown_match.group(2)
    else:
        # Handle corrupted markdown: text](url) -> url
        corrupted_markdown = re.search(r'\]\(([^)]+)\)', original_url)
        if corrupted_markdown:
            url = corrupted_markdown.group(1)

    # Remove trailing punctuation and brackets
    url = re.sub(r'[.,;:\]\)\s]+$', '', url)

    # Remove any leading brackets or punctuation
    url = re.sub(r'^[\[\(\s]+', '', url)

    # Fix common URL issues
    url = url.strip()

    # If URL doesn't have a scheme, add https://
    if url and not url.startswith(('http://', 'https://')):
        # Check if it looks like a domain
        if re.match(r'^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', url):
            # If it starts with www., add https://
            if url.startswith('www.'):
                url = f"https://{url}"
            else:
                # For bare domains, add https://www.
                url = f"https://www.{url}"

    # Final validation - only return if it's a valid URL
    if url and is_valid_url(url):
        return url
    else:
        # If cleaning made it invalid, return the original for manual review
        return original_url

def main():
    """Main function to clean website URLs"""
    logging.info("Starting website URL cleanup...")

    try:
        conn = sqlite3.connect('agencies.db')
        cursor = conn.cursor()

        # Get all agencies with website data
        cursor.execute('''
            SELECT id, name, website
            FROM agencies
            WHERE website IS NOT NULL AND website != ''
            ORDER BY id
        ''')

        agencies_to_check = cursor.fetchall()
        logging.info(f"Found {len(agencies_to_check)} agencies with website data to check")

        cleaned_count = 0
        skipped_count = 0

        for agency_id, name, website in agencies_to_check:
            cleaned_url = clean_website_url(website)

            if cleaned_url != website:
                logging.info(f"Cleaned URL for '{name}': '{website}' -> '{cleaned_url}'")
                cursor.execute('''
                    UPDATE agencies
                    SET website = ?
                    WHERE id = ?
                ''', (cleaned_url, agency_id))
                cleaned_count += 1
            else:
                skipped_count += 1

        conn.commit()
        conn.close()

        logging.info(f"URL cleanup complete: {cleaned_count} URLs cleaned, {skipped_count} URLs unchanged")

        # Show summary of changes
        print(f"\n✅ Website URL cleanup completed!")
        print(f"   📊 URLs cleaned: {cleaned_count}")
        print(f"   📊 URLs unchanged: {skipped_count}")

    except Exception as e:
        logging.error(f"Error during website URL cleanup: {e}")
        print(f"❌ Error during cleanup: {e}")

if __name__ == '__main__':
    main()
