#!/bin/bash

# Gemini Agency Finder - Data Update Script
# This script exports the latest agency data from SQLite to JSON format
# for the web interface

echo "🔄 Updating agency data for web interface..."

# Check if database exists
if [ ! -f "agencies.db" ]; then
    echo "❌ Error: agencies.db not found in current directory"
    echo "Please run this script from the gemini-agency-finder directory"
    exit 1
fi

# Export data to JSON
echo "📊 Exporting data from SQLite to JSON..."
sqlite3 agencies.db -json "SELECT * FROM agencies ORDER BY name;" > agencies.json

if [ $? -eq 0 ]; then
    echo "✅ Data export successful"

    # Get statistics
    TOTAL_AGENCIES=$(sqlite3 agencies.db "SELECT COUNT(*) FROM agencies;")
    MARBELLA_COUNT=$(sqlite3 agencies.db "SELECT COUNT(*) FROM agencies WHERE type='marbella';")
    POLISH_COUNT=$(sqlite3 agencies.db "SELECT COUNT(*) FROM agencies WHERE type='polish';")
    GEMINI_COUNT=$(sqlite3 agencies.db "SELECT COUNT(*) FROM agencies WHERE type='gemini_discovered';")

    echo "📈 Database Statistics:"
    echo "   Total Agencies: $TOTAL_AGENCIES"
    echo "   Marbella Based: $MARBELLA_COUNT"
    echo "   Polish Agencies: $POLISH_COUNT"
    echo "   AI Discovered: $GEMINI_COUNT"

    # Check file size
    FILE_SIZE=$(du -h agencies.json | cut -f1)
    echo "📁 JSON file size: $FILE_SIZE"

    echo ""
    echo "🎉 Data update complete!"
    echo "The web interface (index.html) will automatically use the updated data."
    echo ""
    echo "To deploy changes:"
    echo "  git add agencies.json"
    echo "  git commit -m 'Update agency database - $(date +%Y-%m-%d)'"
    echo "  git push"
else
    echo "❌ Error: Failed to export data"
    exit 1
fi
