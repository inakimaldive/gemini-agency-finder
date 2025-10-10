# Gemini Agency Finder - Web Interface

A static web interface for exploring the Gemini Agency Finder database of real estate agencies specializing in Costa del Sol properties.

## 🌐 Live Demo

[View the interactive database](https://yourusername.github.io/gemini-agency-finder/)

## 📊 Database Overview

This interface displays **288 real estate agencies** across four categories:
- **Marbella Based** (149): Agencies with physical locations in Marbella, Spain
- **Spain & Poland** (75): Agencies serving both Spanish and Polish markets
- **Polish Agencies** (54): Polish agencies specializing in Costa del Sol properties
- **AI Discovered** (10): Agencies discovered via Google Gemini AI search with insufficient classification data

## ✨ Features

### Combined Dashboard Overview
- **Chart & Statistics Side-by-Side**: Distribution chart on left, statistics cards on right
- **Mobile-First Responsive**: Chart stacks above cards on mobile, side-by-side on desktop
- **Real-time Statistics**: Agency counts by type with last updated timestamp
- **Custom Padding**: 35px padding on large screens for optimal readability

### Advanced Data Table
- **Search**: Full-text search across all agency information
- **Filter**: Filter by agency type, location, or any field
- **Sort**: Click column headers to sort data
- **Pagination**: Navigate through results (25 per page)
- **Responsive**: Mobile-friendly design with collapsible columns

### Export Functionality
- **CSV Export**: Download filtered results as CSV file
- **Custom Filename**: Includes export date in filename
- **Filtered Data**: Export only visible/search results

### Data Visualization
- **Color-coded Rows**: Different background colors by agency type
- **Badge System**: Visual type indicators (Marbella, Polish, AI Found)
- **Interactive Chart**: Doughnut chart showing agency distribution
- **Hover Effects**: Enhanced user interaction

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

## 🌐 Sharing the Static Page Using GitHub

This project is designed as a static website that can be easily shared and hosted for free using GitHub Pages. Follow these steps to make your agency database publicly accessible:

### Step 1: Create a GitHub Repository
1. Go to [GitHub.com](https://github.com) and sign in
2. Click the "+" icon → "New repository"
3. Name it `gemini-agency-finder` (or your preferred name)
4. Make it public (so others can view it)
5. Don't initialize with README (we already have one)
6. Click "Create repository"

### Step 2: Upload Your Files
Upload all project files to your GitHub repository:
- `index.html` - The main web interface
- `agencies.json` - The agency data
- `README.md` - This documentation
- Any other files in your project

### Step 3: Enable GitHub Pages
1. Go to your repository settings (click "Settings" tab)
2. Scroll down to "Pages" section
3. Under "Source", select "Deploy from a branch"
4. Under "Branch", select "main" (or "master") and "/ (root)"
5. Click "Save"

### Step 4: Get Your Live URL
After a few minutes, GitHub will provide a live URL for your site. It will be:
```
https://yourusername.github.io/gemini-agency-finder/
```

### Step 5: Share Your Database
- Share the GitHub Pages URL with others
- The site works completely offline once loaded
- No server or hosting costs required
- Updates automatically when you push new data

### Updating the Live Site
Whenever you update the agency data:

1. Run the update script:
   ```bash
   ./update_data.sh
   ```

2. Commit and push changes:
   ```bash
   git add agencies.json
   git commit -m "Update agency database - $(date +%Y-%m-%d)"
   git push
   ```

3. GitHub Pages will automatically update within minutes

### Benefits of GitHub Pages Hosting
- **Free**: No hosting costs
- **Fast**: Global CDN delivery
- **Reliable**: 99.9% uptime SLA
- **SEO-friendly**: Search engines can index your content
- **Version controlled**: Full git history of data changes
- **Collaborative**: Others can contribute via pull requests

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
**Total Agencies**: 288
