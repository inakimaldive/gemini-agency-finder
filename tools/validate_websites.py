#!/usr/bin/env python3
"""
Script to validate website URLs for agencies by checking if they are accessible
"""

import sqlite3
import requests
import logging
import time
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def is_valid_url(url):
    """Check if URL is properly formatted"""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

def check_website_status(url, timeout=10):
    """Check if website is accessible and returns a valid response"""
    if not url or not is_valid_url(url):
        return "invalid_url"

    try:
        # Set headers to mimic a browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        response = requests.head(url, timeout=timeout, headers=headers, allow_redirects=True)

        if response.status_code == 200:
            return "active"
        elif response.status_code in [301, 302, 303, 307, 308]:
            return "redirect"
        elif response.status_code == 404:
            return "not_found"
        elif response.status_code >= 500:
            return "server_error"
        else:
            return f"http_{response.status_code}"

    except requests.exceptions.Timeout:
        return "timeout"
    except requests.exceptions.ConnectionError:
        return "connection_error"
    except requests.exceptions.RequestException as e:
        return f"error_{str(e)[:20]}"
    except Exception as e:
        return f"unknown_error_{str(e)[:20]}"

def main():
    """Main function to validate websites"""
    logging.info("Starting website validation for all agencies...")

    try:
        conn = sqlite3.connect('agencies.db')
        cursor = conn.cursor()

        # Get all agencies with websites
        cursor.execute('''
            SELECT id, name, website
            FROM agencies
            WHERE website IS NOT NULL AND website != ''
            ORDER BY id
        ''')

        agencies = cursor.fetchall()
        logging.info(f"Found {len(agencies)} agencies with websites to validate")

        updated_count = 0
        status_counts = {}

        for agency_id, name, website in agencies:
            status = check_website_status(website)
            status_counts[status] = status_counts.get(status, 0) + 1

            logging.info(f"Checked '{name}': {website} -> {status}")

            # Update the database with website status
            cursor.execute('''
                UPDATE agencies
                SET website_status = ?
                WHERE id = ?
            ''', (status, agency_id))

            updated_count += 1

            # Rate limiting to be respectful to websites
            time.sleep(0.5)

        conn.commit()
        conn.close()

        logging.info(f"Successfully validated {updated_count} websites")

        # Show summary
        logging.info("Website validation summary:")
        for status, count in sorted(status_counts.items()):
            logging.info(f"  {status}: {count} websites")

    except Exception as e:
        logging.error(f"Error during website validation: {e}")

if __name__ == '__main__':
    main()
