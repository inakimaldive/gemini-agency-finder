#!/usr/bin/env python3
"""
Enrich Inactive Agencies - Uses Gemini AI to search for more information about inactive agencies
that have name and address data.
"""

import sqlite3
import json
import os
import sys
import time
from datetime import datetime
import logging

# Add parent directory to path to import GeminiAgencyFinder
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from gemini_agency_finder import GeminiAgencyFinder

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('enrich_inactive_agencies.log'),
        logging.StreamHandler()
    ]
)

class InactiveAgencyEnricher:
    def __init__(self, db_path='agencies.db'):
        self.db_path = db_path
        self.finder = GeminiAgencyFinder(db_path=db_path)

    def get_inactive_agencies_with_data(self):
        """Get agencies that are inactive but have name and address information"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Query for inactive agencies based on the frontend logic
            cursor.execute('''
                SELECT id, name, website, phone, address, description, website_status, alternative_urls
                FROM agencies
                WHERE website IS NOT NULL AND website != ''
                AND website_status IN ('inactive', 'connection_error', 'timeout', 'ssl_error', 'http_405', 'http_403', 'http_400', 'upgraded_to_https')
                AND name IS NOT NULL AND name != ''
                AND address IS NOT NULL AND address != ''
                ORDER BY id
            ''')

            agencies = []
            for row in cursor.fetchall():
                agency_id, name, website, phone, address, description, website_status, alternative_urls = row

                # Check if there are any working alternatives
                has_working_alternatives = False
                if alternative_urls:
                    try:
                        alts = json.loads(alternative_urls)
                        if isinstance(alts, list):
                            has_working_alternatives = any(
                                alt.get('status') in ['active', 'corrected'] for alt in alts
                            )
                    except:
                        pass

                # Only include if no working alternatives (truly inactive)
                if not has_working_alternatives:
                    agencies.append({
                        'id': agency_id,
                        'name': name,
                        'website': website,
                        'phone': phone,
                        'address': address,
                        'description': description,
                        'website_status': website_status
                    })

            conn.close()
            return agencies

        except Exception as e:
            logging.error(f"Error getting inactive agencies: {e}")
            return []

    def enrich_agency_info(self, agency, max_retries=2):
        """Use Gemini to search for more information about an agency"""
        name = agency['name']
        address = agency['address']

        # Create search prompt
        prompt = f"""Search the web for the real estate agency "{name}" located at "{address}" in Spain.

Please provide detailed information about this agency including:
- Current website URL (if different from known)
- Phone number (if different from known)
- Updated address information
- Services offered
- Areas they serve (Costa del Sol, Marbella, etc.)
- Any additional contact information
- Current status (active/inactive)

Focus on finding working contact information and current business status.
If the agency has moved, merged, or changed names, please note this.

Return the information in a clear, structured format."""

        logging.info(f"Searching for more info on: {name}")

        for attempt in range(max_retries):
            try:
                response = self.finder.run_gemini_prompt(prompt, use_web_search=True)
                if response:
                    logging.info(f"✅ Got response for {name} (attempt {attempt + 1})")
                    return self.parse_enrichment_response(response)
                else:
                    logging.warning(f"❌ No response for {name} (attempt {attempt + 1})")
            except Exception as e:
                logging.error(f"💥 Error enriching {name} (attempt {attempt + 1}): {e}")

            if attempt < max_retries - 1:
                time.sleep(2)  # Wait before retry

        return None

    def parse_enrichment_response(self, response):
        """Parse the Gemini response to extract useful information"""
        import re
        updates = {}

        # Look for specific patterns in the response
        lines = response.split('\n')

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Extract website
            if 'website' in line.lower() and ('http' in line or 'www' in line):
                # Try to extract URL
                url_match = re.search(r'https?://[^\s]+', line)
                if url_match:
                    updates['website'] = url_match.group(0).rstrip('.,;')

            # Extract phone
            if 'phone' in line.lower() or 'tel' in line.lower():
                # Try to extract phone number
                phone_match = re.search(r'[\+]?[\d\s\-\(\)]{7,}', line)
                if phone_match:
                    updates['phone'] = phone_match.group(0).strip()

            # Extract address
            if 'address' in line.lower() or 'location' in line.lower():
                # Take the rest of the line as address
                addr_part = line.split(':', 1)[-1].strip()
                if addr_part and len(addr_part) > 10:  # Reasonable address length
                    updates['address'] = addr_part

        # If we found any updates, also store the raw response for reference
        if updates:
            updates['_raw_response'] = response[:500]  # First 500 chars

        return updates if updates else None

    def update_agency_in_db(self, agency_id, updates):
        """Update agency information in the database"""
        if not updates:
            return False

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Build update query
            set_parts = []
            values = []
            for field, value in updates.items():
                if field.startswith('_'):  # Skip internal fields
                    continue
                if value and value.strip():
                    set_parts.append(f"{field} = ?")
                    values.append(value.strip())

            if set_parts:
                query = f"UPDATE agencies SET {', '.join(set_parts)} WHERE id = ?"
                values.append(agency_id)

                cursor.execute(query, values)
                conn.commit()

                # Add enrichment note to additional_info
                enrichment_note = f" | Enriched inactive agency data via Gemini search on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                cursor.execute('''
                    UPDATE agencies
                    SET additional_info = COALESCE(additional_info, '') || ?
                    WHERE id = ?
                ''', (enrichment_note, agency_id))
                conn.commit()

                logging.info(f"✅ Updated agency {agency_id} with: {list(updates.keys())}")
                return True

            conn.close()
            return False

        except Exception as e:
            logging.error(f"Error updating agency {agency_id}: {e}")
            return False

    def run_enrichment(self, max_agencies=None, dry_run=False):
        """Run the enrichment process for inactive agencies"""
        print("🔍 Starting enrichment of inactive agencies with name and address data...")
        print("=" * 70)

        # Get inactive agencies
        inactive_agencies = self.get_inactive_agencies_with_data()

        if not inactive_agencies:
            print("✅ No inactive agencies found with name and address data")
            return 0

        if max_agencies:
            inactive_agencies = inactive_agencies[:max_agencies]

        print(f"📋 Found {len(inactive_agencies)} inactive agencies to enrich")
        logging.info(f"Found {len(inactive_agencies)} inactive agencies to enrich")

        enriched_count = 0
        total_processed = 0

        for agency in inactive_agencies:
            print(f"\n🔎 [{total_processed + 1}/{len(inactive_agencies)}] Processing: {agency['name']}")
            logging.info(f"Processing agency: {agency['name']} (ID: {agency['id']})")

            # Get enrichment data
            updates = self.enrich_agency_info(agency)

            if updates:
                print(f"   📝 Found updates: {', '.join([k for k in updates.keys() if not k.startswith('_')])}")

                if not dry_run:
                    if self.update_agency_in_db(agency['id'], updates):
                        enriched_count += 1
                        print("   ✅ Database updated")
                    else:
                        print("   ❌ Failed to update database")
                else:
                    print("   🔍 Dry run - would update database")
                    enriched_count += 1  # Count as enriched for dry run
            else:
                print("   ⚠️ No useful information found")

            total_processed += 1

            # Rate limiting
            if total_processed < len(inactive_agencies):
                time.sleep(3)

        print(f"\n🎉 Enrichment complete!")
        print(f"📊 Processed: {total_processed} agencies")
        print(f"✅ Enriched: {enriched_count} agencies")
        print(f"📈 Success rate: {enriched_count/total_processed*100:.1f}%" if total_processed > 0 else "0%")

        logging.info(f"Enrichment complete. Processed: {total_processed}, Enriched: {enriched_count}")

        return enriched_count

def main():
    import argparse

    parser = argparse.ArgumentParser(description='Enrich inactive agencies with additional information')
    parser.add_argument('--max-agencies', type=int, help='Maximum number of agencies to process')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without making changes')
    parser.add_argument('--db-path', default='agencies.db', help='Path to the agencies database')

    args = parser.parse_args()

    enricher = InactiveAgencyEnricher(db_path=args.db_path)

    if args.dry_run:
        print("🔍 DRY RUN MODE - No database changes will be made")
        print("=" * 50)

    enriched_count = enricher.run_enrichment(
        max_agencies=args.max_agencies,
        dry_run=args.dry_run
    )

    print(f"\n🏁 Script completed. Enriched {enriched_count} agencies.")

if __name__ == '__main__':
    main()
