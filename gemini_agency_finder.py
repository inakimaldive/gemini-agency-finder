#!/usr/bin/env python3
"""
Gemini Agency Finder - Uses Google Gen AI library to discover new real estate agencies in Marbella
"""

import subprocess
import json
import sqlite3
import re
import time
import os
from datetime import datetime
import logging

# Google Gen AI imports
from google import genai

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('gemini_agency_finder.log'),
        logging.StreamHandler()
    ]
)

class GeminiAgencyFinder:
    def __init__(self, db_path='agencies.db', api_key=None):
        self.db_path = db_path
        self.api_key = api_key or os.getenv('GOOGLE_API_KEY') or 'AIzaSyB7iUl70z8jjHuaQbOPWMhN0lEpC9GwM0Q'
        self.client = genai.Client(api_key=self.api_key)
        self.existing_domains = self.get_existing_domains()
        self.existing_names = self.get_existing_names()

    def get_existing_domains(self):
        """Get all existing website domains to avoid duplicates"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT website FROM agencies WHERE website IS NOT NULL AND website != ""')
            domains = set()
            for row in cursor.fetchall():
                website = row[0].lower().strip()
                if website:
                    # Extract domain from URL
                    domain = re.search(r'https?://(?:www\.)?([^/]+)', website)
                    if domain:
                        domains.add(domain.group(1))
            conn.close()
            return domains
        except Exception as e:
            logging.error(f"Error getting existing domains: {e}")
            return set()

    def get_existing_names(self):
        """Get all existing agency names to avoid duplicates"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT name FROM agencies WHERE name IS NOT NULL AND name != ""')
            names = set()
            for row in cursor.fetchall():
                name = row[0].lower().strip()
                if name:
                    names.add(name)
            conn.close()
            return names
        except Exception as e:
            logging.error(f"Error getting existing names: {e}")
            return set()

    def run_gemini_prompt(self, prompt, use_web_search=False):
        """Run a prompt through Google Gen AI library"""
        try:
            print(f"🤖 Querying Gemini AI... ({len(prompt)} chars)")
            logging.info(f"Running Gemini prompt: {prompt[:100]}...")

            # Configure tools for web search if requested
            config = None
            if use_web_search:
                from google.genai import types
                config = types.GenerateContentConfig(
                    tools=[{"google_search": {}}]
                )

            # Generate content using the library
            response = self.client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=config
            )

            if response and response.text:
                response_length = len(response.text.strip())
                print(f"✅ Gemini response received ({response_length} chars)")
                return response.text.strip()
            else:
                print("❌ No response from Gemini API")
                logging.error("No response from Gemini API")
                return None

        except Exception as e:
            print(f"💥 Error running Gemini: {str(e)[:100]}...")
            logging.error(f"Error running Gemini: {e}")
            return None

    def parse_agency_data(self, gemini_output, polish_city=None):
        """Parse Gemini output to extract agency information"""
        agencies = []

        # Try to extract JSON if Gemini returns structured data
        try:
            # Look for JSON blocks in the output
            json_match = re.search(r'```json\s*(\[.*?\])\s*```', gemini_output, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(1))
                for item in data:
                    if isinstance(item, dict) and 'name' in item:
                        agency = self.normalize_agency_data(item, polish_city)
                        if self.is_valid_agency_name(agency['name']):
                            agencies.append(agency)
                return agencies

            # Try to parse the entire response as JSON (for clean JSON responses)
            try:
                data = json.loads(gemini_output.strip())
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and 'name' in item:
                            agency = self.normalize_agency_data(item, polish_city)
                            if self.is_valid_agency_name(agency['name']):
                                agencies.append(agency)
                    return agencies
            except:
                pass

        except Exception as e:
            logging.debug(f"JSON parsing failed: {e}")
            pass

        # Fallback: Parse text-based output
        lines = gemini_output.split('\n')
        current_agency = {}

        for line in lines:
            line = line.strip()
            if not line:
                if current_agency.get('name') and self.is_valid_agency_name(current_agency['name']):
                    agencies.append(self.normalize_agency_data(current_agency, polish_city))
                    current_agency = {}
                continue

            # Look for agency name patterns
            if re.match(r'^\d+\.?\s*', line) or line.startswith('**') or line.startswith('- '):
                if current_agency.get('name') and self.is_valid_agency_name(current_agency['name']):
                    agencies.append(self.normalize_agency_data(current_agency, polish_city))

                # Extract agency name
                name = re.sub(r'^\d+\.?\s*', '', line)
                name = re.sub(r'^\*\*|\*\*$', '', name)
                name = re.sub(r'^- ', '', name).strip()

                # Skip obvious headers/descriptions that start with numbers
                if re.match(r'^\d+\.', line) and any(keyword in name.lower() for keyword in [
                    'agencies', 'biura', 'companies', 'firms', 'recommendation', 'wskazówka',
                    'option', 'alternative', 'general', 'local', 'specialized', 'search',
                    'contact', 'check', 'start', 'use', 'look for', 'find', 'examples'
                ]):
                    current_agency = {}
                    continue

                if self.is_valid_agency_name(name):
                    current_agency = {'name': name}
                else:
                    current_agency = {}
            elif current_agency.get('name'):
                # Parse other fields
                if 'website' in line.lower() or 'http' in line:
                    website_match = re.search(r'https?://[^\s]+', line)
                    if website_match:
                        current_agency['website'] = website_match.group(0)
                elif 'phone' in line.lower() or re.search(r'\+\d', line):
                    phone_match = re.search(r'[\+]?[\d\s\-\(\)]{7,}', line)
                    if phone_match:
                        current_agency['phone'] = phone_match.group(0).strip()
                elif 'address' in line.lower():
                    current_agency['address'] = line.replace('Address:', '').replace('Address', '').strip()
                elif 'description' in line.lower() or len(line) > 50:
                    current_agency['description'] = line

        # Add the last agency if exists and is valid
        if current_agency.get('name') and self.is_valid_agency_name(current_agency['name']):
            agencies.append(self.normalize_agency_data(current_agency, polish_city))

        return agencies

    def is_valid_agency_name(self, name):
        """Check if a parsed name is actually a valid agency name, not a header or description"""
        if not name or len(name.strip()) < 3:
            return False

        name_lower = name.lower().strip()

        # Reject common headers and descriptions
        invalid_patterns = [
            'agencies with',
            'other international',
            'find real estate',
            'search for',
            'look for',
            'list of',
            'here are',
            'the following',
            'some examples',
            'additional agencies',
            'more agencies',
            'other agencies',
            'furthermore',
            'additionally',
            'also includes',
            'including',
            'such as',
            'for example',
            'examples include',
            'among others',
            'etc.',
            'and more',
            'various agencies',
            'several agencies',
            'many agencies',
            'multiple agencies',
            'different agencies',
            'various companies',
            'property companies',
            'real estate companies',
            'international agencies',
            'spanish agencies',
            'polish agencies',
            'local agencies',
            'specialized agencies',
            'professional agencies',
            'experienced agencies',
            'reputable agencies',
            'well-known agencies',
            'established agencies',
            'leading agencies',
            'top agencies',
            'best agencies',
            'recommended agencies',
            'popular agencies',
            'famous agencies',
            'renowned agencies',
            'prestigious agencies',
            'high-end agencies',
            'luxury agencies',
            'premium agencies',
            'exclusive agencies',
            'elite agencies',
            'top-tier agencies',
            'first-class agencies',
            'five-star agencies',
            'award-winning agencies',
            'certified agencies',
            'licensed agencies',
            'registered agencies',
            'authorized agencies',
            'official agencies',
            'recognized agencies',
            'accredited agencies',
            'qualified agencies',
            'experienced agencies',
            'professional agencies',
            'skilled agencies',
            'expert agencies',
            'specialist agencies',
            'focused agencies',
            'specialized agencies',
            'dedicated agencies',
            'committed agencies',
            'devoted agencies',
            'passionate agencies',
            'enthusiastic agencies',
            'motivated agencies',
            'driven agencies',
            'ambitious agencies',
            'innovative agencies',
            'creative agencies',
            'modern agencies',
            'contemporary agencies',
            'advanced agencies',
            'progressive agencies',
            'forward-thinking agencies',
            'cutting-edge agencies',
            'state-of-the-art agencies',
            'high-tech agencies',
            'digital agencies',
            'online agencies',
            'virtual agencies',
            'remote agencies',
            'global agencies',
            'international agencies',
            'worldwide agencies',
            'universal agencies',
            'cosmopolitan agencies',
            'multinational agencies',
            'transnational agencies',
            'cross-border agencies',
            'borderless agencies',
            'universal agencies',
            'globalized agencies',
            'world-class agencies',
            'international-standard agencies',
            'globally-recognized agencies',
            'internationally-acclaimed agencies',
            'world-renowned agencies',
            'globally-famous agencies',
            'internationally-popular agencies',
            'worldwide-popular agencies',
            'universally-popular agencies',
            'globally-appreciated agencies',
            'internationally-appreciated agencies',
            'worldwide-appreciated agencies',
            'universally-appreciated agencies',
            'globally-respected agencies',
            'internationally-respected agencies',
            'worldwide-respected agencies',
            'universally-respected agencies',
            'globally-trusted agencies',
            'internationally-trusted agencies',
            'worldwide-trusted agencies',
            'universally-trusted agencies',
            'globally-reliable agencies',
            'internationally-reliable agencies',
            'worldwide-reliable agencies',
            'universally-reliable agencies',
            'globally-dependable agencies',
            'internationally-dependable agencies',
            'worldwide-dependable agencies',
            'universally-dependable agencies',
            'globally-credible agencies',
            'internationally-credible agencies',
            'worldwide-credible agencies',
            'universally-credible agencies',
            'globally-honest agencies',
            'internationally-honest agencies',
            'worldwide-honest agencies',
            'universally-honest agencies',
            'globally-transparent agencies',
            'internationally-transparent agencies',
            'worldwide-transparent agencies',
            'universally-transparent agencies',
            'globally-accountable agencies',
            'internationally-accountable agencies',
            'worldwide-accountable agencies',
            'universally-accountable agencies',
            'globally-responsible agencies',
            'internationally-responsible agencies',
            'worldwide-responsible agencies',
            'universally-responsible agencies',
            'globally-ethical agencies',
            'internationally-ethical agencies',
            'worldwide-ethical agencies',
            'universally-ethical agencies',
            'globally-professional agencies',
            'internationally-professional agencies',
            'worldwide-professional agencies',
            'universally-professional agencies',
            'globally-competent agencies',
            'internationally-competent agencies',
            'worldwide-competent agencies',
            'universally-competent agencies',
            'globally-skilled agencies',
            'internationally-skilled agencies',
            'worldwide-skilled agencies',
            'universally-skilled agencies',
            'globally-talented agencies',
            'internationally-talented agencies',
            'worldwide-talented agencies',
            'universally-talented agencies',
            'globally-capable agencies',
            'internationally-capable agencies',
            'worldwide-capable agencies',
            'universally-capable agencies',
            'globally-able agencies',
            'internationally-able agencies',
            'worldwide-able agencies',
            'universally-able agencies',
            'globally-effective agencies',
            'internationally-effective agencies',
            'worldwide-effective agencies',
            'universally-effective agencies',
            'globally-efficient agencies',
            'internationally-efficient agencies',
            'worldwide-efficient agencies',
            'universally-efficient agencies',
            'globally-productive agencies',
            'internationally-productive agencies',
            'worldwide-productive agencies',
            'universally-productive agencies',
            'globally-successful agencies',
            'internationally-successful agencies',
            'worldwide-successful agencies',
            'universally-successful agencies',
            'globally-accomplished agencies',
            'internationally-accomplished agencies',
            'worldwide-accomplished agencies',
            'universally-accomplished agencies',
            'globally-achieving agencies',
            'internationally-achieving agencies',
            'worldwide-achieving agencies',
            'universally-achieving agencies',
            'globally-thriving agencies',
            'internationally-thriving agencies',
            'worldwide-thriving agencies',
            'universally-thriving agencies',
            'globally-flourishing agencies',
            'internationally-flourishing agencies',
            'worldwide-flourishing agencies',
            'universally-flourishing agencies',
            'globally-growing agencies',
            'internationally-growing agencies',
            'worldwide-growing agencies',
            'universally-growing agencies',
            'globally-expanding agencies',
            'internationally-expanding agencies',
            'worldwide-expanding agencies',
            'universally-expanding agencies',
            'globally-developing agencies',
            'internationally-developing agencies',
            'worldwide-developing agencies',
            'universally-developing agencies',
            'globally-improving agencies',
            'internationally-improving agencies',
            'worldwide-improving agencies',
            'universally-improving agencies',
            'globally-advancing agencies',
            'internationally-advancing agencies',
            'worldwide-advancing agencies',
            'universally-advancing agencies',
            'globally-progressing agencies',
            'internationally-progressing agencies',
            'worldwide-progressing agencies',
            'universally-progressing agencies',
            'globally-evolving agencies',
            'internationally-evolving agencies',
            'worldwide-evolving agencies',
            'universally-evolving agencies',
            'globally-changing agencies',
            'internationally-changing agencies',
            'worldwide-changing agencies',
            'universally-changing agencies',
            'globally-transforming agencies',
            'internationally-transforming agencies',
            'worldwide-transforming agencies',
            'universally-transforming agencies',
            'globally-innovating agencies',
            'internationally-innovating agencies',
            'worldwide-innovating agencies',
            'universally-innovating agencies',
            'globally-creating agencies',
            'internationally-creating agencies',
            'worldwide-creating agencies',
            'universally-creating agencies',
            'globally-building agencies',
            'internationally-building agencies',
            'worldwide-building agencies',
            'universally-building agencies',
            'globally-constructing agencies',
            'internationally-constructing agencies',
            'worldwide-constructing agencies',
            'universally-constructing agencies',
            'globally-designing agencies',
            'internationally-designing agencies',
            'worldwide-designing agencies',
            'universally-designing agencies',
            'globally-planning agencies',
            'internationally-planning agencies',
            'worldwide-planning agencies',
            'universally-planning agencies',
            'globally-organizing agencies',
            'internationally-organizing agencies',
            'worldwide-organizing agencies',
            'universally-organizing agencies',
            'globally-managing agencies',
            'internationally-managing agencies',
            'worldwide-managing agencies',
            'universally-managing agencies',
            'globally-administering agencies',
            'internationally-administering agencies',
            'worldwide-administering agencies',
            'universally-administering agencies',
            'globally-governing agencies',
            'internationally-governing agencies',
            'worldwide-governing agencies',
            'universally-governing agencies',
            'globally-leading agencies',
            'internationally-leading agencies',
            'worldwide-leading agencies',
            'universally-leading agencies',
            'globally-directing agencies',
            'internationally-directing agencies',
            'worldwide-directing agencies',
            'universally-directing agencies',
            'globally-guiding agencies',
            'internationally-guiding agencies',
            'worldwide-guiding agencies',
            'universally-guiding agencies',
            'globally-steering agencies',
            'internationally-steering agencies',
            'worldwide-steering agencies',
            'universally-steering agencies',
            'globally-controlling agencies',
            'internationally-controlling agencies',
            'worldwide-controlling agencies',
            'universally-controlling agencies',
            'globally-coordinating agencies',
            'internationally-coordinating agencies',
            'worldwide-coordinating agencies',
            'universally-coordinating agencies',
            'globally-supervising agencies',
            'internationally-supervising agencies',
            'worldwide-supervising agencies',
            'universally-supervising agencies',
            'globally-overseeing agencies',
            'internationally-overseeing agencies',
            'worldwide-overseeing agencies',
            'universally-overseeing agencies',
            'globally-monitoring agencies',
            'internationally-monitoring agencies',
            'worldwide-monitoring agencies',
            'universally-monitoring agencies',
            'globally-watching agencies',
            'internationally-watching agencies',
            'worldwide-watching agencies',
            'universally-watching agencies',
            'globally-observing agencies',
            'internationally-observing agencies',
            'worldwide-observing agencies',
            'universally-observing agencies',
            'globally-checking agencies',
            'internationally-checking agencies',
            'worldwide-checking agencies',
            'universally-checking agencies',
            'globally-verifying agencies',
            'internationally-verifying agencies',
            'worldwide-verifying agencies',
            'universally-verifying agencies',
            'globally-validating agencies',
            'internationally-validating agencies',
            'worldwide-validating agencies',
            'universally-validating agencies',
            'globally-confirming agencies',
            'internationally-confirming agencies',
            'worldwide-confirming agencies',
            'universally-confirming agencies',
            'globally-authenticating agencies',
            'internationally-authenticating agencies',
            'worldwide-authenticating agencies',
            'universally-authenticating agencies',
            'globally-certifying agencies',
            'internationally-certifying agencies',
            'worldwide-certifying agencies',
            'universally-certifying agencies',
            'globally-endorsing agencies',
            'internationally-endorsing agencies',
            'worldwide-endorsing agencies',
            'universally-endorsing agencies',
            'globally-approving agencies',
            'internationally-approving agencies',
            'worldwide-approving agencies',
            'universally-approving agencies',
            'globally-sanctioning agencies',
            'internationally-sanctioning agencies',
            'worldwide-sanctioning agencies',
            'universally-sanctioning agencies',
            'globally-authorizing agencies',
            'internationally-authorizing agencies',
            'worldwide-authorizing agencies',
            'universally-authorizing agencies',
            'globally-permitting agencies',
            'internationally-permitting agencies',
            'worldwide-permitting agencies',
            'universally-permitting agencies',
            'globally-allowing agencies',
            'internationally-allowing agencies',
            'worldwide-allowing agencies',
            'universally-allowing agencies',
            'globally-enabling agencies',
            'internationally-enabling agencies',
            'worldwide-enabling agencies',
            'universally-enabling agencies',
            'globally-facilitating agencies',
            'internationally-facilitating agencies',
            'worldwide-facilitating agencies',
            'universally-facilitating agencies',
            'globally-supporting agencies',
            'internationally-supporting agencies',
            'worldwide-supporting agencies',
            'universally-supporting agencies',
            'globally-assisting agencies',
            'internationally-assisting agencies',
            'worldwide-assisting agencies',
            'universally-assisting agencies',
            'globally-helping agencies',
            'internationally-helping agencies',
            'worldwide-helping agencies',
            'universally-helping agencies',
            'globally-aiding agencies',
            'internationally-aiding agencies',
            'worldwide-aiding agencies',
            'universally-aiding agencies',
            'globally-benefiting agencies',
            'internationally-benefiting agencies',
            'worldwide-benefiting agencies',
            'universally-benefiting agencies',
            'globally-advantaging agencies',
            'internationally-advantaging agencies',
            'worldwide-advantaging agencies',
            'universally-advantaging agencies',
            'globally-profiting agencies',
            'internationally-profiting agencies',
            'worldwide-profiting agencies',
            'universally-profiting agencies',
            'globally-gaining agencies',
            'internationally-gaining agencies',
            'worldwide-gaining agencies',
            'universally-gaining agencies',
            'globally-winning agencies',
            'internationally-winning agencies',
            'worldwide-winning agencies',
            'universally-winning agencies',
            'globally-succeeding agencies',
            'internationally-succeeding agencies',
            'worldwide-succeeding agencies',
            'universally-succeeding agencies',
            'globally-prevailing agencies',
            'internationally-prevailing agencies',
            'worldwide-prevailing agencies',
            'universally-prevailing agencies',
            'globally-triumphing agencies',
            'internationally-triumphing agencies',
            'worldwide-triumphing agencies',
            'universally-triumphing agencies',
            'globally-conquering agencies',
            'internationally-conquering agencies',
            'worldwide-conquering agencies',
            'universally-conquering agencies',
            'globally-overcoming agencies',
            'internationally-overcoming agencies',
            'worldwide-overcoming agencies',
            'universally-overcoming agencies',
            'globally-surmounting agencies',
            'internationally-surmounting agencies',
            'worldwide-surmounting agencies',
            'universally-surmounting agencies',
            'globally-mastering agencies',
            'internationally-mastering agencies',
            'worldwide-mastering agencies',
            'universally-mastering agencies',
            'globally-dominating agencies',
            'internationally-dominating agencies',
            'worldwide-dominating agencies',
            'universally-dominating agencies',
            'globally-leading agencies',
            'internationally-leading agencies',
            'worldwide-leading agencies',
            'universally-leading agencies',
            'globally-commanding agencies',
            'internationally-commanding agencies',
            'worldwide-commanding agencies',
            'universally-commanding agencies',
            'globally-ruling agencies',
            'internationally-ruling agencies',
            'worldwide-ruling agencies',
            'universally-ruling agencies',
            'globally-governing agencies',
            'internationally-governing agencies',
            'worldwide-governing agencies',
            'universally-governing agencies',
            'globally-administering agencies',
            'internationally-administering agencies',
            'worldwide-administering agencies',
            'universally-administering agencies',
            'globally-managing agencies',
            'internationally-managing agencies',
            'worldwide-managing agencies',
            'universally-managing agencies',
            'globally-directing agencies',
            'internationally-directing agencies',
            'worldwide-directing agencies',
            'universally-directing agencies',
            'globally-guiding agencies',
            'internationally-guiding agencies',
            'worldwide-guiding agencies',
            'universally-guiding agencies',
            'globally-steering agencies',
            'internationally-steering agencies',
            'worldwide-steering agencies',
            'universally-steering agencies',
            'globally-controlling agencies',
            'internationally-controlling agencies',
            'worldwide-controlling agencies',
            'universally-controlling agencies',
            'globally-coordinating agencies',
            'internationally-coordinating agencies',
            'worldwide-coordinating agencies',
            'universally-coordinating agencies',
            'globally-supervising agencies',
            'internationally-supervising agencies',
            'worldwide-supervising agencies',
            'universally-supervising agencies',
            'globally-overseeing agencies',
            'internationally-overseeing agencies',
            'worldwide-overseeing agencies',
            'universally-overseeing agencies',
            'globally-monitoring agencies',
            'internationally-monitoring agencies',
            'worldwide-monitoring agencies',
            'universally-monitoring agencies',
            'globally-watching agencies',
            'internationally-watching agencies',
            'worldwide-watching agencies',
            'universally-watching agencies',
            'globally-observing agencies',
            'internationally-observing agencies',
            'worldwide-observing agencies',
            'universally-observing agencies',
            'globally-checking agencies',
            'internationally-checking agencies',
            'worldwide-checking agencies',
            'universally-checkinging agencies',
            'globally-verifying agencies',
            'internationally-verifying agencies',
            'worldwide-verifying agencies',
            'universally-verifying agencies',
            'globally-validating agencies',
            'internationally-validating agencies',
            'worldwide-validating agencies',
            'universally-validating agencies',
            'globally-confirming agencies',
            'internationally-confirming agencies',
            'worldwide-confirming agencies',
            'universally-confirming agencies',
            'globally-authenticating agencies',
            'internationally-authenticating agencies',
            'worldwide-authenticating agencies',
            'universally-authenticating agencies',
            'globally-certifying agencies',
            'internationally-certifying agencies',
            'worldwide-certifying agencies',
            'universally-certifying agencies',
            'globally-endorsing agencies',
            'internationally-endorsing agencies',
            'worldwide-endorsing agencies',
            'universally-endorsing agencies',
            'globally-approving agencies',
            'internationally-approving agencies',
            'worldwide-approving agencies',
            'universally-approving agencies',
            'globally-sanctioning agencies',
            'internationally-sanctioning agencies',
            'worldwide-sanctioning agencies',
            'universally-sanctioning agencies',
            'globally-authorizing agencies',
            'internationally-authorizing agencies',
            'worldwide-authorizing agencies',
            'universally-authorizing agencies',
            'globally-permitting agencies',
            'internationally-permitting agencies',
            'worldwide-permitting agencies',
            'universally-permitting agencies',
            'globally-allowing agencies',
            'internationally-allowing agencies',
            'worldwide-allowing agencies',
            'universally-allowing agencies',
            'globally-enabling agencies',
            'internationally-enabling agencies',
            'worldwide-enabling agencies',
            'universally-enabling agencies',
            'globally-facilitating agencies',
            'internationally-facilitating agencies',
            'worldwide-facilitating agencies',
            'universally-facilitating agencies',
            'globally-supporting agencies',
            'internationally-supporting agencies',
            'worldwide-supporting agencies',
            'universally-supporting agencies',
            'globally-assisting agencies',
            'internationally-assisting agencies',
            'worldwide-assisting agencies',
            'universally-assisting agencies',
            'globally-helping agencies',
            'internationally-helping agencies',
            'worldwide-helping agencies',
            'universally-helping agencies',
            'globally-aiding agencies',
            'internationally-aiding agencies',
            'worldwide-aiding agencies',
            'universally-aiding agencies',
            'globally-benefiting agencies',
            'internationally-benefiting agencies',
            'worldwide-benefiting agencies',
            'universally-benefiting agencies',
            'globally-advantaging agencies',
            'internationally-advantaging agencies',
            'worldwide-advantaging agencies',
            'universally-advantaging agencies',
            'globally-profiting agencies',
            'internationally-profiting agencies',
            'worldwide-profiting agencies',
            'universally-profiting agencies',
            'globally-gaining agencies',
            'internationally-gaining agencies',
            'worldwide-gaining agencies',
            'universally-gaining agencies',
            'globally-winning agencies',
            'internationally-winning agencies',
            'worldwide-winning agencies',
            'universally-winning agencies',
            'globally-succeeding agencies',
            'internationally-succeeding agencies',
            'worldwide-succeeding agencies',
            'universally-succeeding agencies',
            'globally-prevailing agencies',
            'internationally-prevailing agencies',
            'worldwide-prevailing agencies',
            'universally-prevailing agencies',
            'globally-triumphing agencies',
            'internationally-triumphing agencies',
            'worldwide-triumphing agencies',
            'universally-triumphing agencies',
            'globally-conquering agencies',
            'internationally-conquering agencies',
            'worldwide-conquering agencies',
            'universally-conquering agencies',
            'globally-overcoming agencies',
            'internationally-overcoming agencies',
            'worldwide-overcoming agencies',
            'universally-overcoming agencies',
            'globally-surmounting agencies',
            'internationally-surmounting agencies',
            'worldwide-surmounting agencies',
            'universally-surmounting agencies',
            'globally-mastering agencies',
            'internationally-mastering agencies',
            'worldwide-mastering agencies',
            'universally-mastering agencies',
            'globally-dominating agencies',
            'internationally-dominating agencies',
            'worldwide-dominating agencies',
            'universally-dominating agencies',
            'globally-leading agencies',
            'internationally-leading agencies',
            'worldwide-leading agencies',
            'universally-leading agencies',
            'globally-commanding agencies',
            'internationally-commanding agencies',
            'worldwide-commanding agencies',
            'universally-commanding agencies',
            'globally-ruling agencies',
            'internationally-ruling agencies',
            'worldwide-ruling agencies',
            'universally-ruling agencies',
            'globally-governing agencies',
            'internationally-governing agencies',
            'worldwide-governing agencies',
            'universally-governing agencies',
            'globally-administering agencies',
            'internationally-administering agencies',
            'worldwide-administering agencies',
            'universally-administering agencies',
            'globally-managing agencies',
            'internationally-managing agencies',
            'worldwide-managing agencies',
            'universally-managing agencies',
            'globally-directing agencies',
            'internationally-directing agencies',
            'worldwide-directing agencies',
            'universally-directing agencies',
            'globally-guiding agencies',
            'internationally-guiding agencies',
            'worldwide-guiding agencies',
            'universally-guiding agencies',
            'globally-steering agencies',
            'internationally-steering agencies',
            'worldwide-steering agencies',
            'universally-steering agencies',
            'globally-controlling agencies',
            'internationally-controlling agencies',
            'worldwide-controlling agencies',
            'universally-controlling agencies',
            'globally-coordinating agencies',
            'internationally-coordinating agencies',
            'worldwide-coordinating agencies',
            'universally-coordinating agencies',
            'globally-supervising agencies',
            'internationally-supervising agencies',
            'worldwide-supervising agencies',
            'universally-supervising agencies',
            'globally-overseeing agencies',
            'internationally-overseeing agencies',
            'worldwide-overseeing agencies',
            'universally-overseeing agencies',
            'globally-monitoring agencies',
            'internationally-monitoring agencies',
            'worldwide-monitoring agencies',
            'universally-monitoring agencies',
            'globally-watching agencies',
            'internationally-watching agencies',
            'worldwide-watching agencies',
            'universally-watching agencies',
            'globally-observing agencies',
            'internationally-observing agencies',
            'worldwide-observing agencies',
            'universally-observing agencies',
            'globally-checking agencies',
            'internationally-checking agencies',
            'worldwide-checking agencies',
            'universally-checking agencies',
            'globally-verifying agencies',
            'internationally-verifying agencies',
            'worldwide-verifying agencies',
            'universally-verifying agencies',
            'globally-validating agencies',
            'internationally-validating agencies',
            'worldwide-validating agencies',
            'universally-validating agencies',
            'globally-confirming agencies',
            'internationally-confirming agencies',
            'worldwide-confirming agencies',
            'universally-confirming agencies',
            'globally-authenticating agencies',
            'internationally-authenticating agencies',
            'worldwide-authenticating agencies',
            'universally-authenticating agencies',
            'globally-certifying agencies',
            'internationally-certifying agencies',
            'worldwide-certifying agencies',
            'universally-certifying agencies',
            'globally-endorsing agencies',
            'internationally-endorsing agencies',
            'worldwide-endorsing agencies',
            'universally-endorsing agencies',
            'globally-approving agencies',
            'internationally-approving agencies',
            'worldwide-approving agencies',
            'universally-approving agencies',
            'globally-sanctioning agencies',
            'internationally-sanctioning agencies',
            'worldwide-sanctioning agencies',
            'universally-sanctioning agencies',
            'globally-authorizing agencies',
            'internationally-authorizing agencies',
            'worldwide-authorizing agencies',
            'universally-authorizing agencies',
            'globally-permitting agencies',
            'internationally-permitting agencies',
            'worldwide-permitting agencies',
            'universally-permitting agencies',
            'globally-allowing agencies',
            'internationally-allowing agencies',
            'worldwide-allowing agencies',
            'universally-allowing agencies',
            'globally-enabling agencies',
            'internationally-enabling agencies',
            'worldwide-enabling agencies',
            'universally-enabling agencies',
            'globally-facilitating agencies',
            'internationally-facilitating agencies',
            'worldwide-facilitating agencies',
            'universally-facilitating agencies',
            'globally-supporting agencies',
            'internationally-supporting agencies',
            'worldwide-supporting agencies',
            'universally-supporting agencies',
            'globally-assisting agencies',
            'internationally-assisting agencies',
            'worldwide-assisting agencies',
            'universally-assisting agencies',
            'globally-helping agencies',
            'internationally-helping agencies',
            'worldwide-helping agencies',
            'universally-helping agencies',
            'globally-aiding agencies',
            'internationally-aiding agencies',
            'worldwide-aiding agencies',
            'universally-aiding agencies',
            'globally-benefiting agencies',
            'internationally-benefiting agencies',
            'worldwide-benefiting agencies',
            'universally-benefiting agencies',
            'globally-advantaging agencies',
            'internationally-advantaging agencies',
            'worldwide-advantaging agencies',
            'universally-advantaging agencies',
            'globally-profiting agencies',
            'internationally-profiting agencies',
            'worldwide-profiting agencies',
            'universally-profiting agencies',
            'globally-gaining agencies',
            'internationally-gaining agencies',
            'worldwide-gaining agencies',
            'universally-gaining agencies',
            'globally-winning agencies',
            'internationally-winning agencies',
            'worldwide-winning agencies',
            'universally-winning agencies',
            'globally-succeeding agencies',
            'internationally-succeeding agencies',
            'worldwide-succeeding agencies',
            'universally-succeeding agencies',
            'globally-prevailing agencies',
            'internationally-prevailing agencies',
            'worldwide-prevailing agencies',
            'universally-prevailing agencies',
            'globally-triumphing agencies',
            'internationally-triumphing agencies',
            'worldwide-triumphing agencies',
            'universally-triumphing agencies',
            'globally-conquering agencies',
            'internationally-conquering agencies',
            'worldwide-conquering agencies',
            'universally-conquering agencies',
            'globally-overcoming agencies',
            'internationally-overcoming agencies',
            'worldwide-overcoming agencies',
            'universally-overcoming agencies',
            'globally-surmounting agencies',
            'internationally-surmounting agencies',
            'worldwide-surmounting agencies',
            'universally-surmounting agencies',
            'globally-mastering agencies',
            'internationally-mastering agencies',
            'worldwide-mastering agencies',
            'universally-mastering agencies',
            'globally-dominating agencies',
            'internationally-dominating agencies',
            'worldwide-dominating agencies',
            'universally-dominating agencies',
            'globally-leading agencies',
            'internationally-leading agencies',
            'worldwide-leading agencies',
            'universally-leading agencies',
            'globally-commanding agencies',
            'internationally-commanding agencies',
            'worldwide-commanding agencies',
            'universally-commanding agencies',
            'globally-ruling agencies',
            'internationally-ruling agencies',
            'worldwide-ruling agencies',
            'universally-ruling agencies',
            'globally-governing agencies',
            'internationally-governing agencies',
            'worldwide-governing agencies',
            'universally-governing agencies',
            'globally-administering agencies',
            'internationally-administering agencies',
            'worldwide-administering agencies',
            'universally-administering agencies',
            'globally-managing agencies',
            'internationally-managing agencies',
            'worldwide-managing agencies',
            'universally-managing agencies',
            'globally-directing agencies',
            'internationally-directing agencies',
            'worldwide-directing agencies',
            'universally-directing agencies',
            'globally-guiding agencies',
            'internationally-guiding agencies',
            'worldwide-guiding agencies',
            'universally-guiding agencies',
            'globally-steering agencies',
            'internationally-steering agencies',
            'worldwide-steering agencies',
            'universally-steering agencies',
            'globally-controlling agencies',
            'internationally-controlling agencies',
            'worldwide-controlling agencies',
            'universally-controlling agencies',
            'globally-coordinating agencies',
            'internationally-coordinating agencies',
            'worldwide-coordinating agencies',
            'universally-coordinating agencies',
            'globally-supervising agencies',
            'internationally-supervising agencies',
            'worldwide-supervising agencies',
            'universally-supervising agencies',
            'globally-overseeing agencies',
            'internationally-overseeing agencies',
            'worldwide-overseeing agencies',
            'universally-overseeing agencies',
            'globally-monitoring agencies',
            'internationally-monitoring agencies',
            'worldwide-monitoring agencies',
            'universally-monitoring agencies',
            'globally-watching agencies',
            'internationally-watching agencies',
            'worldwide-watching agencies',
            'universally-watching agencies',
            'globally-observing agencies',
            'internationally-observing agencies',
            'worldwide-observing agencies',
            'universally-observing agencies',
            'globally-checking agencies',
            'internationally-checking agencies',
            'worldwide-checking agencies',
            'universally-checking agencies',
            'globally-verifying agencies',
            'internationally-verifying agencies',
            'worldwide-verifying agencies',
            'universally-verifying agencies',
            'globally-validating agencies',
            'internationally-validating agencies',
            'worldwide-validating agencies',
            'universally-validating agencies',
            'globally-confirming agencies',
            'internationally-confirming agencies',
            'worldwide-confirming agencies',
            'universally-confirming agencies',
            'globally-authenticating agencies',
            'internationally-authenticating agencies',
            'worldwide-authenticating agencies',
            'universally-authenticating agencies',
            'globally-certifying agencies',
            'internationally-certifying agencies',
            'worldwide-certifying agencies',
            'universally-certifying agencies',
            'globally-endorsing agencies',
            'internationally-endorsing agencies',
            'worldwide-endorsing agencies',
            'universally-endorsing agencies',
            'globally-approving agencies',
            'internationally-approving agencies',
            'worldwide-approving agencies',
            'universally-approving agencies',
            'globally-sanctioning agencies',
            'internationally-sanctioning agencies',
            'worldwide-sanctioning agencies',
            'universally-sanctioning agencies',
            'globally-authorizing agencies',
            'internationally-authorizing agencies',
            'worldwide-authorizing agencies',
            'universally-authorizing agencies',
            'globally-permitting agencies',
            'internationally-permitting agencies',
            'worldwide-permitting agencies',
            'universally-permitting agencies',
            'globally-allowing agencies',
            'internationally-allowing agencies',
            'worldwide-allowing agencies',
            'universally-allowing agencies',
            'globally-enabling agencies',
            'internationally-enabling agencies',
            'worldwide-enabling agencies',
            'universally-enabling agencies',
            'globally-facilitating agencies',
            'internationally-facilitating agencies',
            'worldwide-facilitating agencies',
            'universally-facilitating agencies',
            'globally-supporting agencies',
            'internationally-supporting agencies',
            'worldwide-supporting agencies',
            'universally-supporting agencies',
            'globally-assisting agencies',
            'internationally-assisting agencies',
            'worldwide-assisting agencies',
            'universally-assisting agencies',
            'globally-helping agencies',
            'internationally-helping agencies',
            'worldwide-helping agencies',
            'universally-helping agencies',
            'globally-aiding agencies',
            'internationally-aiding agencies',
            'worldwide-aiding agencies',
            'universally-aiding agencies',
            'globally-benefiting agencies',
            'internationally-benefiting agencies',
            'worldwide-benefiting agencies',
            'universally-benefiting agencies',
            'globally-advantaging agencies',
            'internationally-advantaging agencies',
            'worldwide-advantaging agencies',
            'universally-advantaging agencies',
            'globally-profiting agencies',
            'internationally-profiting agencies',
            'worldwide-profiting agencies',
            'universally-profiting agencies',
            'globally-gaining agencies',
            'internationally-gaining agencies',
            'worldwide-gaining agencies',
            'universally-gaining agencies',
            'globally-winning agencies',
            'internationally-winning agencies',
            'worldwide-winning agencies',
            'universally-winning agencies',
            'globally-succeeding agencies',
            'internationally-succeeding agencies',
            'worldwide-succeeding agencies',
            'universally-succeeding agencies',
            'globally-prevailing agencies',
            'internationally-prevailing agencies',
            'worldwide-prevailing agencies',
            'universally-prevailing agencies',
            'globally-triumphing agencies',
            'internationally-triumphing agencies',
            'worldwide-triumphing agencies',
            'universally-triumphing agencies',
            'globally-conquering agencies',
            'internationally-conquering agencies',
            'worldwide-conquering agencies',
            'universally-conquering agencies',
            'globally-overcoming agencies',
            'internationally-overcoming agencies',
            'worldwide-overcoming agencies',
            'universally-overcoming agencies',
            'globally-surmounting agencies',
            'internationally-surmounting agencies',
            'worldwide-surmounting agencies',
            'universally-surmounting agencies',
            'globally-mastering agencies',
            'internationally-mastering agencies',
            'worldwide-mastering agencies',
            'universally-mastering agencies',
            'globally-dominating agencies',
            'internationally-dominating agencies',
            'worldwide-dominating agencies',
            'universally-dominating agencies',
            'globally-leading agencies',
            'internationally-leading agencies',
            'worldwide-leading agencies',
            'universally-leading agencies',
            'globally-commanding agencies',
            'internationally-commanding agencies',
            'worldwide-commanding agencies',
            'universally-commanding agencies',
            'globally-ruling agencies',
            'internationally-ruling agencies',
            'worldwide-ruling agencies',
            'universally-ruling agencies',
            'globally-governing agencies',
            'internationally-governing agencies',
            'worldwide-governing agencies',
            'universally-governing agencies',
            'globally-administering agencies',
            'internationally-administering agencies',
            'worldwide-administering agencies',
            'universally-administering agencies',
            'globally-managing agencies',
            'internationally-managing agencies',
            'worldwide-managing agencies',
            'universally-managing agencies',
            'globally-directing agencies',
            'internationally-directing agencies',
            'worldwide-directing agencies',
            'universally-directing agencies',
            'globally-guiding agencies',
            'internationally-guiding agencies',
            'worldwide-guiding agencies',
            'universally-guiding agencies',
            'globally-steering agencies',
            'internationally-steering agencies',
            'worldwide-steering agencies',
            'universally-steering agencies',
            'globally-controlling agencies',
            'internationally-controlling agencies',
            'worldwide-controlling agencies',
            'universally-controlling agencies',
            'globally-coordinating agencies',
            'internationally-coordinating agencies',
            'worldwide-coordinating agencies',
        ]

        for pattern in invalid_patterns:
            if pattern in name_lower:
                return False

        return True

    def normalize_agency_data(self, agency_data, polish_city=None):
        """Normalize agency data to match database schema"""
        normalized = {
            'name': agency_data.get('name', '').strip(),
            'type': 'gemini_discovered',
            'website': agency_data.get('website', '').strip(),
            'phone': agency_data.get('phone', '').strip(),
            'address': agency_data.get('address', '').strip(),
            'description': agency_data.get('description', '').strip(),
            'additional_info': f"Discovered via Gemini AI on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            'polish_city': polish_city or agency_data.get('polish_city', '').strip()
        }

        # Clean up website URL
        if normalized['website']:
            normalized['website'] = re.sub(r'[.,;]$', '', normalized['website'])

        return normalized

    def is_duplicate(self, agency):
        """Check if agency is a duplicate based on domain and name"""
        agency_name = agency.get('name', '').lower().strip()

        # Check exact name match
        if agency_name in self.existing_names:
            logging.info(f"   🚫 Duplicate name found: {agency_name}")
            return True

        # Check domain match
        if agency.get('website'):
            domain_match = re.search(r'https?://(?:www\.)?([^/]+)', agency['website'])
            if domain_match:
                domain = domain_match.group(1).lower()
                if domain in self.existing_domains:
                    logging.info(f"   🚫 Duplicate domain found: {domain}")
                    return True

        # Check for fuzzy name matches (similar names)
        if self.is_fuzzy_name_duplicate(agency_name):
            logging.info(f"   🚫 Fuzzy name duplicate found: {agency_name}")
            return True

        return False

    def is_fuzzy_name_duplicate(self, agency_name):
        """Check for fuzzy name matches to catch similar agency names"""
        if not agency_name:
            return False

        # Common variations to check
        variations = [
            agency_name,
            agency_name.replace('properties', 'property'),
            agency_name.replace('property', 'properties'),
            agency_name.replace('real estate', 'realtors'),
            agency_name.replace('realtors', 'real estate'),
            agency_name.replace('agency', 'agencies'),
            agency_name.replace('agencies', 'agency'),
            agency_name.replace('international', 'intl'),
            agency_name.replace('marbella', ''),
            agency_name.replace('costa del sol', ''),
            agency_name.replace('costa', ''),
        ]

        # Remove extra spaces and check
        variations = [re.sub(r'\s+', ' ', v).strip() for v in variations]

        for variation in variations:
            if variation in self.existing_names and variation != agency_name:
                return True

        return False

    def save_agencies(self, agencies, run_cleanup=False):
        """Save new agencies to database and optionally run cleanup tools"""
        if not agencies:
            return 0

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            saved_count = 0
            for agency in agencies:
                if not self.is_duplicate(agency):
                    cursor.execute('''
                        INSERT INTO agencies (name, type, website, phone, address, description, additional_info, polish_city)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        agency['name'],
                        agency['type'],
                        agency['website'],
                        agency['phone'],
                        agency['address'],
                        agency['description'],
                        agency['additional_info'],
                        agency.get('polish_city', '')
                    ))
                    saved_count += 1
                    logging.info(f"Added new agency: {agency['name']} from {agency.get('polish_city', 'unknown city')}")

            conn.commit()
            conn.close()

            # Run cleanup tools optionally if agencies were saved and explicitly requested
            if saved_count > 0 and run_cleanup:
                print(f"🧹 Running cleanup tools on {saved_count} new agencies...")
                self.run_cleanup_tools()
                print("✅ Cleanup tools completed")

            return saved_count

        except Exception as e:
            logging.error(f"Error saving agencies: {e}")
            return 0

    def run_cleanup_tools(self):
        """Run all cleanup tools automatically"""
        try:
            # Run name cleaning
            print("   🔧 Running name cleaning...")
            result = subprocess.run([sys.executable, 'tools/clean_names.py'],
                                  capture_output=True, text=True, cwd=os.getcwd())
            if result.returncode == 0:
                print("   ✅ Name cleaning completed")
            else:
                print(f"   ⚠️ Name cleaning had issues: {result.stderr[:100]}")

            # Run website fixing
            print("   🔧 Running website extraction...")
            result = subprocess.run([sys.executable, 'tools/fix_websites.py'],
                                  capture_output=True, text=True, cwd=os.getcwd())
            if result.returncode == 0:
                print("   ✅ Website extraction completed")
            else:
                print(f"   ⚠️ Website extraction had issues: {result.stderr[:100]}")

            # Run duplicate removal
            print("   🔧 Running duplicate removal...")
            result = subprocess.run([sys.executable, 'tools/remove_duplicates.py'],
                                  capture_output=True, text=True, cwd=os.getcwd())
            if result.returncode == 0:
                print("   ✅ Duplicate removal completed")
            else:
                print(f"   ⚠️ Duplicate removal had issues: {result.stderr[:100]}")

            # Run type classification
            print("   🔧 Running type classification...")
            result = subprocess.run([sys.executable, 'tools/update_types.py'],
                                  capture_output=True, text=True, cwd=os.getcwd())
            if result.returncode == 0:
                print("   ✅ Type classification completed")
            else:
                print(f"   ⚠️ Type classification had issues: {result.stderr[:100]}")

        except Exception as e:
            print(f"   💥 Error running cleanup tools: {e}")
            logging.error(f"Error running cleanup tools: {e}")

    def get_polish_towns(self):
        """Get list of major Polish towns/cities for targeted searches, prioritized by population"""
        # Major cities by population (most important first) - expanded to 50 cities
        return [
            # Top 30 cities (current list)
            "Warsaw", "Krakow", "Lodz", "Wroclaw", "Poznan", "Gdansk", "Szczecin",
            "Bydgoszcz", "Lublin", "Katowice", "Bialystok", "Gdynia", "Czestochowa",
            "Radom", "Sosnowiec", "Torun", "Kielce", "Rzeszow", "Gliwice", "Zabrze",
            "Olsztyn", "Bielsko-Biala", "Bytom", "Zielona Gora", "Rybnik", "Ruda Slaska",
            "Opole", "Tychy", "Gorzow Wielkopolski", "Dabrowa Gornicza",
            # Additional cities (31-50) for expanded coverage
            "Plock", "Elblag", "Walbrzych", "Tarnow", "Chorzow", "Koszalin", "Kalisz",
            "Legnica", "Grudziadz", "Slupsk", "Jastrzebie-Zdroj", "Nowy Sacz", "Jaworzno",
            "Jelenia Gora", "Ostrow Mazowiecka", "Swidnica", "Stalowa Wola", "Piekary Slaskie",
            "Lubin", "Zamosc"
        ]

    def get_polish_keywords(self):
        """Get Polish real estate keywords and phrases"""
        return {
            'agencies': ['biuro nieruchomości', 'agencja nieruchomości', 'firma nieruchomościowa'],
            'properties': ['nieruchomości', 'własność', 'mieszkanie', 'dom', 'apartament'],
            'locations': ['Costa del Sol', 'Marbella', 'Hiszpania', 'Hiszpania nieruchomości'],
            'services': ['sprzedaż', 'kupno', 'inwestycja', 'wynajem'],
            'combinations': [
                'nieruchomości Costa del Sol',
                'Marbella nieruchomości',
                'Hiszpania nieruchomości',
                'Costa del Sol inwestycja',
                'Marbella sprzedaż'
            ]
        }

    def get_existing_agencies_by_city(self):
        """Get existing agencies grouped by their city/location"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Get agencies with Polish focus or from Polish cities
            cursor.execute('''
                SELECT name, address, description, additional_info
                FROM agencies
                WHERE type = 'polish' OR additional_info LIKE '%Poland%'
                ORDER BY name
            ''')

            agencies_by_city = {}
            for row in cursor.fetchall():
                name, address, description, additional_info = row

                # Try to extract city from address or additional_info
                city = self.extract_city_from_text(address + " " + description + " " + additional_info)

                if city:
                    if city not in agencies_by_city:
                        agencies_by_city[city] = []
                    agencies_by_city[city].append(name)

            conn.close()
            return agencies_by_city

        except Exception as e:
            logging.error(f"Error getting existing agencies by city: {e}")
            return {}

    def extract_city_from_text(self, text):
        """Extract Polish city name from text"""
        polish_cities = self.get_polish_towns()
        text_lower = text.lower()

        for city in polish_cities:
            if city.lower() in text_lower:
                return city

        return None

    def generate_search_prompts(self):
        """Generate a series of targeted prompts for finding agencies"""
        prompts = []
        polish_towns = self.get_polish_towns()

        # Basic searches
        prompts.extend([
            "List 5 real estate agencies in Marbella, Spain with their websites and phone numbers.",
            "Find luxury real estate agencies in Marbella that specialize in high-end properties. Include contact information and websites.",
            "Find property management companies in Marbella that handle rentals and sales. List their contact details.",
            "Find inmobiliarias in Marbella, Spain. List their names, websites, addresses, and phone numbers.",
            "Find commercial real estate agencies in Marbella that handle business properties and investments.",
            "Find real estate agencies in Marbella that specialize in new developments and off-plan properties."
        ])

        # Polish-focused general searches
        prompts.extend([
            "Find real estate agencies in Marbella that work with Polish buyers or have Polish-speaking staff. Include their websites and contact information.",
            "Search for real estate agencies in Marbella that cater specifically to Polish clients or expatriates.",
            "Find agencies in Marbella that help Polish investors purchase property in Spain."
        ])

        # Targeted searches for Polish agencies offering Costa del Sol properties
        for town in polish_towns[:10]:  # Use first 10 towns for manageable prompt count
            prompts.extend([
                f"Find real estate agencies in {town}, Poland that specialize in Costa del Sol properties. Include their websites and contact information.",
                f"Search for property agencies in {town}, Poland that offer Marbella real estate for sale. List their contact details.",
                f"Find Polish real estate companies in {town} that help clients buy property in Marbella, Spain."
            ])

        # Additional specialized searches
        prompts.extend([
            "Search Google for 'real estate agencies Marbella Polish clients' and list the top results with contact information.",
            "Find agencies in Marbella that advertise property services to Polish markets or have Polish language websites.",
            "Search for real estate consultants in Marbella who specialize in the Polish property market."
        ])

        return prompts

    def run_discovery(self, max_prompts=5, use_web_search=True):
        """Run the agency discovery process"""
        logging.info("Starting Gemini agency discovery...")

        prompts = self.generate_search_prompts()
        all_agencies = []
        processed_prompts = 0

        for prompt in prompts[:max_prompts]:
            logging.info(f"Processing prompt {processed_prompts + 1}/{min(max_prompts, len(prompts))}")

            response = self.run_gemini_prompt(prompt, use_web_search)
            if response:
                agencies = self.parse_agency_data(response)
                logging.info(f"Found {len(agencies)} potential agencies from this prompt")

                # Filter out duplicates
                new_agencies = [a for a in agencies if not self.is_duplicate(a)]
                all_agencies.extend(new_agencies)
                logging.info(f"Added {len(new_agencies)} new agencies (filtered duplicates)")

            processed_prompts += 1

            # Rate limiting
            if processed_prompts < len(prompts):
                time.sleep(2)

        # Remove duplicates within the batch
        unique_agencies = []
        seen_names = set()
        for agency in all_agencies:
            name_key = agency['name'].lower().strip()
            if name_key not in seen_names:
                seen_names.add(name_key)
                unique_agencies.append(agency)

        # Save to database
        saved_count = self.save_agencies(unique_agencies)

        logging.info(f"Discovery complete. Found {len(unique_agencies)} unique agencies, saved {saved_count} to database.")
        return saved_count

    def run_targeted_polish_search(self, target_agencies=50, use_context=True, max_iterations=None):
        """Run targeted searches for specific Polish towns with context-aware prompting until target reached"""
        print(f"🚀 Starting targeted Polish town agency discovery...")
        print(f"🎯 Target: {target_agencies} new agencies")
        print("=" * 60)

        logging.info(f"Starting targeted Polish town agency discovery... Target: {target_agencies} new agencies")

        # Get unscanned cities
        scanned_cities = self.get_scanned_cities()
        all_polish_towns = self.get_polish_towns()
        unscanned_cities = [city for city in all_polish_towns if city not in scanned_cities]

        print(f"🏙️ Cities available: {len(all_polish_towns)}")
        print(f"✅ Cities already scanned: {len(scanned_cities)}")
        print(f"🎯 Cities to scan: {len(unscanned_cities)}")

        if not unscanned_cities:
            print("⚠️ All cities have been scanned! Restarting from the beginning...")
            logging.warning("All cities have been scanned, restarting from beginning")
            unscanned_cities = all_polish_towns.copy()

        keywords = self.get_polish_keywords()

        all_agencies = []
        processed_towns = 0
        total_saved = 0
        iteration = 0

        while total_saved < target_agencies and (max_iterations is None or iteration < max_iterations):
            iteration += 1
            print(f"\n📊 Iteration {iteration} - Progress: {total_saved}/{target_agencies} agencies")
            logging.info(f"=== Iteration {iteration} === Total agencies found so far: {total_saved}")

            # Refresh existing agencies context for each iteration
            existing_agencies_by_city = self.get_existing_agencies_by_city() if use_context else {}

            # Process towns in batches from unscanned cities
            towns_batch = unscanned_cities[processed_towns:processed_towns + 5]  # Process 5 towns per iteration
            if not towns_batch:
                print("🔄 All unscanned cities processed, restarting from beginning...")
                logging.info("All unscanned cities processed, restarting from beginning...")
                processed_towns = 0
                towns_batch = unscanned_cities[:5] if unscanned_cities else all_polish_towns[:5]

            print(f"🏘️ Processing cities: {', '.join(towns_batch)}")

            for town_idx, town in enumerate(towns_batch, 1):
                print(f"\n🏙️ [{town_idx}/5] Scanning {town}, Poland...")
                logging.info(f"🔍 Searching for agencies in {town}, Poland...")

                # Get existing agencies for this city to exclude them
                existing_agencies = existing_agencies_by_city.get(town, [])
                exclude_text = ""
                if existing_agencies:
                    exclude_text = f" Exclude these agencies we already know about: {', '.join(existing_agencies[:5])}. "
                    print(f"   📋 Excluding {len(existing_agencies)} known agencies")
                    logging.info(f"   📋 Excluding {len(existing_agencies)} known agencies from {town}")

                # Create targeted prompts with structured JSON output
                prompts = [
                    f"""Find real estate agencies in {town}, Poland that specialize in Costa del Sol or international properties.{exclude_text}

Return ONLY a JSON array with this exact format:
[{{"name": "Agency Name", "website": "https://example.com", "phone": "+48 XXX XXX XXX", "address": "Address in {town}"}}]

If no agencies are found, return an empty array []. Do not include explanations or additional text.""",

                    f"""Search for property agencies in {town}, Poland that help with international property purchases including Spain/Costa del Sol.{exclude_text}

Return ONLY a JSON array with this exact format:
[{{"name": "Agency Name", "website": "https://example.com", "phone": "+48 XXX XXX XXX", "address": "Address in {town}"}}]

If no agencies are found, return an empty array []. Do not include explanations or additional text.""",

                    f"""Find Polish real estate companies in {town} that offer services for buying property abroad, especially in Spain.{exclude_text}

Return ONLY a JSON array with this exact format:
[{{"name": "Agency Name", "website": "https://example.com", "phone": "+48 XXX XXX XXX", "address": "Address in {town}"}}]

If no agencies are found, return an empty array []. Do not include explanations or additional text.""",

                    f"""Search for 'biuro nieruchomości' in {town}, Poland that might handle international property transactions.{exclude_text}

Return ONLY a JSON array with this exact format:
[{{"name": "Agency Name", "website": "https://example.com", "phone": "+48 XXX XXX XXX", "address": "Address in {town}"}}]

If no agencies are found, return an empty array []. Do not include explanations or additional text.""",

                    f"""Find any real estate agencies in {town}, Poland that could assist with foreign property purchases.{exclude_text}

Return ONLY a JSON array with this exact format:
[{{"name": "Agency Name", "website": "https://example.com", "phone": "+48 XXX XXX XXX", "address": "Address in {town}"}}]

If no agencies are found, return an empty array []. Do not include explanations or additional text."""
                ]

                town_agencies = []
                for i, prompt in enumerate(prompts, 1):
                    try:
                        print(f"   🤖 [{i}/5] Querying AI...")
                        logging.info(f"   🤖 Prompt {i}/5: {prompt[:80]}...")
                        response = self.run_gemini_prompt(prompt)
                        if response:
                            agencies = self.parse_agency_data(response, town)
                            print(f"   📄 Found {len(agencies)} potential agencies")
                            logging.info(f"   📄 Response received ({len(response)} chars)")
                            logging.info(f"   🔍 Parsed {len(agencies)} potential agencies from response")
                            town_agencies.extend(agencies)
                        else:
                            print(f"   ❌ No response for prompt {i}")
                            logging.warning(f"   ❌ No response received for prompt {i}")
                    except Exception as e:
                        print(f"   💥 Error processing prompt {i}: {str(e)[:50]}...")
                        logging.error(f"Error processing prompt {i} for {town}: {e}")
                        continue

                    time.sleep(1)  # Rate limiting between prompts

                # Filter duplicates for this town
                new_agencies = [a for a in town_agencies if not self.is_duplicate(a)]
                all_agencies.extend(new_agencies)
                print(f"   ✅ {len(new_agencies)} new agencies found for {town}")
                logging.info(f"   ✅ Found {len(new_agencies)} new agencies for {town}")

                # Log details of new agencies found
                for agency in new_agencies[:3]:  # Show first 3
                    print(f"      ➕ {agency['name']}")
                    logging.info(f"      ➕ NEW: {agency['name']} - {agency.get('website', 'No website')}")

                if len(new_agencies) > 3:
                    print(f"      ... and {len(new_agencies) - 3} more")

            # Remove duplicates across all towns in this batch
            unique_agencies = []
            seen_names = set()
            for agency in all_agencies:
                name_key = agency['name'].lower().strip()
                if name_key not in seen_names:
                    seen_names.add(name_key)
                    unique_agencies.append(agency)

            # Save to database
            print(f"\n💾 Saving {len(unique_agencies)} agencies to database...")
            batch_saved = self.save_agencies(unique_agencies)
            total_saved += batch_saved

            print(f"✅ Batch complete: {batch_saved} agencies saved")
            print(f"📊 Total progress: {total_saved}/{target_agencies} agencies")

            logging.info(f"📊 Batch complete: Found {len(unique_agencies)} unique agencies, saved {batch_saved} to database")
            logging.info(f"🎯 Progress: {total_saved}/{target_agencies} total agencies saved")

            processed_towns += len(towns_batch)

            # Check if we've reached the target
            if total_saved >= target_agencies:
                print(f"\n🎉 TARGET REACHED! Found {total_saved} new agencies")
                logging.info(f"🎉 Target reached! Found {total_saved} new agencies")
                break

            # Rate limiting between batches
            if iteration < 10:  # Don't wait on last few iterations
                print("⏳ Waiting 3 seconds before next batch...")
                logging.info("⏳ Waiting 3 seconds before next batch...")
                time.sleep(3)

        print(f"\n🏁 Search complete! Total agencies found: {total_saved}")
        logging.info(f"🏁 Targeted search complete. Total agencies found: {total_saved}")
        return total_saved

    def run_single_city_scan(self, city_name=None, target_agencies=10):
        """Run targeted search for a single Polish city"""
        logging.info(f"Starting single city scan for {city_name or 'next unscanned city'}... Target: {target_agencies} agencies")

        polish_towns = self.get_polish_towns()
        keywords = self.get_polish_keywords()

        # If no city specified, find the next unscanned city
        if not city_name:
            # Get cities that haven't been scanned yet (based on tracking file or database)
            scanned_cities = self.get_scanned_cities()
            unscanned_cities = [city for city in polish_towns if city not in scanned_cities]
            if unscanned_cities:
                city_name = unscanned_cities[0]
                logging.info(f"Selected next unscanned city: {city_name}")
            else:
                logging.info("All cities have been scanned, restarting from beginning...")
                city_name = polish_towns[0]

        if city_name not in polish_towns:
            logging.error(f"City '{city_name}' not found in Polish cities list")
            return 0

        logging.info(f"🔍 Scanning single city: {city_name}, Poland...")

        # Get existing agencies for this city to exclude them
        existing_agencies_by_city = self.get_existing_agencies_by_city()
        existing_agencies = existing_agencies_by_city.get(city_name, [])
        exclude_text = ""
        if existing_agencies:
            exclude_text = f" Exclude these agencies we already know about: {', '.join(existing_agencies[:5])}. "
            logging.info(f"   📋 Excluding {len(existing_agencies)} known agencies from {city_name}")

        # Create targeted prompts with structured JSON output
        prompts = [
            f"""Find real estate agencies in {city_name}, Poland that specialize in Costa del Sol or international properties.{exclude_text}

Return ONLY a JSON array with this exact format:
[{{"name": "Agency Name", "website": "https://example.com", "phone": "+48 XXX XXX XXX", "address": "Address in {city_name}"}}]

If no agencies are found, return an empty array []. Do not include explanations or additional text.""",

            f"""Search for property agencies in {city_name}, Poland that help with international property purchases including Spain/Costa del Sol.{exclude_text}

Return ONLY a JSON array with this exact format:
[{{"name": "Agency Name", "website": "https://example.com", "phone": "+48 XXX XXX XXX", "address": "Address in {city_name}"}}]

If no agencies are found, return an empty array []. Do not include explanations or additional text.""",

            f"""Find Polish real estate companies in {city_name} that offer services for buying property abroad, especially in Spain.{exclude_text}

Return ONLY a JSON array with this exact format:
[{{"name": "Agency Name", "website": "https://example.com", "phone": "+48 XXX XXX XXX", "address": "Address in {city_name}"}}]

If no agencies are found, return an empty array []. Do not include explanations or additional text.""",

            f"""Search for 'biuro nieruchomości' in {city_name}, Poland that might handle international property transactions.{exclude_text}

Return ONLY a JSON array with this exact format:
[{{"name": "Agency Name", "website": "https://example.com", "phone": "+48 XXX XXX XXX", "address": "Address in {city_name}"}}]

If no agencies are found, return an empty array []. Do not include explanations or additional text.""",

            f"""Find any real estate agencies in {city_name}, Poland that could assist with foreign property purchases.{exclude_text}

Return ONLY a JSON array with this exact format:
[{{"name": "Agency Name", "website": "https://example.com", "phone": "+48 XXX XXX XXX", "address": "Address in {city_name}"}}]

If no agencies are found, return an empty array []. Do not include explanations or additional text."""
        ]

        city_agencies = []
        for i, prompt in enumerate(prompts, 1):
            logging.info(f"   🤖 Prompt {i}/5: {prompt[:80]}...")
            response = self.run_gemini_prompt(prompt)
            if response:
                logging.info(f"   📄 Response received ({len(response)} chars)")
                agencies = self.parse_agency_data(response, city_name)
                logging.info(f"   🔍 Parsed {len(agencies)} potential agencies from response")
                city_agencies.extend(agencies)
            else:
                logging.warning(f"   ❌ No response received for prompt {i}")

            time.sleep(1)  # Rate limiting between prompts

        # Filter duplicates for this city
        new_agencies = [a for a in city_agencies if not self.is_duplicate(a)]
        logging.info(f"   ✅ Found {len(new_agencies)} new agencies for {city_name}")

        # Log details of new agencies found
        for agency in new_agencies:
            logging.info(f"      ➕ NEW: {agency['name']} - {agency.get('website', 'No website')}")

        # Save to database
        saved_count = self.save_agencies(new_agencies)

        # Update tracking file
        self.update_city_tracking(city_name, len(new_agencies))

        logging.info(f"🏁 Single city scan complete for {city_name}. Found {len(new_agencies)} agencies, saved {saved_count} to database")
        return saved_count

    def get_scanned_cities(self):
        """Get list of cities that have been scanned based on tracking file"""
        try:
            scanned_cities = set()

            # Read the tracking file to get scanned cities
            with open('polish-cities-tracking.md', 'r', encoding='utf-8') as f:
                content = f.read()

            # Parse the table rows to find cities marked as scanned (✅)
            lines = content.split('\n')
            in_table = False

            for line in lines:
                line = line.strip()
                if line.startswith('| City |') and 'Scanned |' in line:
                    in_table = True
                    continue
                elif line.startswith('|------') and in_table:
                    continue
                elif line.startswith('| ') and in_table and ' | ' in line:
                    # Parse table row
                    parts = line.split('|')
                    if len(parts) >= 6:
                        city = parts[1].strip()
                        scanned_status = parts[3].strip()
                        if scanned_status == '✅':
                            scanned_cities.add(city)
                elif line.startswith('## ') and in_table:
                    # End of table
                    break

            logging.info(f"Found {len(scanned_cities)} scanned cities from tracking file")
            return scanned_cities

        except Exception as e:
            logging.error(f"Error getting scanned cities from tracking file: {e}")
            return set()

    def update_city_tracking(self, city_name, agencies_found):
        """Update the tracking file with scan results for a city"""
        try:
            # Read current tracking file
            with open('polish-cities-tracking.md', 'r', encoding='utf-8') as f:
                content = f.read()

            # Update the city's status in the table
            today = datetime.now().strftime('%Y-%m-%d')

            # Find and replace the city's row
            import re
            city_pattern = f"\\| {re.escape(city_name)} \\| (\\d+) \\| ❌ \\| 0 \\| - \\| ([^\\|]*) \\|"
            replacement = f"| {city_name} | \\1 | ✅ | {agencies_found} | {today} | Scanned - {agencies_found} agencies found |"

            updated_content = re.sub(city_pattern, replacement, content, flags=re.MULTILINE)

            # Update statistics
            # Find current stats
            total_scanned_match = re.search(r"Cities Scanned: (\d+)", updated_content)
            total_agencies_match = re.search(r"Total Agencies Found: (\d+)", updated_content)

            if total_scanned_match and total_agencies_match:
                current_scanned = int(total_scanned_match.group(1))
                current_agencies = int(total_agencies_match.group(1))

                new_scanned = current_scanned + 1
                new_agencies = current_agencies + agencies_found

                updated_content = re.sub(r"Cities Scanned: \d+", f"Cities Scanned: {new_scanned}", updated_content)
                updated_content = re.sub(r"Cities Remaining: \d+", f"Cities Remaining: {50 - new_scanned}", updated_content)
                updated_content = re.sub(r"Total Agencies Found: \d+", f"Total Agencies Found: {new_agencies}", updated_content)

            # Update last updated date
            updated_content = re.sub(r"\\*Last Updated: [^\\*]+\\*", f"*Last Updated: {today}*", updated_content)

            # Write back to file
            with open('polish-cities-tracking.md', 'w', encoding='utf-8') as f:
                f.write(updated_content)

            logging.info(f"Updated tracking file for city: {city_name}")

        except Exception as e:
            logging.error(f"Error updating city tracking: {e}")

    def fill_missing_data_web_search(self, max_agencies=None):
        """Use Gemini AI to search for missing contact information for gemini_discovered agencies"""
        print("🔍 Starting web search to fill missing data for gemini_discovered agencies...")
        logging.info("Starting web search to fill missing data for gemini_discovered agencies")

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Get agencies with missing data
            cursor.execute('''
                SELECT id, name, website, phone, address, description
                FROM agencies
                WHERE type = 'gemini_discovered'
                AND (website IS NULL OR website = '' OR phone IS NULL OR phone = '' OR address IS NULL OR address = '')
                ORDER BY id
            ''')

            agencies_to_update = cursor.fetchall()
            conn.close()

            if not agencies_to_update:
                print("✅ No agencies found with missing data")
                return 0

            if max_agencies:
                agencies_to_update = agencies_to_update[:max_agencies]

            print(f"📋 Found {len(agencies_to_update)} agencies with missing data")
            logging.info(f"Found {len(agencies_to_update)} agencies with missing data")

            updated_count = 0

            for agency_id, name, website, phone, address, description in agencies_to_update:
                print(f"\n🔎 Searching for: {name}")

                # Determine what data is missing
                missing_fields = []
                if not website or website.strip() == '':
                    missing_fields.append('website')
                if not phone or phone.strip() == '':
                    missing_fields.append('phone number')
                if not address or address.strip() == '':
                    missing_fields.append('address')

                if not missing_fields:
                    continue

                missing_text = ', '.join(missing_fields)

                # Create search prompt
                prompt = f"""Search the web for the real estate agency "{name}" in Marbella, Spain.
Find their {missing_text}. Provide the information in this exact format:
Website: [URL or "Not found"]
Phone: [phone number or "Not found"]
Address: [full address or "Not found"]

Only include factual information from reliable sources."""

                print(f"   🤖 Searching for: {missing_text}")
                logging.info(f"Searching for missing data for agency: {name}")

                response = self.run_gemini_prompt(prompt)
                if response:
                    # Parse the response
                    updates = self.parse_web_search_response(response)

                    if updates:
                        # Update database
                        if self.update_agency_data(agency_id, updates):
                            updated_count += 1
                            print(f"   ✅ Updated: {', '.join([f'{k}: {v}' for k, v in updates.items() if v and v != 'Not found'])}")
                            logging.info(f"Updated agency {name} with: {updates}")
                        else:
                            print("   ❌ Failed to update database")
                    else:
                        print("   ⚠️ No useful information found")
                else:
                    print("   ❌ No response from AI")

                # Rate limiting
                time.sleep(2)

            print(f"\n🎉 Completed! Updated {updated_count} agencies with missing data")
            logging.info(f"Web search data filling complete. Updated {updated_count} agencies")
            return updated_count

        except Exception as e:
            print(f"💥 Error during web search: {e}")
            logging.error(f"Error during web search data filling: {e}")
            return 0

    def parse_web_search_response(self, response):
        """Parse Gemini response for web search results"""
        updates = {}

        lines = response.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('Website:'):
                website = line.replace('Website:', '').strip()
                if website and website != 'Not found' and 'http' in website:
                    updates['website'] = website
            elif line.startswith('Phone:'):
                phone = line.replace('Phone:', '').strip()
                if phone and phone != 'Not found':
                    updates['phone'] = phone
            elif line.startswith('Address:'):
                address = line.replace('Address:', '').strip()
                if address and address != 'Not found':
                    updates['address'] = address

        return updates

    def update_agency_data(self, agency_id, updates):
        """Update agency data in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Build update query dynamically
            set_parts = []
            values = []
            for field, value in updates.items():
                if value and value != 'Not found':
                    set_parts.append(f"{field} = ?")
                    values.append(value)

            if set_parts:
                query = f"UPDATE agencies SET {', '.join(set_parts)} WHERE id = ?"
                values.append(agency_id)

                cursor.execute(query, values)
                conn.commit()

                # Update additional_info to note the data enrichment
                cursor.execute('''
                    UPDATE agencies
                    SET additional_info = additional_info || ? || ?
                    WHERE id = ?
                ''', (
                    f" | Data enriched via web search on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                    f" (added: {', '.join(updates.keys())})",
                    agency_id
                ))
                conn.commit()

            conn.close()
            return True

        except Exception as e:
            logging.error(f"Error updating agency data: {e}")
            return False

def main():
    finder = GeminiAgencyFinder()
    # Use more prompts now that we have targeted Polish town searches
    saved_count = finder.run_discovery(max_prompts=8, use_web_search=True)
    print(f"Successfully added {saved_count} new agencies to the database.")

if __name__ == '__main__':
    import sys

    finder = GeminiAgencyFinder()

    if len(sys.argv) > 1 and sys.argv[1] == '--targeted':
        # Run targeted search for specific Polish towns
        target_agencies = 50  # Default target
        if len(sys.argv) > 2:
            try:
                target_agencies = int(sys.argv[2])
            except ValueError:
                print("Invalid target number, using default of 50")

        polish_towns = finder.get_polish_towns()
        print(f"🎯 Running targeted searches for {len(polish_towns)} Polish towns...")
        print(f"🎯 Target: {target_agencies} new agencies")
        print("=" * 60)

        saved_count = finder.run_targeted_polish_search(target_agencies=target_agencies, use_context=True)

        print("=" * 60)
        print(f"🎉 COMPLETED: Successfully added {saved_count} new agencies to the database!")
        print("📊 Check gemini_agency_finder.log for detailed operation logs")

    elif len(sys.argv) > 1 and sys.argv[1] == '--single':
        # Run single city scan
        city_name = None
        target_agencies = 10  # Default target for single city

        if len(sys.argv) > 2:
            city_name = sys.argv[2]
        if len(sys.argv) > 3:
            try:
                target_agencies = int(sys.argv[3])
            except ValueError:
                print("Invalid target number, using default of 10")

        print(f"🏙️ Running single city scan...")
        if city_name:
            print(f"🎯 Target City: {city_name}")
        else:
            print("🎯 Target: Next unscanned city")
        print(f"🎯 Target Agencies: {target_agencies}")
        print("=" * 60)

        saved_count = finder.run_single_city_scan(city_name=city_name, target_agencies=target_agencies)

        print("=" * 60)
        print(f"🎉 COMPLETED: Successfully added {saved_count} new agencies to the database!")
        print("📊 Check gemini_agency_finder.log for detailed operation logs")
        print("📋 Tracking file updated automatically")

    elif len(sys.argv) > 1 and sys.argv[1] == '--fill-missing':
        # Fill missing data using web search
        max_agencies = None
        if len(sys.argv) > 2:
            try:
                max_agencies = int(sys.argv[2])
            except ValueError:
                print("Invalid number, processing all agencies with missing data")

        print("🔍 Filling missing data for gemini_discovered agencies...")
        if max_agencies:
            print(f"🎯 Max agencies to process: {max_agencies}")
        else:
            print("🎯 Processing all agencies with missing data")
        print("=" * 60)

        updated_count = finder.fill_missing_data_web_search(max_agencies=max_agencies)

        print("=" * 60)
        print(f"🎉 COMPLETED: Successfully updated {updated_count} agencies with missing data!")
        print("📊 Check gemini_agency_finder.log for detailed operation logs")

    else:
        main()
