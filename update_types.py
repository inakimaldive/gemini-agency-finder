#!/usr/bin/env python3
"""
Script to update the type field for gemini_discovered agencies
to either 'polish' or 'marbella' based on phone country codes and website domains.
"""

import sqlite3
import re
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def determine_agency_type(name, website, phone, address, description):
    """Determine if agency is Polish, Marbella-based, both, or keep as gemini_discovered"""

    indicators = {'polish': 0, 'marbella': 0}

    # Check phone country codes
    if phone:
        if phone.startswith('+48') or phone.startswith('48'):
            indicators['polish'] += 1
        elif phone.startswith('+34') or phone.startswith('34'):
            indicators['marbella'] += 1

    # Check website domains
    if website:
        domain = website.lower()
        if '.pl' in domain or 'poland' in domain:
            indicators['polish'] += 1
        elif '.es' in domain or 'spain' in domain or 'marbella' in domain:
            indicators['marbella'] += 1

    # Check address for location indicators
    if address:
        address_lower = address.lower()
        if 'poland' in address_lower or any(city in address_lower for city in ['warsaw', 'krakow', 'lodz', 'wroclaw', 'poznan', 'gdansk', 'szczecin', 'bydgoszcz', 'lublin', 'katowice', 'bialystok', 'gdynia', 'czestochowa', 'radom', 'sosnowiec', 'torun', 'kielce', 'rzeszow', 'gliwice', 'zabrze', 'olsztyn', 'bielsko-biala', 'bytom', 'zielona gora', 'rybnik', 'ruda slaska', 'opole', 'tichy', 'gorzow wielkopolski', 'dabrowa gornicza', 'plock', 'elblag', 'walbrzych', 'tarnow', 'chorzow', 'koscian', 'kalisz', 'legnica', 'grudziadz', 'slupsk', 'jastrzebie-zdroj', 'nowy sacz', 'jaworzno', 'jelenia gora', 'ostrow mazowiecka', 'swidnica', 'stalowa wola', 'piekary slaskie', 'lubin', 'zamosc']):
            indicators['polish'] += 1
        elif 'spain' in address_lower or 'marbella' in address_lower or 'costa del sol' in address_lower or 'malaga' in address_lower:
            indicators['marbella'] += 1

    # Check description for location indicators
    if description:
        desc_lower = description.lower()
        if 'polish' in desc_lower or 'polska' in desc_lower or 'poland' in desc_lower:
            indicators['polish'] += 1
        elif 'marbella' in desc_lower or 'spain' in desc_lower or 'costa del sol' in desc_lower:
            indicators['marbella'] += 1

    # Check name for location indicators
    if name:
        name_lower = name.lower()
        if 'polish' in name_lower or 'polska' in name_lower or 'nieruchomosci' in name_lower:
            indicators['polish'] += 1
        elif 'marbella' in name_lower or 'costa' in name_lower or 'inmobiliaria' in name_lower:
            indicators['marbella'] += 1

    # Determine classification based on indicators
    polish_score = indicators['polish']
    marbella_score = indicators['marbella']

    if polish_score > 0 and marbella_score > 0:
        return 'spain&poland'
    elif polish_score > 0:
        return 'polish'
    elif marbella_score > 0:
        return 'marbella'
    else:
        # No clear indicators found
        return 'gemini_discovered'

def main():
    """Main function to update agency types"""
    logging.info("Starting type classification for gemini_discovered agencies...")

    try:
        conn = sqlite3.connect('agencies.db')
        cursor = conn.cursor()

        # First, reset all previously classified agencies back to gemini_discovered
        cursor.execute('''
            UPDATE agencies
            SET type = 'gemini_discovered'
            WHERE type IN ('polish', 'marbella', 'spain&poland')
        ''')
        reset_count = cursor.rowcount
        logging.info(f"Reset {reset_count} agencies back to 'gemini_discovered' for reclassification")

        # Get all gemini_discovered agencies
        cursor.execute('''
            SELECT id, name, website, phone, address, description
            FROM agencies
            WHERE type = 'gemini_discovered'
            ORDER BY id
        ''')

        agencies = cursor.fetchall()
        logging.info(f"Found {len(agencies)} gemini_discovered agencies to classify")

        updated_count = 0

        for agency_id, name, website, phone, address, description in agencies:
            new_type = determine_agency_type(name, website, phone, address, description)

            logging.info(f"Classifying '{name}' as '{new_type}' (phone: {phone}, website: {website})")

            # Update the database
            cursor.execute('''
                UPDATE agencies
                SET type = ?
                WHERE id = ?
            ''', (new_type, agency_id))

            updated_count += 1

        conn.commit()
        conn.close()

        logging.info(f"Successfully updated {updated_count} agencies with proper type classification")

        # Show summary
        conn = sqlite3.connect('agencies.db')
        cursor = conn.cursor()
        cursor.execute("SELECT type, COUNT(*) FROM agencies GROUP BY type ORDER BY COUNT(*) DESC")
        results = cursor.fetchall()
        conn.close()

        logging.info("Final classification summary:")
        for agency_type, count in results:
            logging.info(f"  {agency_type}: {count} agencies")

    except Exception as e:
        logging.error(f"Error during type classification: {e}")

if __name__ == '__main__':
    main()
