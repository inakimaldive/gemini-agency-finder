# Gemini Agency Finder - Web Interface

A static web interface for exploring the Gemini Agency Finder database of real estate agencies specializing in Costa del Sol properties.

## 🌐 Live Demo

[View the interactive database](https://yourusername.github.io/gemini-agency-finder/)

## 📊 Database Overview

This interface displays **515 real estate agencies** across three categories:
- **Marbella Based** (154): Agencies with physical locations in Marbella
- **Polish Agencies** (81): Polish agencies specializing in Costa del Sol properties
- **AI Discovered** (280): Agencies discovered via Google Gemini AI search

## ✨ Features

### Interactive Dashboard
- Real-time statistics with agency counts by type
- Visual distribution chart (doughnut chart)
- Last updated timestamp

### Advanced Data Table
- **Search**: Full-text search across all agency information
- **Filter**: Filter by agency type, location, or any field
- **Sort**: Click column headers to sort data
- **Pagination**: Navigate through results (25 per page)
- **Responsive**: Mobile-friendly design

### Export Functionality
- **CSV Export**: Download filtered results as CSV file
- **Custom Filename**: Includes export date in filename

### Data Visualization
- Color-coded rows by agency type
- Badge system for quick type identification
- Hover effects and responsive design

## 🛠️ Technical Stack

- **Frontend**: HTML5, CSS3, JavaScript (ES6+)
- **Libraries**:
  - [Bootstrap 5](https://getbootstrap.com/) - Responsive UI framework
  - [DataTables](https://datatables.net/) - Interactive table functionality
  - [Chart.js](https://www.chartjs.org/) - Data visualization
  - [jQuery](https://jquery.com/) - DOM manipulation
- **Data Format**: JSON (exported from SQLite database)
- **Hosting**: GitHub Pages (static hosting)

## 📁 Project Structure

```
gemini-agency-finder/
├── index.html          # Main web interface
├── agencies.json       # Agency data (JSON format)
├── README.md           # This documentation
├── .gitignore         # Git ignore rules
└── assets/            # Static assets (if needed)
```

## 🚀 Quick Start

### For Users
1. Visit the [live demo](https://yourusername.github.io/gemini-agency-finder/)
2. Use the search box to find specific agencies
3. Filter by agency type using the table controls
4. Export data using the CSV export button

### For Developers

#### Prerequisites
- Python 3.x (for data export)
- SQLite3 (for database operations)
- Git (for version control)

#### Local Development
1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/gemini-agency-finder.git
   cd gemini-agency-finder
   ```

2. Export fresh data from SQLite database:
   ```bash
   sqlite3 agencies.db -json "SELECT * FROM agencies ORDER BY name;" > agencies.json
   ```

3. Open `index.html` in your browser or serve locally:
   ```bash
   python -m http.server 8000
   # Visit http://localhost:8000
   ```

## 📊 Data Schema

The agency data includes the following fields:

| Field | Description | Example |
|-------|-------------|---------|
| `name` | Agency name | "Costa del Sol Properties" |
| `type` | Agency category | "marbella", "polish", "gemini_discovered" |
| `website` | Agency website URL | "https://example.com" |
| `phone` | Contact phone number | "+34 123 456 789" |
| `address` | Physical address | "Calle Mayor 123, Marbella" |
| `description` | Agency description | "Specializing in luxury properties..." |
| `additional_info` | Discovery metadata | "Discovered via Gemini AI on 2025-10-10" |

## 🔄 Data Updates

To update the database with fresh data:

1. Run the agency discovery script:
   ```bash
   python gemini_agency_finder.py --targeted 50
   ```

2. Export updated data to JSON:
   ```bash
   sqlite3 agencies.db -json "SELECT * FROM agencies ORDER BY name;" > agencies.json
   ```

3. Commit and push changes:
   ```bash
   git add agencies.json
   git commit -m "Update agency database - $(date +%Y-%m-%d)"
   git push
   ```

## 🎨 Customization

### Styling
The interface uses Bootstrap 5 with custom CSS. Modify styles in the `<style>` section of `index.html`.

### Functionality
JavaScript code is embedded in `index.html`. Key functions:
- `loadAgenciesData()` - Loads JSON data
- `initializeDashboard()` - Creates statistics and charts
- `initializeTable()` - Sets up DataTables functionality

### Adding New Features
1. Edit the HTML structure in `index.html`
2. Add corresponding JavaScript functionality
3. Test locally before deploying

## 📈 Performance

- **File Size**: ~173KB JSON data file
- **Load Time**: <2 seconds on modern connections
- **Mobile Optimized**: Responsive design works on all devices
- **Search Performance**: Client-side search with instant results

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes
4. Test locally
5. Submit a pull request

## 📄 License

This project is part of the Gemini Agency Finder tool. See the main repository for licensing information.

## 📞 Support

For questions or issues:
- Open an issue on GitHub
- Check the main repository documentation
- Review the console logs for JavaScript errors

## 🔍 Data Source

This database is maintained by the Gemini Agency Finder project, which uses AI-powered search to discover real estate agencies working with Costa del Sol properties. The data includes agencies physically located in Marbella, Polish agencies specializing in Spanish properties, and agencies discovered through automated AI searches.

**Last Updated**: October 10, 2025
**Total Agencies**: 515
