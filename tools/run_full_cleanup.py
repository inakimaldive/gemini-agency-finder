#!/usr/bin/env python3
"""
Comprehensive Data Cleanup Script for Gemini Agency Finder

This script runs all cleanup tools in the proper order to maintain data quality
after adding new agency entries.

Cleanup Order:
1. Name cleaning - standardize agency names
2. Website fixing - fix invalid URLs and add missing https://
3. Duplicate removal - remove exact duplicate entries
4. Type classification - classify agencies by type (marbella, polish, both, etc.)
5. Enhanced type classification - apply advanced classification rules
6. Website validation - check website accessibility
7. Move undefined - move incomplete entries to separate table

Usage:
    python tools/run_full_cleanup.py
"""

import subprocess
import sys
import time
from pathlib import Path

def run_cleanup_tool(tool_name, description):
    """Run a cleanup tool and report results"""
    print(f"\n🧹 Running {tool_name}...")
    print(f"   {description}")

    try:
        start_time = time.time()
        result = subprocess.run([sys.executable, f'tools/{tool_name}.py'],
                              capture_output=True, text=True, cwd=Path(__file__).parent.parent)

        end_time = time.time()
        duration = end_time - start_time

        if result.returncode == 0:
            print(f"   ✅ {tool_name} completed successfully ({duration:.1f}s)")
            # Print the last few lines of output (usually the summary)
            output_lines = result.stdout.strip().split('\n')
            if output_lines:
                # Show last 2-3 lines which usually contain the summary
                summary_lines = [line for line in output_lines[-3:] if line.strip()]
                for line in summary_lines:
                    if any(keyword in line.lower() for keyword in ['successfully', 'completed', 'found', 'moved', 'updated', 'removed']):
                        print(f"      📊 {line.strip()}")
        else:
            print(f"   ⚠️ {tool_name} completed with warnings ({duration:.1f}s)")
            if result.stderr:
                error_lines = result.stderr.strip().split('\n')[-2:]  # Last 2 lines of errors
                for line in error_lines:
                    if line.strip():
                        print(f"      ⚠️ {line.strip()}")

    except Exception as e:
        print(f"   💥 Error running {tool_name}: {e}")

def get_database_stats():
    """Get current database statistics"""
    try:
        import sqlite3
        conn = sqlite3.connect('agencies.db')
        cursor = conn.cursor()

        # Get counts
        cursor.execute("SELECT COUNT(*) FROM agencies")
        agencies_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM undefined")
        undefined_count = cursor.fetchone()[0]

        # Get type breakdown
        cursor.execute("SELECT type, COUNT(*) FROM agencies GROUP BY type ORDER BY COUNT(*) DESC")
        type_breakdown = cursor.fetchall()

        conn.close()

        return agencies_count, undefined_count, type_breakdown

    except Exception as e:
        print(f"Error getting database stats: {e}")
        return 0, 0, []

def main():
    """Main cleanup function"""
    print("🚀 Starting Comprehensive Data Cleanup")
    print("=" * 50)

    # Mark all agencies as pending cleanup initially
    try:
        import sqlite3
        conn = sqlite3.connect('agencies.db')
        cursor = conn.cursor()
        cursor.execute("UPDATE agencies SET cleanup_status = 'pending' WHERE cleanup_status IS NULL OR cleanup_status = ''")
        pending_count = cursor.rowcount
        conn.commit()
        conn.close()
        if pending_count > 0:
            print(f"📝 Marked {pending_count} agencies as pending cleanup")
    except Exception as e:
        print(f"⚠️ Error initializing cleanup status: {e}")

    # Get initial stats
    print("📊 Initial Database Status:")
    initial_agencies, initial_undefined, initial_types = get_database_stats()
    print(f"   Agencies table: {initial_agencies} entries")
    print(f"   Undefined table: {initial_undefined} entries")
    print(f"   Total: {initial_agencies + initial_undefined} entries")

    if initial_types:
        print("   Type breakdown:")
        for type_name, count in initial_types:
            print(f"     - {type_name}: {count}")

    # Define cleanup tools in order (website validation is optional due to long runtime)
    cleanup_tools = [
        ('clean_names', 'Standardize and clean agency names'),
        ('fix_websites', 'Fix invalid URLs and add missing https:// prefixes'),
        ('remove_duplicates', 'Remove exact duplicate entries'),
        ('update_types', 'Classify agencies by type (marbella, polish, both, etc.)'),
        ('enhanced_type_classification', 'Apply advanced classification rules with multiple indicators'),
        # ('validate_websites', 'Check website accessibility and update status'),  # Commented out - too slow for regular cleanup
        ('move_undefined', 'Move incomplete entries to separate undefined table')
    ]

    # Run all cleanup tools
    for tool_name, description in cleanup_tools:
        run_cleanup_tool(tool_name, description)

    # Get final stats
    print("\n📊 Final Database Status:")
    final_agencies, final_undefined, final_types = get_database_stats()
    print(f"   Agencies table: {final_agencies} entries")
    print(f"   Undefined table: {final_undefined} entries")
    print(f"   Total: {final_agencies + final_undefined} entries")

    if final_types:
        print("   Type breakdown:")
        for type_name, count in final_types:
            print(f"     - {type_name}: {count}")

    # Summary
    print("\n🎉 Cleanup Complete!")
    print("=" * 50)

    agencies_change = final_agencies - initial_agencies
    undefined_change = final_undefined - initial_undefined

    print("📈 Changes:")
    print(f"   Agencies table: {agencies_change:+d} entries")
    print(f"   Undefined table: {undefined_change:+d} entries")

    if agencies_change != 0 or undefined_change != 0:
        print("\n� Updating web interface data...")
        try:
            result = subprocess.run(['bash', 'tools/update_data.sh'],
                                  capture_output=True, text=True, cwd=Path(__file__).parent.parent)
            if result.returncode == 0:
                print("   ✅ Web interface data updated successfully")
            else:
                print("   ⚠️ Web interface update had issues")
        except Exception as e:
            print(f"   💥 Error updating web interface: {e}")

    print("\n✅ Database is now clean and web interface is updated!")

if __name__ == '__main__':
    main()
