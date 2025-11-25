# 🔍 Yelp Business Lead Scraper

**Professional lead generation tool with web interface and REST API for n8n integration**

## ✨ New Features

- 🌐 **Web Interface** - Modern UI for easy scraping without code
- 🔌 **REST API** - Full API for n8n, Zapier, and automation tools
- 🎯 **Customizable Search** - Change category and location on-the-fly
- 📊 **Real-time Status** - Monitor job progress live
- 💾 **Multiple Formats** - Export as CSV or JSON
- 🚀 **Async Jobs** - Run scraping in background

## 🚀 Quick Start

### 1. Installation

```bash
# Install dependencies
pip install -r requirements.txt
```

### 2. Start the Web Server

```bash
python app.py
```

Server starts on `http://localhost:5000`

### 3. Use the Web Interface

Open `http://localhost:5000` in your browser:

1. Enter **business category** (e.g., "plumbers", "general contractors")
2. Enter **location** (e.g., "Atlanta, GA")
3. Set **number of results** (1-100)
4. Click **"Start Scraping"**

Results appear in real-time with download buttons!

## 📖 Usage Modes

### Mode 1: Web Interface (Easiest) ⭐

Perfect for non-technical users:
- Open `http://localhost:5000`
- Fill form and click "Start Scraping"
- Download CSV/JSON when complete

### Mode 2: Command Line

```bash
# Default settings
python scraper.py

# Custom parameters
python scraper.py --category "plumbers" --location "Dallas, TX" --num-results 50
```

### Mode 3: REST API (For n8n)

```bash
# Start a job
curl -X POST http://localhost:5000/api/scrape \
  -H "Content-Type: application/json" \
  -d '{"category": "plumbers", "location": "Austin, TX", "num_results": 50}'

# Check status
curl http://localhost:5000/api/status/{job_id}

# Get results
curl http://localhost:5000/api/results/{job_id}
```

See [API_DOCUMENTATION.md](API_DOCUMENTATION.md) for complete API reference.

## 🔌 n8n Integration

### Quick Setup

1. **Add HTTP Request Node** (Start Job)
   - Method: POST
   - URL: `http://localhost:5000/api/scrape`
   - Body: `{"category": "{{ $json.category }}", "location": "{{ $json.location }}", "num_results": 50}`

2. **Add Wait Node** (30 seconds)

3. **Add HTTP Request Node** (Get Results)
   - Method: GET
   - URL: `http://localhost:5000/api/results/{{ $json.job_id }}`

4. **Process Leads**
   - Use Split Into Items
   - Send to CRM, email, or database

See [API_DOCUMENTATION.md](API_DOCUMENTATION.md) for detailed n8n workflow.

## 📊 Output Format

### CSV Format
```csv
website,company,emails,phones,contact_pages,scraped_at,status
https://example.com,ABC Plumbing,"contact@example.com","(555) 123-4567",https://example.com/contact,2024-11-23,success
```

### JSON Format
```json
{
  "company": "ABC Plumbing",
  "website": "https://example.com",
  "emails": ["contact@example.com"],
  "phones": ["(555) 123-4567"],
  "status": "success"
}
```

## 📈 Scaling to 3-5K Leads/Month

### Strategy 1: Multiple Locations
- 10 cities × 50 businesses = 500 leads/week
- 4 weeks = 2,000 leads/month

### Strategy 2: Multiple Categories
- General contractors, plumbers, electricians, roofers, HVAC
- 5 categories × 50 businesses × 10 cities = 2,500 leads

### Strategy 3: Automate with n8n
- Set up Cron trigger for daily scraping
- Automatically add leads to your CRM
- Different city/category each day

**Top Markets:**
- Atlanta, GA • Dallas, TX • Houston, TX
- Phoenix, AZ • Miami, FL • Seattle, WA
- Denver, CO • Austin, TX • Chicago, IL

## 🛠️ Configuration

| Parameter | Description | Example |
|-----------|-------------|---------|
| `category` | Business type | "general contractors", "plumbers" |
| `location` | City/state | "Atlanta, GA", "New York, NY" |
| `num_results` | Number of results | 1-100 (default: 50) |

## 🔧 Troubleshooting

### Chrome Crashes
✅ **Fixed:** 30-second timeout prevents hangs. Auto-saves every 10 businesses.

### Unicode Errors on Windows
✅ **Fixed:** Now uses ASCII-compatible characters.

### No Results Found
- Check if Yelp has listings for that category/location
- Try different category or broader location
- Check `scraper.log` for errors

## ⚠️ Legal & Ethical Use

This tool scrapes publicly available business information.

### ✅ Acceptable
- B2B lead generation
- Market research
- Building contact lists for legitimate business

### ❌ Avoid
- Selling scraped data as a product
- Overwhelming servers
- Spam or fraud

**Note:** Web scraping of public data is generally legal (hiQ Labs vs. LinkedIn), but violates Yelp ToS. Use at your own risk.

## 📁 Project Structure

```
├── app.py                 # Flask web server & API
├── scraper.py             # Core scraping logic
├── requirements.txt       # Dependencies
├── API_DOCUMENTATION.md   # Complete API docs
├── templates/
│   ├── index.html        # Web interface
│   └── jobs.html         # Jobs list page
└── results/              # Output files
```

## 🤝 What's New

Recent updates:
- ✅ Added web interface
- ✅ Added REST API for n8n
- ✅ Fixed Chrome crashes (30s timeout)
- ✅ Fixed Windows Unicode errors
- ✅ Improved business name extraction
- ✅ Command-line arguments support

## 📄 License

MIT License

---

**Need Help?**
- 📖 [API Documentation](API_DOCUMENTATION.md)
- 📝 Check `scraper.log` file
- 🐛 Open GitHub issue

**Built with ❤️ for construction tech automation**
