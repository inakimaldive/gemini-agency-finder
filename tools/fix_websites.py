#!/usr/bin/env python3
"""
Enhanced script to fix missing and invalid website information for agencies
by extracting URLs from descriptions and fixing common URL issues.
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

def fix_url_format(url):
    """Fix common URL formatting issues"""
    if not url:
        return url

    url = url.strip()

    # Remove trailing punctuation that might be part of text
    url = re.sub(r'[.,;]$', '', url)

    # If URL doesn't have a scheme, add https://
    if not url.startswith(('http://', 'https://')):
        # Check if it looks like a domain
        if re.match(r'^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', url):
            # If it starts with www., add https://
            if url.startswith('www.'):
                url = f"https://{url}"
            else:
                # For bare domains, add https://www.
                url = f"https://www.{url}"
        else:
            # If it doesn't look like a domain, return as-is
            return url

    return url

def extract_urls_from_text(text):
    """Extract URLs and email-based websites from text using enhanced regex"""
    if not text:
        return []

    urls = []

    # Look for actual URLs (including incomplete ones)
    url_patterns = [
        r'https?://[^\s<>"{}|\\^`\[\]]+',  # Full URLs
        r'www\.[^\s<>"{}|\\^`\[\]]+',      # www. domains
        r'[a-zA-Z0-9.-]+\.(?:com|pl|es|eu|net|org|biz|info)(?:/[^\s<>"{}|\\^`\[\]]*)*',  # Domain + TLD
    ]

    for pattern in url_patterns:
        found_urls = re.findall(pattern, text, re.IGNORECASE)
        for url in found_urls:
            url = re.sub(r'[.,;]$', '', url)  # Remove trailing punctuation
            fixed_url = fix_url_format(url)
            if fixed_url and fixed_url not in urls:
                urls.append(fixed_url)

    # Look for email addresses and deduce websites from them
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
        if website not in urls:
            urls.append(website)

    return urls

def main():
    """Main function to fix missing and invalid websites"""
    logging.info("Starting enhanced website fixing for all agencies...")

    try:
        conn = sqlite3.connect('agencies.db')
        cursor = conn.cursor()

        # Process agencies that haven't been cleaned yet
        cursor.execute('''
            SELECT id, name, website, description
            FROM agencies
            WHERE cleanup_status != 'cleaned' OR cleanup_status IS NULL
            ORDER BY id
        ''')

        agencies_to_process = cursor.fetchall()
        logging.info(f"Found {len(agencies_to_process)} agencies to check for website fixes")

        fixed_invalid_count = 0
        extracted_count = 0

        for agency_id, name, website, description in agencies_to_process:
            updated = False

            # First, fix invalid URLs that are already in the database
            if website and not is_valid_url(website):
                fixed_url = fix_url_format(website)
                if fixed_url != website and is_valid_url(fixed_url):
                    logging.info(f"Fixed invalid URL for '{name}': '{website}' -> '{fixed_url}'")
                    cursor.execute('''
                        UPDATE agencies
                        SET website = ?, cleanup_status = 'cleaned'
                        WHERE id = ?
                    ''', (fixed_url, agency_id))
                    fixed_invalid_count += 1
                    updated = True

            # Then, extract URLs from descriptions for agencies with missing websites
            if not website or website == '':
                urls = extract_urls_from_text(description)

                if urls:
                    # Take the first URL found
                    website = urls[0]
                    logging.info(f"Extracted website for '{name}': {website}")

                    # Update the database
                    cursor.execute('''
                        UPDATE agencies
                        SET website = ?, cleanup_status = 'cleaned'
                        WHERE id = ?
                    ''', (website, agency_id))

                    extracted_count += 1
                    updated = True

            # Mark as cleaned even if no changes were made
            if not updated:
                cursor.execute('''
                    UPDATE agencies
                    SET cleanup_status = 'cleaned'
                    WHERE id = ?
                ''', (agency_id,))

        conn.commit()
        conn.close()

        logging.info(f"Successfully fixed {fixed_invalid_count} invalid URLs and extracted {extracted_count} new websites")

    except Exception as e:
        logging.error(f"Error during website fixing: {e}")

if __name__ == '__main__':
    main()
