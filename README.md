# Gemini Agency Finder

A standalone tool for discovering real estate agencies in Marbella using Google's Gemini AI.

## Files Included

- `gemini_agency_finder.py` - Main script for agency discovery
- `agencies.db` - SQLite database containing existing agencies (249 agencies)
- `README.md` - This documentation file

## Usage

### Basic Discovery
```bash
python gemini_agency_finder.py
```

### Targeted Polish Search (Default 50 agencies)
```bash
python gemini_agency_finder.py --targeted
```

### Targeted Polish Search (Custom target)
```bash
python gemini_agency_finder.py --targeted 100
```

## Requirements

- Python 3.x
- Google Gemini CLI tool (`gemini`) installed and configured
- SQLite3

## Output

- New agencies are saved to `agencies.db`
- Logs are written to `gemini_agency_finder.log`
- Progress is displayed in the console

## Database Schema

The `agencies` table contains:
- `name`: Agency name
- `type`: Discovery method (will be 'gemini_discovered')
- `website`: Agency website URL
- `phone`: Contact phone number
- `address`: Physical address
- `description`: Agency description
- `additional_info`: Discovery metadata and timestamp
