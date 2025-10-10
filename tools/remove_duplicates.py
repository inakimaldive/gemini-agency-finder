#!/usr/bin/env python3
"""
Script to identify and remove duplicate agencies from the database
"""

import sqlite3
import logging
from collections import defaultdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def calculate_completeness_score(agency):
    """Calculate a completeness score for an agency based on filled fields"""
    score = 0
    _, name, _, website, phone, address, description, additional_info, _ = agency

    if name and name.strip(): score += 1
    if website and website.strip(): score += 2  # Website is most important
    if phone and phone.strip(): score += 1
    if address and address.strip(): score += 1
    if description and description.strip(): score += 1
    if additional_info and additional_info.strip(): score += 0.5

    return score

def find_duplicates():
    """Find duplicate agencies based on name similarity"""
    conn = sqlite3.connect('agencies.db')
    cursor = conn.cursor()

    # Get all agencies
    cursor.execute('SELECT id, name, type, website, phone, address, description, additional_info, website_status FROM agencies ORDER BY name')
    agencies = cursor.fetchall()
    conn.close()

    # Group by normalized name (lowercase, remove extra spaces)
    name_groups = defaultdict(list)

    for agency in agencies:
        agency_id, name, *rest = agency
        if name:
            # Normalize name for comparison
            normalized_name = ' '.join(name.lower().split())
            name_groups[normalized_name].append(agency)

    # Find groups with duplicates
    duplicates = []
    for normalized_name, group in name_groups.items():
        if len(group) > 1:
            duplicates.append((normalized_name, group))

    return duplicates

def remove_duplicates():
    """Remove duplicate agencies, keeping the most complete one"""
    logging.info("Starting duplicate removal process...")

    duplicates = find_duplicates()
    total_duplicates_removed = 0

    if not duplicates:
        logging.info("No duplicates found")
        return 0

    conn = sqlite3.connect('agencies.db')
    cursor = conn.cursor()

    for normalized_name, group in duplicates:
        if len(group) <= 1:
            continue

        logging.info(f"Found {len(group)} duplicates for: '{normalized_name}'")

        # Sort by completeness score (highest first)
        scored_group = [(agency, calculate_completeness_score(agency)) for agency in group]
        scored_group.sort(key=lambda x: x[1], reverse=True)

        # Keep the most complete one
        keep_agency = scored_group[0][0]
        keep_id = keep_agency[0]

        # Remove the others
        remove_ids = [agency[0] for agency, _ in scored_group[1:]]

        if remove_ids:
            cursor.execute(f'DELETE FROM agencies WHERE id IN ({",".join("?" * len(remove_ids))})', remove_ids)
            total_duplicates_removed += len(remove_ids)

            logging.info(f"  Kept: {keep_agency[1]} (ID: {keep_id}, score: {scored_group[0][1]:.1f})")
            for remove_id in remove_ids:
                logging.info(f"  Removed duplicate ID: {remove_id}")

    conn.commit()
    conn.close()

    logging.info(f"Successfully removed {total_duplicates_removed} duplicate entries")
    return total_duplicates_removed

def main():
    """Main function"""
    duplicates = find_duplicates()

    if not duplicates:
        logging.info("No duplicates found in the database")
        return

    logging.info(f"Found {len(duplicates)} groups of duplicates")

    # Show summary
    total_duplicate_entries = sum(len(group) for _, group in duplicates)
    logging.info(f"Total duplicate entries: {total_duplicate_entries}")

    # Ask user if they want to proceed
    print(f"\nFound {len(duplicates)} groups of duplicates with {total_duplicate_entries} total entries.")
    print("This will keep the most complete entry from each group and remove the rest.")

    # For now, just proceed automatically
    removed = remove_duplicates()
    print(f"\nRemoved {removed} duplicate entries.")

if __name__ == '__main__':
    main()
