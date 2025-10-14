#!/usr/bin/env python3
"""
AI-Powered Website Recovery Tool
Uses Gemini AI to find correct websites for agencies with broken or missing URLs
"""

import sqlite3
import json
import time
import os
from datetime import datetime
from google import genai
from dotenv import load_dotenv

load_dotenv()

class WebsiteRecoveryAI:
    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv('GOOGLE_API_KEY')
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY environment variable not set")

        self.client = genai.Client(api_key=self.api_key)
        self.model = "gemini-2.5-flash"

        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 1.0  # seconds between requests

    def _rate_limit(self):
        """Ensure we don't exceed API rate limits"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_request_interval:
            time.sleep(self.min_request_interval - time_since_last)
        self.last_request_time = time.time()

    def search_website_for_agency(self, agency_name, agency_address, current_website=None):
        """
        Use Gemini AI to find the correct website for an agency
        """
        self._rate_limit()

        prompt = f"""Find the correct website for this real estate agency:

Agency Name: {agency_name}
Address: {agency_address}
"""

        if current_website:
            prompt += f"Current Website (broken): {current_website}\n"

        prompt += """
Return ONLY a JSON object with this exact format:
{
  "website": "https://correct-website.com",
  "confidence": "high|medium|low",
  "reasoning": "Brief explanation of how you found this website"
}

If you cannot find a working website, return:
{
  "website": null,
  "confidence": "none",
  "reasoning": "No working website found"
}

Do not include explanations outside the JSON object."""

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt
            )

            # Extract JSON from response
            response_text = response.text.strip()

            # Clean up response (remove markdown code blocks if present)
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.startswith('```'):
                response_text = response_text[3:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]

            response_text = response_text.strip()

            try:
                result = json.loads(response_text)
                return result
            except json.JSONDecodeError as e:
                print(f"❌ JSON parsing error for {agency_name}: {e}")
                print(f"Raw response: {response_text}")
                return {
                    "website": None,
                    "confidence": "error",
                    "reasoning": f"JSON parsing failed: {str(e)}"
                }

        except Exception as e:
            print(f"❌ API error for {agency_name}: {e}")
            return {
                "website": None,
                "confidence": "error",
                "reasoning": f"API error: {str(e)}"
            }

def main():
    print("🔍 AI-Powered Website Recovery Tool")
    print("=" * 50)

    try:
        recovery_ai = WebsiteRecoveryAI()
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        return

    # Connect to database
    conn = sqlite3.connect('agencies.db')
    cursor = conn.cursor()

    # Find agencies needing website recovery
    cursor.execute("""
        SELECT id, name, address, website, website_status
        FROM agencies
        WHERE website_status IN ('inactive', 'connection_error', 'timeout', 'ssl_error', 'http_405', 'http_403', 'http_400', 'upgraded_to_https')
        AND name IS NOT NULL AND name != ''
        ORDER BY name
    """)

    agencies_to_check = cursor.fetchall()

    if not agencies_to_check:
        print("✅ No agencies need website recovery")
        conn.close()
        return

    print(f"📋 Found {len(agencies_to_check)} agencies needing website recovery")

    # Process agencies
    updated_count = 0
    error_count = 0

    for agency_id, name, address, current_website, status in agencies_to_check:
        print(f"\n🔍 Processing: {name}")

        # Search for correct website
        result = recovery_ai.search_website_for_agency(name, address, current_website)

        if result['website'] and result['confidence'] in ['high', 'medium']:
            # Found a potential website
            new_website = result['website']
            confidence = result['confidence']

            print(f"   ✅ Found: {new_website} (confidence: {confidence})")

            # Update database
            update_note = f" | Website recovered via AI search on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (confidence: {confidence}, reasoning: {result['reasoning']})"

            cursor.execute("""
                UPDATE agencies
                SET website = ?,
                    website_status = 'recovered',
                    additional_info = COALESCE(additional_info, '') || ?
                WHERE id = ?
            """, (new_website, update_note, agency_id))

            updated_count += 1

        elif result['confidence'] == 'low':
            print(f"   ⚠️  Low confidence result: {result['website']} - skipping")

            # Mark as low_confidence
            cursor.execute("""
                UPDATE agencies
                SET website_status = 'low_confidence',
                    additional_info = COALESCE(additional_info, '') || ?
                WHERE id = ?
            """, (f" | Low confidence website suggestion: {result['website']} on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", agency_id))

        else:
            print(f"   ❌ No website found: {result['reasoning']}")

            # Mark as no_website_found
            cursor.execute("""
                UPDATE agencies
                SET website_status = 'no_website_found',
                    additional_info = COALESCE(additional_info, '') || ?
                WHERE id = ?
            """, (f" | No website found via AI search on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ({result['reasoning']})", agency_id))

            error_count += 1

        # Commit every 10 agencies to avoid losing progress
        if (updated_count + error_count) % 10 == 0:
            conn.commit()
            print(f"   💾 Progress saved: {updated_count + error_count}/{len(agencies_to_check)} processed")

    # Final commit
    conn.commit()
    conn.close()

    print("\n🎉 Website recovery complete!")
    print(f"   Websites recovered: {updated_count}")
    print(f"   No websites found: {error_count}")
    print(f"   Total processed: {updated_count + error_count}")

    if updated_count > 0:
        print("\n💡 Next steps:")
        print("   1. Run website validation: python tools/enhanced_website_validator.py")
        print("   2. Update the agencies.json export")
        print("   3. Refresh the web interface to see the changes")

if __name__ == '__main__':
    main()
