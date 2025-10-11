#!/usr/bin/env python3
"""
Enhanced script to classify agencies based on multiple indicators:
- Phone numbers (+48 Polish vs +34 Spanish)
- Website domains (.pl vs .es)
- Address locations
- Description keywords
"""

import sqlite3
import re
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def analyze_phone_number(phone):
    """Analyze phone number for country indicators"""
    if not phone:
        return None

    phone_str = str(phone).strip()

    # Polish indicators
    if phone_str.startswith('+48') or phone_str.startswith('48'):
        return 'polish'
    if 'poland' in phone_str.lower() or 'polska' in phone_str.lower():
        return 'polish'

    # Spanish indicators
    if phone_str.startswith('+34') or phone_str.startswith('34'):
        return 'spain'
    if 'spain' in phone_str.lower() or 'españa' in phone_str.lower():
        return 'spain'

    return None

def analyze_website_domain(website):
    """Analyze website domain for location indicators"""
    if not website:
        return None

    website_lower = website.lower()

    # Polish domains
    if '.pl' in website_lower or 'poland' in website_lower or 'polska' in website_lower:
        return 'polish'

    # Spanish domains
    if '.es' in website_lower or 'spain' in website_lower or 'españa' in website_lower:
        return 'spain'

    # Costa del Sol / Marbella specific
    if any(term in website_lower for term in ['marbella', 'costadelsol', 'costa-del-sol', 'malaga', 'andalusia']):
        return 'spain'

    return None

def analyze_address(address):
    """Analyze address for location indicators"""
    if not address:
        return None

    address_lower = address.lower()

    # Polish cities
    polish_cities = [
        'warsaw', 'krakow', 'lodz', 'wroclaw', 'poznan', 'gdansk', 'szczecin',
        'bydgoszcz', 'lublin', 'katowice', 'bialystok', 'gdynia', 'czestochowa',
        'radom', 'sosnowiec', 'torun', 'kielce', 'rzeszow', 'gliwice', 'zabrze',
        'olsztyn', 'bielsko-biala', 'bytom', 'zielona gora', 'rybnik', 'ruda slaska',
        'opole', 'tichy', 'gorzow wielkopolski', 'dabrowa gornicza', 'plock',
        'elblag', 'walbrzych', 'tarnow', 'chorzow', 'kalisz', 'legnica', 'grudziadz',
        'slupsk', 'jastrzebie-zdroj', 'nowy sacz', 'jaworzno', 'jelenia gora',
        'ostrow mazowiecka', 'swidnica', 'stalowa wola', 'piekary slaskie',
        'lubin', 'zamosc', 'poland', 'polska'
    ]

    if any(city in address_lower for city in polish_cities):
        return 'polish'

    # Spanish locations
    spanish_locations = [
        'marbella', 'malaga', 'andalusia', 'costa del sol', 'costa blanca',
        'alicante', 'valencia', 'barcelona', 'madrid', 'spain', 'españa',
        'puerto banus', 'estepona', 'san pedro', 'fuengirola', 'torremolinos'
    ]

    if any(location in address_lower for location in spanish_locations):
        return 'spain'

    return None

def analyze_description(description):
    """Analyze description for location indicators"""
    if not description:
        return None

    desc_lower = description.lower()

    # Polish indicators
    polish_keywords = [
        'poland', 'polska', 'polish', 'polski', 'warszawa', 'kraków', 'łódź',
        'wrocław', 'poznań', 'gdańsk', 'szczecin', 'polacy', 'polak', 'polka'
    ]

    if any(keyword in desc_lower for keyword in polish_keywords):
        return 'polish'

    # Spanish/Marbella indicators
    spanish_keywords = [
        'spain', 'españa', 'spanish', 'marbella', 'costa del sol', 'andalusia',
        'malaga', 'puerto banus', 'español', 'española', 'hiszpania'
    ]

    if any(keyword in desc_lower for keyword in spanish_keywords):
        return 'spain'

    return None

def determine_enhanced_type(name, website, phone, address, description, current_type):
    """Determine agency type using multiple indicators"""
    indicators = {'polish': 0, 'spain': 0}

    # Analyze each field
    phone_result = analyze_phone_number(phone)
    if phone_result:
        indicators[phone_result] += 2  # Phone is strong indicator

    website_result = analyze_website_domain(website)
    if website_result:
        indicators[website_result] += 2  # Website is strong indicator

    address_result = analyze_address(address)
    if address_result:
        indicators[address_result] += 1

    description_result = analyze_description(description)
    if description_result:
        indicators[description_result] += 1

    # Analyze name for additional clues
    if name:
        name_lower = name.lower()
        if any(term in name_lower for term in ['polska', 'polish', 'nieruchomości']):
            indicators['polish'] += 1
        if any(term in name_lower for term in ['marbella', 'spain', 'inmobiliaria', 'costa']):
            indicators['spain'] += 1

    # Determine final classification
    polish_score = indicators['polish']
    spain_score = indicators['spain']

    # Strong indicators for both = spain&poland
    if polish_score >= 2 and spain_score >= 2:
        return 'spain&poland'
    elif polish_score >= 1 and spain_score >= 1:
        return 'both'
    elif polish_score > spain_score:
        return 'polish'
    elif spain_score > polish_score:
        return 'marbella'
    else:
        # No clear indicators, keep current type or mark as gemini_discovered
        return current_type if current_type != 'gemini_discovered' else 'gemini_discovered'

def main():
    """Main function to perform enhanced type classification"""
    logging.info("Starting enhanced type classification...")

    try:
        conn = sqlite3.connect('agencies.db')
        cursor = conn.cursor()

        # Get all agencies for re-classification (process recent entries first)
        cursor.execute('''
            SELECT id, name, website, phone, address, description, type
            FROM agencies
            ORDER BY id DESC
        ''')

        agencies = cursor.fetchall()
        logging.info(f"Found {len(agencies)} agencies for enhanced classification")

        updated_count = 0
        type_changes = {}

        for agency_id, name, website, phone, address, description, current_type in agencies:
            new_type = determine_enhanced_type(name, website, phone, address, description, current_type)

            if new_type != current_type:
                logging.info(f"Reclassifying '{name}' from '{current_type}' to '{new_type}'")
                cursor.execute('''
                    UPDATE agencies
                    SET type = ?
                    WHERE id = ?
                ''', (new_type, agency_id))

                # Track changes
                change_key = f"{current_type} -> {new_type}"
                type_changes[change_key] = type_changes.get(change_key, 0) + 1

                updated_count += 1

        conn.commit()
        conn.close()

        logging.info(f"Successfully updated {updated_count} agencies with enhanced classification")

        # Show summary of changes
        logging.info("Classification changes summary:")
        for change, count in sorted(type_changes.items()):
            logging.info(f"  {change}: {count} agencies")

        # Show final type distribution
        conn = sqlite3.connect('agencies.db')
        cursor = conn.cursor()
        cursor.execute('''
            SELECT type, COUNT(*) as count
            FROM agencies
            GROUP BY type
            ORDER BY count DESC
        ''')

        final_types = cursor.fetchall()
        conn.close()

        logging.info("Final type distribution:")
        for agency_type, count in final_types:
            logging.info(f"  {agency_type}: {count} agencies")

    except Exception as e:
        logging.error(f"Error during enhanced type classification: {e}")

if __name__ == '__main__':
    main()
