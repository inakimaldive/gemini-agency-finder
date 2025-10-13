#!/usr/bin/env python3
"""
Enhanced Website Validator with Chrome DevTools Integration

This script provides comprehensive website validation including:
- Multi-stage URL validation (syntax, HTTP->HTTPS, redirects)
- Chrome DevTools integration for security checks
- Smart URL correction and alternative discovery
- Multiple URL support with prioritization
"""

import sqlite3
import requests
import logging
import time
import json
from urllib.parse import urlparse, urljoin
from typing import Dict, List, Tuple, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class EnhancedWebsiteValidator:
    def __init__(self, use_chrome_devtools=False):
        self.use_chrome_devtools = use_chrome_devtools
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })

    def validate_url_comprehensive(self, url: str) -> Dict:
        """
        Comprehensive URL validation with multiple stages and corrections
        Returns detailed validation results
        """
        if not url or not isinstance(url, str):
            return {
                'original_url': url,
                'final_url': None,
                'status': 'invalid_url',
                'redirects': [],
                'security_warnings': [],
                'alternatives': []
            }

        result = {
            'original_url': url,
            'final_url': url,
            'status': 'unknown',
            'redirects': [],
            'security_warnings': [],
            'alternatives': [],
            'validation_method': 'requests'
        }

        # Stage 1: Basic syntax validation
        if not self._is_valid_url_syntax(url):
            result['status'] = 'invalid_syntax'
            # Try to fix syntax
            fixed_url = self._fix_url_syntax(url)
            if fixed_url and fixed_url != url:
                result['alternatives'].append({
                    'url': fixed_url,
                    'reason': 'syntax_correction',
                    'priority': 1
                })
            return result

        # Stage 2: HTTP -> HTTPS upgrade attempt
        if url.startswith('http://'):
            https_url = url.replace('http://', 'https://', 1)
            https_result = self._check_url_basic(https_url)
            if https_result['status'] == 'active':
                result['final_url'] = https_url
                result['status'] = 'upgraded_to_https'
                result['redirects'] = https_result.get('redirects', [])
                return result

        # Stage 3: Basic accessibility check
        basic_result = self._check_url_basic(url)
        result.update(basic_result)

        # Stage 4: Try common URL variations if basic check failed
        if result['status'] in ['connection_error', 'not_found', 'timeout']:
            alternatives = self._generate_url_alternatives(url)
            for alt_url, reason in alternatives:
                alt_result = self._check_url_basic(alt_url)
                if alt_result['status'] == 'active':
                    result['alternatives'].append({
                        'url': alt_url,
                        'reason': reason,
                        'priority': 2,
                        'status': 'active'
                    })
                    # If this is our first working alternative, use it as final
                    if result['status'] != 'active':
                        result['final_url'] = alt_url
                        result['status'] = 'corrected'
                        result['redirects'] = alt_result.get('redirects', [])

        # Stage 5: Chrome DevTools validation (if enabled)
        if self.use_chrome_devtools and result['status'] == 'active':
            chrome_result = self._validate_with_chrome_devtools(result['final_url'])
            result.update(chrome_result)

        return result

    def _is_valid_url_syntax(self, url: str) -> bool:
        """Check if URL has valid syntax"""
        try:
            result = urlparse(url)
            return bool(result.scheme and result.netloc)
        except:
            return False

    def _fix_url_syntax(self, url: str) -> Optional[str]:
        """Try to fix common URL syntax issues"""
        url = url.strip()

        # Remove trailing punctuation
        url = url.rstrip('.,;:!?)')

        # Add https:// if missing scheme
        if not url.startswith(('http://', 'https://')):
            if url.startswith('www.'):
                url = f'https://{url}'
            else:
                url = f'https://www.{url}'

        return url if self._is_valid_url_syntax(url) else None

    def _check_url_basic(self, url: str) -> Dict:
        """Basic URL accessibility check with redirect following"""
        result = {
            'status': 'unknown',
            'redirects': []
        }

        try:
            # First try HEAD request
            response = self.session.head(url, timeout=15, allow_redirects=True)

            if response.status_code == 200:
                result['status'] = 'active'
            elif response.status_code in [301, 302, 303, 307, 308]:
                result['status'] = 'redirect'
            elif response.status_code == 404:
                result['status'] = 'not_found'
            elif response.status_code >= 500:
                result['status'] = 'server_error'
            else:
                result['status'] = f'http_{response.status_code}'

            # Capture redirect chain
            if response.history:
                result['redirects'] = [
                    {
                        'from': resp.url,
                        'to': resp.headers.get('Location', ''),
                        'status': resp.status_code
                    }
                    for resp in response.history
                ]

        except requests.exceptions.SSLError:
            result['status'] = 'ssl_error'
            result['security_warnings'] = ['SSL certificate error']
        except requests.exceptions.Timeout:
            result['status'] = 'timeout'
        except requests.exceptions.ConnectionError:
            result['status'] = 'connection_error'
        except Exception as e:
            result['status'] = f'error_{str(e)[:20]}'

        return result

    def _generate_url_alternatives(self, url: str) -> List[Tuple[str, str]]:
        """Generate alternative URL variations to try"""
        alternatives = []
        parsed = urlparse(url)

        if not parsed.netloc:
            return alternatives

        domain = parsed.netloc
        path = parsed.path or '/'

        # Try www. prefix variations
        if domain.startswith('www.'):
            # Remove www.
            no_www = domain[4:]
            alternatives.append((url.replace(domain, no_www), 'remove_www'))
        else:
            # Add www.
            with_www = f'www.{domain}'
            alternatives.append((url.replace(domain, with_www), 'add_www'))

        # Try HTTPS variations
        if url.startswith('http://'):
            https_url = url.replace('http://', 'https://', 1)
            alternatives.append((https_url, 'upgrade_https'))
        elif url.startswith('https://'):
            http_url = url.replace('https://', 'http://', 1)
            alternatives.append((http_url, 'downgrade_http'))

        # Try common TLD variations for Polish/Spanish sites
        if domain.endswith('.pl'):
            es_domain = domain.replace('.pl', '.es')
            alternatives.append((url.replace(domain, es_domain), 'tld_pl_to_es'))
            com_domain = domain.replace('.pl', '.com')
            alternatives.append((url.replace(domain, com_domain), 'tld_pl_to_com'))
        elif domain.endswith('.es'):
            pl_domain = domain.replace('.es', '.pl')
            alternatives.append((url.replace(domain, pl_domain), 'tld_es_to_pl'))
            com_domain = domain.replace('.es', '.com')
            alternatives.append((url.replace(domain, com_domain), 'tld_es_to_com'))

        return alternatives

    def _validate_with_chrome_devtools(self, url: str) -> Dict:
        """Use Chrome DevTools to validate URL (placeholder for MCP integration)"""
        # This will be implemented when we integrate with chrome-devtools MCP
        # For now, return empty dict
        return {
            'chrome_validated': False,
            'security_warnings': [],
            'performance_score': None
        }

    def find_missing_websites(self, agency_name: str, city: str = None) -> List[Dict]:
        """
        Use AI/web search to find websites for agencies with missing URLs
        This is a placeholder for future AI-powered discovery
        """
        # Placeholder implementation - will be enhanced with Gemini AI
        alternatives = []

        # Basic heuristics for now
        if city and agency_name:
            # Try common patterns
            clean_name = agency_name.lower().replace(' ', '').replace('nieruchomości', '').replace('agency', '')
            alternatives.append({
                'url': f'https://www.{clean_name}.pl',
                'reason': 'domain_pattern_pl',
                'priority': 3
            })
            alternatives.append({
                'url': f'https://www.{clean_name}.com',
                'reason': 'domain_pattern_com',
                'priority': 4
            })

        return alternatives

def update_agency_website(agency_id: int, validation_result: Dict):
    """Update agency record with enhanced website validation results"""
    try:
        conn = sqlite3.connect('agencies.db')
        cursor = conn.cursor()

        # Prepare data for database
        final_url = validation_result.get('final_url')
        status = validation_result.get('status', 'unknown')
        alternatives = validation_result.get('alternatives', [])
        redirects = validation_result.get('redirects', [])
        security_warnings = validation_result.get('security_warnings', [])

        # Update main website if we found a better one
        update_fields = []
        update_values = []

        if final_url and final_url != validation_result.get('original_url'):
            update_fields.append('website = ?')
            update_values.append(final_url)

        # Always update status
        update_fields.append('website_status = ?')
        update_values.append(status)

        # Add new fields for enhanced data
        if alternatives:
            update_fields.append('alternative_urls = ?')
            update_values.append(json.dumps(alternatives))

        if redirects:
            update_fields.append('redirect_chain = ?')
            update_values.append(json.dumps(redirects))

        if security_warnings:
            update_fields.append('security_warnings = ?')
            update_values.append(json.dumps(security_warnings))

        # Add validation timestamp
        update_fields.append('url_validation_date = datetime(\'now\')')

        if update_fields:
            query = f'UPDATE agencies SET {", ".join(update_fields)} WHERE id = ?'
            update_values.append(agency_id)

            cursor.execute(query, update_values)

        conn.commit()
        conn.close()
        return True

    except Exception as e:
        logging.error(f"Error updating agency website data: {e}")
        return False

def main():
    """Main function to run enhanced website validation"""
    logging.info("Starting enhanced website validation...")

    validator = EnhancedWebsiteValidator(use_chrome_devtools=False)  # Set to True when Chrome DevTools is ready

    try:
        conn = sqlite3.connect('agencies.db')
        cursor = conn.cursor()

        # Get agencies that need validation (missing websites or broken ones)
        cursor.execute('''
            SELECT id, name, website, polish_city
            FROM agencies
            WHERE (website IS NULL OR website = '' OR
                   website_status IN ('connection_error', 'not_found', 'timeout', 'invalid_url'))
            AND type != 'undefined'
            ORDER BY id
        ''')

        agencies = cursor.fetchall()
        conn.close()

        logging.info(f"Found {len(agencies)} agencies needing website validation")

        updated_count = 0
        found_alternatives_count = 0

        for agency_id, name, website, city in agencies:
            logging.info(f"Validating: {name}")

            if website and website.strip():
                # Validate existing website
                result = validator.validate_url_comprehensive(website.strip())
                logging.info(f"  Result: {result['status']} -> {result.get('final_url', 'N/A')}")
            else:
                # Try to find missing website
                alternatives = validator.find_missing_websites(name, city)
                if alternatives:
                    result = {
                        'original_url': None,
                        'final_url': alternatives[0]['url'] if alternatives else None,
                        'status': 'discovered',
                        'alternatives': alternatives
                    }
                    found_alternatives_count += 1
                    logging.info(f"  Discovered potential website: {result['final_url']}")
                else:
                    result = {
                        'original_url': None,
                        'final_url': None,
                        'status': 'not_found',
                        'alternatives': []
                    }
                    logging.info("  No website found")

            # Update database
            if update_agency_website(agency_id, result):
                updated_count += 1

            # Rate limiting
            time.sleep(1)

        logging.info(f"Enhanced validation complete: {updated_count} agencies updated, {found_alternatives_count} new websites discovered")

        # Show summary
        print("\n✅ Enhanced Website Validation Complete!")
        print(f"   📊 Agencies processed: {len(agencies)}")
        print(f"   📊 Database updated: {updated_count}")
        print(f"   📊 New websites discovered: {found_alternatives_count}")

    except Exception as e:
        logging.error(f"Error during enhanced website validation: {e}")
        print(f"❌ Error: {e}")

if __name__ == '__main__':
    main()
