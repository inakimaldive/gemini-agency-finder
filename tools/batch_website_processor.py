#!/usr/bin/env python3
"""
Batch Website Processor - Addresses remaining website challenges

This script tackles the remaining 269 website issues by:
1. Finding websites for agencies with missing URLs (87 agencies)
2. Finding alternative URLs for broken websites (173 agencies)
3. Upgrading HTTP to HTTPS for insecure sites (9 agencies)
4. Comprehensive validation and correction
"""

import sqlite3
import logging
import time
import json
from typing import List, Dict, Optional

# Import our enhanced tools
from enhanced_website_validator import EnhancedWebsiteValidator
from website_discovery_ai import AIWebsiteDiscoverer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class BatchWebsiteProcessor:
    def __init__(self):
        self.validator = EnhancedWebsiteValidator(use_chrome_devtools=False)
        self.ai_discoverer = AIWebsiteDiscoverer()
        self.processed_count = 0
        self.improved_count = 0

    def process_missing_websites(self, limit: int = 50) -> int:
        """Find websites for agencies that have none"""
        logging.info(f"🔍 Finding websites for agencies with missing URLs (limit: {limit})")

        conn = sqlite3.connect('agencies.db')
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, name, polish_city
            FROM agencies
            WHERE (website IS NULL OR website = '')
            AND type != 'undefined'
            ORDER BY id
            LIMIT ?
        ''', (limit,))

        agencies = cursor.fetchall()
        conn.close()

        if not agencies:
            logging.info("✅ No agencies found with missing websites")
            return 0

        logging.info(f"📋 Processing {len(agencies)} agencies with missing websites")

        improved = 0
        for agency_id, name, city in agencies:
            logging.info(f"🔎 Searching for website: {name}")

            # Try AI discovery first
            discovered_websites = self.ai_discoverer.discover_website_for_agency(name, city)

            if discovered_websites:
                # Use the AI discovery update function
                from website_discovery_ai import update_agency_with_discovered_website
                if update_agency_with_discovered_website(agency_id, discovered_websites):
                    improved += 1
                    logging.info(f"  ✅ Found website for {name}: {discovered_websites[0]['url']}")
                else:
                    logging.error(f"  ❌ Failed to update database for {name}")
            else:
                logging.info(f"  ⚠️ No website found for {name}")

            # Rate limiting
            time.sleep(2)

        logging.info(f"🤖 AI discovery complete: {improved}/{len(agencies)} agencies got websites")
        return improved

    def process_broken_websites(self, limit: int = 100) -> int:
        """Find alternative URLs for broken/invalid websites"""
        logging.info(f"🔧 Finding alternatives for broken websites (limit: {limit})")

        conn = sqlite3.connect('agencies.db')
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, name, website
            FROM agencies
            WHERE website IS NOT NULL AND website != ''
            AND website_status IN ('connection_error', 'not_found', 'timeout', 'invalid_url', 'ssl_error')
            AND type != 'undefined'
            ORDER BY id
            LIMIT ?
        ''', (limit,))

        agencies = cursor.fetchall()
        conn.close()

        if not agencies:
            logging.info("✅ No agencies found with broken websites")
            return 0

        logging.info(f"📋 Processing {len(agencies)} agencies with broken websites")

        improved = 0
        for agency_id, name, website in agencies:
            logging.info(f"🔄 Finding alternatives for: {name} ({website})")

            # Run comprehensive validation which includes alternative finding
            result = self.validator.validate_url_comprehensive(website)

            if result.get('final_url') != website or result.get('alternatives'):
                # Update with enhanced validation results
                from enhanced_website_validator import update_agency_website
                if update_agency_website(agency_id, result):
                    improved += 1
                    new_url = result.get('final_url', website)
                    alt_count = len(result.get('alternatives', []))
                    logging.info(f"  ✅ Improved {name}: {website} → {new_url} (+{alt_count} alternatives)")
                else:
                    logging.error(f"  ❌ Failed to update {name}")
            else:
                logging.info(f"  ⚠️ No improvements found for {name}")

            # Rate limiting
            time.sleep(1)

        logging.info(f"🔧 Broken website processing complete: {improved}/{len(agencies)} agencies improved")
        return improved

    def upgrade_http_to_https(self) -> int:
        """Upgrade HTTP-only websites to HTTPS"""
        logging.info("🔒 Upgrading HTTP websites to HTTPS")

        conn = sqlite3.connect('agencies.db')
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, name, website
            FROM agencies
            WHERE website LIKE 'http://%'
            AND type != 'undefined'
            ORDER BY id
        ''')

        agencies = cursor.fetchall()
        conn.close()

        if not agencies:
            logging.info("✅ No HTTP-only websites found")
            return 0

        logging.info(f"📋 Processing {len(agencies)} HTTP websites")

        upgraded = 0
        for agency_id, name, http_url in agencies:
            https_url = http_url.replace('http://', 'https://', 1)
            logging.info(f"⬆️ Testing HTTPS upgrade: {name}")

            # Test if HTTPS works
            result = self.validator.validate_url_comprehensive(https_url)

            if result['status'] == 'active':
                # Update to HTTPS
                update_result = {
                    'original_url': http_url,
                    'final_url': https_url,
                    'status': 'upgraded_to_https',
                    'redirects': result.get('redirects', []),
                    'alternatives': [],
                    'security_warnings': []
                }

                from enhanced_website_validator import update_agency_website
                if update_agency_website(agency_id, update_result):
                    upgraded += 1
                    logging.info(f"  ✅ Upgraded {name}: HTTP → HTTPS")
                else:
                    logging.error(f"  ❌ Failed to upgrade {name}")
            else:
                logging.info(f"  ⚠️ HTTPS not available for {name}")

            # Rate limiting
            time.sleep(1)

        logging.info(f"🔒 HTTPS upgrade complete: {upgraded}/{len(agencies)} websites upgraded")
        return upgraded

    def run_comprehensive_processing(self, missing_limit: int = 25, broken_limit: int = 50) -> Dict:
        """Run all processing steps"""
        logging.info("🚀 Starting comprehensive website processing")
        print("🚀 Starting comprehensive website processing...")

        results = {
            'missing_websites_found': 0,
            'broken_websites_fixed': 0,
            'http_upgraded': 0,
            'total_improved': 0
        }

        # Step 1: Find missing websites
        print("🔍 Step 1: Finding websites for agencies with missing URLs...")
        results['missing_websites_found'] = self.process_missing_websites(missing_limit)

        # Step 2: Fix broken websites
        print("🔧 Step 2: Finding alternatives for broken websites...")
        results['broken_websites_fixed'] = self.process_broken_websites(broken_limit)

        # Step 3: Upgrade HTTP to HTTPS
        print("🔒 Step 3: Upgrading HTTP websites to HTTPS...")
        results['http_upgraded'] = self.upgrade_http_to_https()

        results['total_improved'] = sum(results.values())

        logging.info(f"🎉 Comprehensive processing complete: {results['total_improved']} total improvements")
        print("\n🎉 Comprehensive processing complete!")
        print(f"   🤖 Websites found for missing entries: {results['missing_websites_found']}")
        print(f"   🔧 Broken websites fixed: {results['broken_websites_fixed']}")
        print(f"   🔒 HTTP upgraded to HTTPS: {results['http_upgraded']}")
        print(f"   📊 Total improvements: {results['total_improved']}")

        return results

def main():
    """Main function to run batch website processing"""
    processor = BatchWebsiteProcessor()

    # Run comprehensive processing with reasonable limits
    results = processor.run_comprehensive_processing(
        missing_limit=25,  # Process 25 missing websites
        broken_limit=50    # Process 50 broken websites
    )

    # Update web interface data
    print("\n📤 Updating web interface data...")
    import subprocess
    result = subprocess.run(['bash', 'tools/update_data.sh'],
                          capture_output=True, text=True)
    if result.returncode == 0:
        print("✅ Web interface data updated")
    else:
        print("⚠️ Web interface update had issues")

if __name__ == '__main__':
    main()
