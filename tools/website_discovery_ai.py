#!/usr/bin/env python3
"""
AI-Powered Website Discovery for Missing Agency Websites

Uses Google Gemini AI to search for websites of agencies that don't have them.
Integrates with the enhanced website validator for comprehensive discovery.
"""

import sqlite3
import logging
import time
import json
from typing import List, Dict, Optional

# Import Gemini integration
try:
    from gemini_agency_finder import GeminiAgencyFinder
except ImportError:
    # Fallback if not available
    class GeminiAgencyFinder:
        def __init__(self):
            self.api_key = None
        def run_gemini_prompt(self, prompt, use_web_search=True):
            return "AI search not available - Gemini API key not configured"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class AIWebsiteDiscoverer:
    def __init__(self):
        self.finder = GeminiAgencyFinder()
        self.max_prompts_per_agency = 2  # Limit API calls per agency

    def discover_website_for_agency(self, agency_name: str, city: str = None, country: str = "Poland") -> List[Dict]:
        """
        Use AI to discover website for a specific agency
        Returns list of potential website matches with confidence scores
        """
        if not agency_name or not agency_name.strip():
            return []

        discovered_websites = []

        # Create targeted search prompts
        prompts = self._generate_search_prompts(agency_name, city, country)

        for prompt in prompts[:self.max_prompts_per_agency]:
            logging.info(f"Searching for website: {agency_name} in {city or 'unknown city'}")

            response = self.finder.run_gemini_prompt(prompt, use_web_search=True)
            if response:
                websites = self._extract_websites_from_response(response, agency_name)
                discovered_websites.extend(websites)

                # Rate limiting
                time.sleep(2)

        # Remove duplicates and rank by confidence
        unique_websites = self._deduplicate_and_rank(agency_name, discovered_websites)

        logging.info(f"Discovered {len(unique_websites)} potential websites for {agency_name}")
        return unique_websites

    def _generate_search_prompts(self, agency_name: str, city: str = None, country: str = "Poland") -> List[str]:
        """Generate AI search prompts for finding agency websites"""
        prompts = []

        # Basic search
        base_prompt = f"""Find the official website for the real estate agency "{agency_name}"{' in ' + city if city else ''}, {country}.

Return ONLY a JSON array with this exact format:
[{{"url": "https://example.com", "confidence": 0.9, "reason": "official website found in business directory", "source": "company registry"}}]

If no website is found, return an empty array []. Do not include explanations."""

        prompts.append(base_prompt)

        # Alternative search with more context
        if city:
            alt_prompt = f"""Search for the website of "{agency_name}" real estate agency located in {city}, {country}.

Look for:
- Official company website
- Business directory listings
- Social media profiles (as fallback)
- Property portal profiles

Return ONLY a JSON array:
[{{"url": "https://example.com", "confidence": 0.8, "reason": "found in local business directory", "source": "yellow pages"}}]

Empty array [] if nothing found."""

            prompts.append(alt_prompt)

        # Search for Polish real estate agencies specifically
        if "nieruchomości" in agency_name.lower() or country == "Poland":
            pl_prompt = f"""Find the website for Polish real estate agency "{agency_name}"{' in ' + city if city else ''}.

Search Polish business directories, real estate portals, and company registries.

Return ONLY JSON array:
[{{"url": "https://example.pl", "confidence": 0.95, "reason": "official Polish company website", "source": "KRS registry"}}]"""

            prompts.append(pl_prompt)

        return prompts

    def _extract_websites_from_response(self, response: str, agency_name: str) -> List[Dict]:
        """Extract website information from AI response"""
        websites = []

        try:
            # Try to parse as JSON first
            data = json.loads(response.strip())
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and 'url' in item:
                        websites.append({
                            'url': item['url'],
                            'confidence': item.get('confidence', 0.5),
                            'reason': item.get('reason', 'AI discovered'),
                            'source': item.get('source', 'AI search'),
                            'agency_name': agency_name
                        })

        except json.JSONDecodeError:
            # Fallback: extract URLs from text response
            import re
            url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
            found_urls = re.findall(url_pattern, response)

            for url in found_urls[:3]:  # Limit to first 3 URLs
                websites.append({
                    'url': url,
                    'confidence': 0.6,  # Lower confidence for text extraction
                    'reason': 'extracted from AI response text',
                    'source': 'AI text parsing',
                    'agency_name': agency_name
                })

        return websites

    def _deduplicate_and_rank(self, agency_name: str, websites: List[Dict]) -> List[Dict]:
        """Remove duplicates and rank websites by relevance and confidence"""
        seen_urls = set()
        unique_websites = []

        # Sort by confidence first
        websites.sort(key=lambda x: x.get('confidence', 0), reverse=True)

        for website in websites:
            url = website['url'].lower().strip()

            # Skip if already seen
            if url in seen_urls:
                continue

            # Basic validation
            if not url.startswith(('http://', 'https://')):
                continue

            # Boost confidence for official-looking domains
            domain_indicators = [
                agency_name.lower().replace(' ', '').replace('nieruchomości', '').replace('agency', ''),
                agency_name.lower().split()[0] if agency_name.split() else '',
                'nieruchomosci', 'property', 'realestate', 'immobilien'
            ]

            url_lower = url.lower()
            for indicator in domain_indicators:
                if indicator and len(indicator) > 2 and indicator in url_lower:
                    website['confidence'] = min(1.0, website.get('confidence', 0.5) + 0.2)
                    break

            seen_urls.add(url)
            unique_websites.append(website)

        return unique_websites[:5]  # Return top 5 most relevant

def update_agency_with_discovered_website(agency_id: int, discovered_websites: List[Dict]):
    """Update agency record with AI-discovered websites"""
    if not discovered_websites:
        return False

    try:
        conn = sqlite3.connect('agencies.db')
        cursor = conn.cursor()

        # Take the highest confidence website as primary
        best_website = discovered_websites[0]

        # Prepare alternatives (all discovered websites)
        alternatives = []
        for i, website in enumerate(discovered_websites):
            alternatives.append({
                'url': website['url'],
                'confidence': website.get('confidence', 0.5),
                'reason': website.get('reason', 'AI discovered'),
                'source': website.get('source', 'AI search'),
                'priority': i + 1
            })

        # Update database
        cursor.execute('''
            UPDATE agencies
            SET website = ?,
                website_status = 'ai_discovered',
                alternative_urls = ?,
                url_validation_date = datetime('now'),
                additional_info = additional_info || ?
            WHERE id = ?
        ''', (
            best_website['url'],
            json.dumps(alternatives),
            f" | Website discovered via AI search on {time.strftime('%Y-%m-%d %H:%M:%S')}",
            agency_id
        ))

        conn.commit()
        conn.close()
        return True

    except Exception as e:
        logging.error(f"Error updating agency with discovered website: {e}")
        return False

def main():
    """Main function to run AI-powered website discovery"""
    logging.info("Starting AI-powered website discovery...")

    discoverer = AIWebsiteDiscoverer()

    try:
        conn = sqlite3.connect('agencies.db')
        cursor = conn.cursor()

        # Get agencies with missing websites (including those without polish_city)
        cursor.execute('''
            SELECT id, name, polish_city
            FROM agencies
            WHERE (website IS NULL OR website = '')
            AND type != 'undefined'
            ORDER BY id
        ''')

        agencies = cursor.fetchall()
        conn.close()

        if not agencies:
            print("✅ No agencies found with missing websites")
            return

        logging.info(f"Found {len(agencies)} agencies with missing websites")

        discovered_count = 0
        processed_count = 0

        for agency_id, name, city in agencies[:10]:  # Limit to 10 for testing
            logging.info(f"Discovering website for: {name}")

            discovered_websites = discoverer.discover_website_for_agency(name, city)

            if discovered_websites:
                if update_agency_with_discovered_website(agency_id, discovered_websites):
                    discovered_count += 1
                    logging.info(f"  ✅ Updated {name} with {len(discovered_websites)} discovered websites")
                else:
                    logging.error(f"  ❌ Failed to update database for {name}")
            else:
                logging.info(f"  ⚠️ No websites discovered for {name}")

            processed_count += 1

            # Rate limiting between agencies
            time.sleep(3)

        logging.info(f"AI discovery complete: {discovered_count}/{processed_count} agencies updated with discovered websites")

        # Show summary
        print("\n✅ AI Website Discovery Complete!")
        print(f"   📊 Agencies processed: {processed_count}")
        print(f"   📊 Websites discovered: {discovered_count}")

    except Exception as e:
        logging.error(f"Error during AI website discovery: {e}")
        print(f"❌ Error: {e}")

if __name__ == '__main__':
    main()
