#!/usr/bin/env python3
"""
Move agencies with missing information to a separate table.
"""

import sqlite3

def move_missing_info():
    """Move agencies with no website, phone, address, or description to a new table."""
    print("🚚 Starting to move agencies with missing information...")
    print("=" * 50)

    try:
        conn = sqlite3.connect('agencies.db')
        cursor = conn.cursor()

        # Create the missing_info table if it doesn't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS missing_info AS
            SELECT * FROM agencies WHERE 1=0
        """)

        # Select agencies with missing information
        cursor.execute("""
            SELECT * FROM agencies
            WHERE (website IS NULL OR website = '')
            AND (phone IS NULL OR phone = '')
            AND (address IS NULL OR address = '')
            AND (description IS NULL OR description = '')
        """)
        missing_info_agencies = cursor.fetchall()
        moved_count = len(missing_info_agencies)

        if moved_count == 0:
            print("✅ No agencies with missing information found.")
            conn.close()
            return 0

        print(f"🚚 Found {moved_count} agencies to move.")

        # Get column names from the agencies table
        cursor.execute("PRAGMA table_info(agencies)")
        columns = [col[1] for col in cursor.fetchall()]
        column_names = ", ".join(columns)
        placeholders = ", ".join(["?" for _ in columns])

        # Insert the selected agencies into the missing_info table
        cursor.executemany(f"INSERT INTO missing_info ({column_names}) VALUES ({placeholders})", missing_info_agencies)

        # Delete the moved agencies from the agencies table
        cursor.execute("""
            DELETE FROM agencies
            WHERE (website IS NULL OR website = '')
            AND (phone IS NULL OR phone = '')
            AND (address IS NULL OR address = '')
            AND (description IS NULL OR description = '')
        """)

        conn.commit()
        conn.close()

        print(f"✅ Successfully moved {moved_count} agencies to the 'missing_info' table.")
        return moved_count

    except Exception as e:
        print(f"💥 Error moving agencies: {e}")
        return 0

if __name__ == '__main__':
    move_missing_info()
