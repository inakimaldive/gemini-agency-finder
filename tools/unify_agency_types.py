#!/usr/bin/env python3
"""
Unify Agency Types - Consolidate redundant type tags
"""

import sqlite3
import json
import os
from datetime import datetime

def unify_agency_types():
    """Unify 'both' and 'Spain&Poland' types to 'Spain and Poland'"""
    print("🔄 Starting type unification process...")
    print("=" * 50)

    try:
        conn = sqlite3.connect('agencies.db')
        cursor = conn.cursor()

        # Check current type distribution
        print("📊 Current type distribution:")
        cursor.execute("SELECT type, COUNT(*) FROM agencies GROUP BY type ORDER BY COUNT(*) DESC")
        for row in cursor.fetchall():
            print(f"   {row[0]}: {row[1]}")

        # Count agencies that need updating
        cursor.execute("SELECT COUNT(*) FROM agencies WHERE type IN ('both', 'Spain&Poland')")
        count_to_update = cursor.fetchone()[0]

        if count_to_update == 0:
            print("✅ No agencies need type unification")
            conn.close()
            return 0

        print(f"\n🔄 Updating {count_to_update} agencies from 'both'/'Spain&Poland' to 'Spain and Poland'...")

        # Update the types
        cursor.execute("""
            UPDATE agencies
            SET type = 'Spain and Poland'
            WHERE type IN ('both', 'Spain&Poland')
        """)

        # Add update note to additional_info
        update_note = f" | Type unified to 'Spain and Poland' on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        cursor.execute("""
            UPDATE agencies
            SET additional_info = COALESCE(additional_info, '') || ?
            WHERE type = 'Spain and Poland'
        """, (update_note,))

        conn.commit()

        # Verify the changes
        print("\n📊 Updated type distribution:")
        cursor.execute("SELECT type, COUNT(*) FROM agencies GROUP BY type ORDER BY COUNT(*) DESC")
        for row in cursor.fetchall():
            print(f"   {row[0]}: {row[1]}")

        conn.close()

        print(f"\n✅ Successfully unified {count_to_update} agency types")
        return count_to_update

    except Exception as e:
        print(f"💥 Error during type unification: {e}")
        return 0

def update_website_statuses():
    """Update website statuses for agencies that were enriched"""
    print("\n🔍 Checking for agencies that need website status updates...")

    try:
        conn = sqlite3.connect('agencies.db')
        cursor = conn.cursor()

        # Find agencies that were enriched but might have new working websites
        cursor.execute("""
            SELECT id, name, website, website_status
            FROM agencies
            WHERE additional_info LIKE '%Enriched inactive agency data via Gemini search%'
            AND website IS NOT NULL AND website != ''
            AND (website_status IS NULL OR website_status NOT IN ('active', 'corrected'))
        """
        )

        agencies_to_check = cursor.fetchall()

        if not agencies_to_check:
            print("✅ No agencies need website status updates")
            conn.close()
            return 0

        print(f"📋 Found {len(agencies_to_check)} agencies that may need website status updates")

        # For now, we'll mark them as 'needs_validation' to trigger re-checking
        # In a full implementation, we'd run the website validator here
        updated_count = 0
        for agency_id, name, website, status in agencies_to_check:
            cursor.execute("""
                UPDATE agencies
                SET website_status = 'needs_validation',
                    additional_info = additional_info || ?
                WHERE id = ?
            """, (f" | Website status set to needs_validation for re-checking on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", agency_id))
            updated_count += 1

        conn.commit()
        conn.close()

        print(f"✅ Marked {updated_count} agencies for website status re-validation")
        return updated_count

    except Exception as e:
        print(f"💥 Error updating website statuses: {e}")
        return 0

def main():
    print("🏷️ Agency Type Unification and Status Update Tool")
    print("=" * 55)

    # Unify types
    unified_count = unify_agency_types()

    # Update website statuses
    status_updated_count = update_website_statuses()

    print("\n🎉 Process complete!")
    print(f"   Types unified: {unified_count}")
    print(f"   Status updates: {status_updated_count}")

    if unified_count > 0 or status_updated_count > 0:
        print("\n💡 Next steps:")
        print("   1. Run website validation: python tools/enhanced_website_validator.py")
        print("   2. Update the agencies.json export: python -c \"import json; import sqlite3; conn=sqlite3.connect('agencies.db'); cursor=conn.cursor(); cursor.execute('SELECT * FROM agencies'); data=[dict(zip([col[0] for col in cursor.description], row)) for row in cursor.fetchall()]; conn.close(); json.dump(data, open('agencies.json', 'w'), indent=2, default=str)")
        print("   3. Refresh the web interface to see the changes")

if __name__ == '__main__':
    main()